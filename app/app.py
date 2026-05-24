import os, json, time, datetime, requests, threading, traceback
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
CONFIG_FILE = '/app/config/config.json'

LAST_CHECKED_TIME, CURRENT_WAN_IP, ENGINE_STATUS = "Never", "Loading...", "Initializing..."
wake_up_event = threading.Event()

def load_config():
    if not os.path.exists(CONFIG_FILE): return {"token": "", "zone_id": "", "zone_name": "", "record_id": "", "interval": "60"}
    try:
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    except: return {"token": "", "zone_id": "", "zone_name": "", "record_id": "", "interval": "60"}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)

def ddns_worker_engine():
    global LAST_CHECKED_TIME, CURRENT_WAN_IP, ENGINE_STATUS
    while True:
        try:
            config = load_config()
            if config.get("token") and config.get("zone_id") and config.get("record_id"):
                current_wan = requests.get("https://api.ipify.org", timeout=5).text.strip()
                CURRENT_WAN_IP = current_wan
                url = f"https://api.cloudflare.com/client/v4/zones/{config['zone_id']}/dns_records/{config['record_id']}"
                headers = {"Authorization": f"Bearer {config['token']}", "Content-Type": "application/json"}
                payload = {"type": "A", "name": config['zone_name'], "content": current_wan, "proxied": False}
                requests.put(url, headers=headers, json=payload, timeout=10)
                ENGINE_STATUS = "Sync Successful"
            else:
                ENGINE_STATUS = "Configuration Incomplete"
        except: ENGINE_STATUS = "Error"
        wake_up_event.wait(timeout=int(load_config().get("interval", 60)))
        wake_up_event.clear()

threading.Thread(target=ddns_worker_engine, daemon=True).start()

@app.route('/')
def index(): return render_template('status.html')

@app.route('/api/status')
def api_status():
    config = load_config()
    return jsonify({"wan_ip": CURRENT_WAN_IP, "dns_record": config.get("zone_name"), "last_checked": LAST_CHECKED_TIME, "engine_status": ENGINE_STATUS, "interval": config.get("interval")})

@app.route('/api/fetch_zones', methods=['POST'])
def api_fetch_zones():
    token = request.get_json().get('token', '')
    try:
        resp = requests.get("https://api.cloudflare.com/client/v4/zones", headers={"Authorization": f"Bearer {token}"}, timeout=8)
        return jsonify({"success": True, "zones": [{"id": z["id"], "name": z["name"]} for z in resp.json().get("result", [])]})
    except: return jsonify({"success": False, "zones": []})

@app.route('/api/resolve_ids', methods=['POST'])
def api_resolve_ids():
    data = request.get_json()
    token, zone_name = data.get('token'), data.get('zone_name')
    headers = {"Authorization": f"Bearer {token}"}
    zone_id, record_id = "", ""
    z_resp = requests.get("https://api.cloudflare.com/client/v4/zones", headers=headers).json()
    for z in z_resp.get('result', []):
        if z['name'] == zone_name: zone_id = z['id']; break
    if zone_id:
        r_resp = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name={zone_name}", headers=headers).json()
        if r_resp.get('result'): record_id = r_resp['result'][0]['id']
    return jsonify({"zone_id": zone_id, "record_id": record_id})

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        save_config({
            "token": request.form.get('token'), "zone_id": request.form.get('zone_id'),
            "zone_name": request.form.get('zone_name'), "record_id": request.form.get('record_id'), "interval": "60"
        })
        wake_up_event.set()
        return redirect(url_for('index'))
    return render_template('setup.html', config=load_config())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555)
