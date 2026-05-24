import os, json, requests, threading, traceback, sys
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
CONFIG_FILE = '/app/config/config.json'

LAST_CHECKED_TIME, CURRENT_WAN_IP, ENGINE_STATUS = "Never", "Loading...", "Initializing..."
wake_up_event = threading.Event()

def load_config():
    default = {"token": "", "zone_id": "", "zone_name": "", "record_id": "", "timezone": os.environ.get('TZ', 'UTC'), "proxied": False, "interval": "60"}
    if not os.path.exists(CONFIG_FILE): return default
    try:
        with open(CONFIG_FILE, 'r') as f: return {**default, **json.load(f)}
    except: return default

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
                
                # Update with proxy status from config
                payload = {"type": "A", "name": config['zone_name'], "content": current_wan, "proxied": config.get('proxied', False)}
                requests.put(url, headers=headers, json=payload, timeout=10)
                ENGINE_STATUS = "Sync Successful"
            else:
                ENGINE_STATUS = "Config Incomplete"
        except Exception:
            ENGINE_STATUS = "Error: Check Logs"
        wake_up_event.wait(timeout=int(load_config().get("interval", 60)))
        wake_up_event.clear()

threading.Thread(target=ddns_worker_engine, daemon=True).start()

@app.route('/')
def index(): return render_template('status.html')

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        zone_name = request.form.get('zone_name', '').strip()
        timezone = request.form.get('timezone', 'UTC')
        proxied = request.form.get('proxied') == 'true'
        interval = request.form.get('interval', '60')

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        zone_id, record_id = "", ""
        
        # Resolve IDs
        z_resp = requests.get("https://api.cloudflare.com/client/v4/zones", headers=headers, timeout=8).json()
        for z in z_resp.get('result', []):
            if z['name'] == zone_name:
                zone_id = z['id']
                break
        if zone_id:
            r_resp = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name={zone_name}", headers=headers, timeout=8).json()
            if r_resp.get('result'): record_id = r_resp['result'][0]['id']

        save_config({"token": token, "zone_id": zone_id, "zone_name": zone_name, "record_id": record_id, "timezone": timezone, "proxied": proxied, "interval": interval})
        wake_up_event.set()
        return redirect(url_for('index'))
    return render_template('setup.html', config=load_config())

@app.route('/api/fetch_zones', methods=['POST'])
def api_fetch_zones():
    token = request.get_json().get('token', '')
    resp = requests.get("https://api.cloudflare.com/client/v4/zones", headers={"Authorization": f"Bearer {token}"}, timeout=8)
    return jsonify({"zones": [{"name": z["name"]} for z in resp.json().get("result", [])]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555)
