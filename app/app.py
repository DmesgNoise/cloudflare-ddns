import os, json, time, datetime, requests, threading, traceback, sys
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
CONFIG_FILE = 'config/config.json'

LAST_CHECKED_TIME, CURRENT_WAN_IP, ENGINE_STATUS = "Never", "Loading...", "Initializing..."
wake_up_event = threading.Event()

def load_config():
    if not os.path.exists(CONFIG_FILE): 
        return {"token": "", "zone_id": "", "zone_name": "", "record_id": "", "interval": "60", "timezone": os.environ.get('TZ', 'America/New_York')}
    try:
        with open(CONFIG_FILE, 'r') as f: 
            data = json.load(f)
            # Ensure standard configuration keys are safely mapped
            for key in ["token", "zone_id", "zone_name", "record_id", "interval"]:
                if key not in data: data[key] = ""
            
            # REQUIREMENT CHECK: Prioritize Compose environment TZ variable over file storage
            data["timezone"] = os.environ.get('TZ', data.get('timezone', 'America/New_York'))
            return data
    except: 
        return {"token": "", "zone_id": "", "zone_name": "", "record_id": "", "interval": "60", "timezone": os.environ.get('TZ', 'America/New_York')}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f: 
        json.dump(config, f, indent=4)

def get_cloudflare_ip(token, zone_id, record_id):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            return resp.json()['result']['content']
    except: pass
    return None

def update_cloudflare_record(token, zone_id, record_id, domain_name, new_ip):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"type": "A", "name": domain_name, "content": new_ip, "proxied": False}
    try:
        return requests.put(url, headers=headers, json=payload, timeout=10).status_code == 200
    except: return False

def ddns_worker_engine():
    global LAST_CHECKED_TIME, CURRENT_WAN_IP, ENGINE_STATUS
    while True:
        try:
            LAST_CHECKED_TIME = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ENGINE_STATUS = "Checking IP..."
            config = load_config()
            
            # Behind the scenes resolution logic if text name exists but ID hashes are missing
            if config.get("token") and config.get("zone_name") and (not config.get("zone_id") or not config.get("record_id")):
                headers = {"Authorization": f"Bearer {config['token']}"}
                
                # Fetch Zone ID automatically if missing
                if not config.get("zone_id"):
                    z_resp = requests.get("https://api.cloudflare.com/client/v4/zones", headers=headers, timeout=6)
                    if z_resp.status_code == 200:
                        for z in z_resp.json().get('result', []):
                            if z["name"] == config["zone_name"]:
                                config["zone_id"] = z["id"]
                                break
                
                # Fetch Record ID automatically if missing
                if config.get("zone_id") and not config.get("record_id"):
                    r_url = f"https://api.cloudflare.com/client/v4/zones/{config['zone_id']}/dns_records?type=A&name={config['zone_name']}"
                    r_resp = requests.get(r_url, headers=headers, timeout=6)
                    if r_resp.status_code == 200:
                        records = r_resp.json().get('result', [])
                        if records:
                            config["record_id"] = records[0]["id"]
                
                # Resave configuration file silently with newfound background mappings
                save_config(config)

            # Core application DDNS processing loop
            if config.get("token") and config.get("zone_id") and config.get("record_id"):
                current_wan = requests.get("https://api.ipify.org", timeout=5).text.strip()
                CURRENT_WAN_IP = current_wan
                cf_ip = get_cloudflare_ip(config["token"], config["zone_id"], config["record_id"])
                
                if cf_ip and cf_ip != current_wan:
                    ENGINE_STATUS = "Mismatch: Updating Cloudflare..."
                    if update_cloudflare_record(config["token"], config["zone_id"], config["record_id"], config["zone_name"], current_wan):
                        ENGINE_STATUS = "Sync Successful"
                    else:
                        ENGINE_STATUS = "Update Failed"
                else:
                    ENGINE_STATUS = "IP stable"
            else:
                ENGINE_STATUS = "Configuration Incomplete"
        except Exception:
            ENGINE_STATUS = "Error: See container logs"
            print(traceback.format_exc(), file=sys.stderr)
            
        wake_up_event.wait(timeout=int(load_config().get("interval", 60)))
        wake_up_event.clear()

threading.Thread(target=ddns_worker_engine, daemon=True).start()

@app.route('/')
def index(): return render_template('status.html')

@app.route('/api/status')
def api_status():
    config = load_config()
    return jsonify({"wan_ip": CURRENT_WAN_IP, "dns_record": config.get("zone_name"), "last_checked": LAST_CHECKED_TIME, "engine_status": ENGINE_STATUS, "interval": config.get("interval")})

@app.route('/api/force_sync', methods=['POST'])
def api_force_sync():
    wake_up_event.set()
    return jsonify({"success": True})

@app.route('/api/update_interval', methods=['POST'])
def api_update_interval():
    config = load_config()
    config['interval'] = request.get_json().get('interval', '60')
    save_config(config)
    wake_up_event.set()
    return jsonify({"success": True})

@app.route('/api/fetch_zones', methods=['POST'])
def api_fetch_zones():
    token = request.get_json().get('token', '')
    try:
        resp = requests.get("https://api.cloudflare.com/client/v4/zones", headers={"Authorization": f"Bearer {token}"}, timeout=8)
        return jsonify({"success": True, "zones": [{"id": z["id"], "name": z["name"]} for z in resp.json().get("result", [])]})
    except: return jsonify({"success": False, "zones": []})

@app.route('/api/fetch_records', methods=['POST'])
def api_fetch_records():
    data = request.get_json()
    token, zone_id = data.get('token'), data.get('zone_id')
    try:
        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=8)
        return jsonify({"success": True, "records": [{"id": r["id"], "name": r["name"]} for r in resp.json().get("result", []) if r["type"] == "A"]})
    except: return jsonify({"success": False, "records": []})

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        # REQUIREMENT CHECK: Catch, lock, and persistently save all fields exactly as submitted
        save_config({
            "token": request.form.get('token'), 
            "zone_id": request.form.get('zone_id'),  
            "zone_name": request.form.get('zone_name'), 
            "record_id": request.form.get('record_id'), 
            "timezone": request.form.get('timezone'),
            "interval": "60"
        })
        wake_up_event.set()
        return redirect(url_for('index'))
    return render_template('setup.html', config=load_config())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555)
