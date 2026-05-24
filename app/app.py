import os, json, time, datetime, requests, threading, traceback, sys

app = Flask(__name__)
CONFIG_FILE = 'config/config.json'

LAST_CHECKED_TIME, CURRENT_WAN_IP, ENGINE_STATUS = "Never", "Loading...", "Initializing..."
wake_up_event = threading.Event()

def load_config():
    if not os.path.exists(CONFIG_FILE):  
        return {"token": "", "zone_name": "", "zone_id": "", "record_id": "", "interval": "60", "proxied": False, "timezone": os.environ.get('TZ', 'America/New_York')}
    try:
        with open(CONFIG_FILE, 'r') as f:  
            data = json.load(f)
            # Guarantee standard keys exist
            for key in ["token", "zone_name", "zone_id", "record_id", "interval"]:
                if key not in data: data[key] = ""
            
            # Prioritize Compose file TZ environment variable, fallback to file value
            data["timezone"] = os.environ.get('TZ', data.get('timezone', 'America/New_York'))
            if "proxied" not in data: data["proxied"] = False
            if not data["interval"]: data["interval"] = "60"
            return data
    except:  
        return {"token": "", "zone_name": "", "zone_id": "", "record_id": "", "interval": "60", "proxied": False, "timezone": os.environ.get('TZ', 'America/New_York')}

def save_config(config):
    config_dir = os.path.dirname(CONFIG_FILE)
    try:
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:  
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config file: {e}", file=sys.stderr)

def get_cloudflare_ip(token, zone_id, record_id):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            return resp.json()['result']['content']
    except: pass
    return None

def update_cloudflare_record(token, zone_id, record_id, domain_name, new_ip, proxied_status):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"type": "A", "name": domain_name, "content": new_ip, "proxied": bool(proxied_status)}
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
            
            if config.get("token").strip() and config.get("zone_id").strip() and config.get("record_id").strip():
                current_wan = requests.get("https://api.ipify.org", timeout=5).text.strip()
                CURRENT_WAN_IP = current_wan
                cf_ip = get_cloudflare_ip(config["token"], config["zone_id"], config["record_id"])
                
                if cf_ip and cf_ip != current_wan:
                    ENGINE_STATUS = "Mismatch: Updating Cloudflare..."
                    if update_cloudflare_record(config["token"], config["zone_id"], config["record_id"], config["zone_name"], current_wan, config.get("proxied", False)):
                        ENGINE_STATUS = "Sync Successful"
                    else:
                        ENGINE_STATUS = "Update Failed"
                else:
                    ENGINE_STATUS = "IP stable"
            else:
                ENGINE_STATUS = "Configuration Incomplete"
        except Exception:
            ENGINE_STATUS = "Error: Check container terminal logs"
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

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        # 1. Grab the 3 exact items entered by the user
        token = request.form.get('token', '').strip()
        zone_name = request.form.get('zone_name', '').strip()
        timezone = request.form.get('timezone', 'America/New_York')
        
        # Keep proxy setting if tracked, default to False
        current_config = load_config()
        proxied_status = current_config.get('proxied', False)
        
        resolved_zone_id = ""
        resolved_record_id = ""
        
        # 2. Behind the scenes: Convert human entries into Cloudflare system IDs
        try:
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            
            # Fetch Zone ID matching the exact domain string text input
            z_resp = requests.get("https://api.cloudflare.com/client/v4/zones", headers=headers, timeout=6)
            if z_resp.status_code == 200:
                zones = z_resp.json().get('result', [])
                for z in zones:
                    if z["name"] == zone_name:
                        resolved_zone_id = z["id"]
                        break
            
            # Fetch Record ID matching the root A record inside that zone
            if resolved_zone_id:
                r_url = f"https://api.cloudflare.com/client/v4/zones/{resolved_zone_id}/dns_records?type=A&name={zone_name}"
                r_resp = requests.get(r_url, headers=headers, timeout=6)
                if r_resp.status_code == 200:
                    records = r_resp.json().get('result', [])
                    if records:
                        resolved_record_id = records[0]["id"]
                        
        except Exception as e:
            print(f"Backend background lookup failed: {e}", file=sys.stderr)

        # 3. Persistently save all values cleanly to disk
        save_config({
            "token": token,  
            "zone_name": zone_name,
            "zone_id": resolved_zone_id,     
            "record_id": resolved_record_id,  
            "timezone": timezone,
            "proxied": proxied_status,
            "interval": current_config.get('interval', '60')
        })
        wake_up_event.set()
        return redirect(url_for('index'))
        
    return render_template('setup.html', config=load_config())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555)
