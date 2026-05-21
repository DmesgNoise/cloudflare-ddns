from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import json
import threading
import time
from ddns_logic import run_ddns_cycle  # Assuming your core sync function is here

app = Flask(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading config: {e}")
    # Return pristine defaults if no config exists yet
    return {
        "api_token": "",
        "interval": 5,
        "proxied": True
    }

def save_config(config_data):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

@app.route('/')
def index():
    config = load_config()
    # Check if the container has a running status message or logs to display
    status_message = "Awaiting initial configuration..." if not config["api_token"] else "Service Active"
    return render_template('index.html', config=config, status_message=status_message)

@app.route('/save-settings', methods=['POST'])
def save_settings():
    api_token = request.form.get('api_token', '').strip()
    interval = request.form.get('interval', '5')
    proxied = request.form.get('proxied') == 'true' or request.form.get('proxied') == 'on'

    config = {
        "api_token": api_token,
        "interval": int(interval),
        "proxied": proxied
    }
    
    if save_config(config):
        # Trigger an immediate background run of the DDNS logic with the new settings
        threading.Thread(target=run_ddns_cycle, args=(config,), daemon=True).start()

    return redirect(url_for('index'))

@app.route('/api/status')
def status():
    config = load_config()
    return jsonify({
        "configured": bool(config["api_token"]),
        "interval": config["interval"],
        "proxied": config["proxied"]
    })

def background_scheduler():
    while True:
        config = load_config()
        if config.get("api_token"):
            try:
                run_ddns_cycle(config)
            except Exception as e:
                print(f"Error in background sync cycle: {e}")
        # Sleep for the configured interval (converted to seconds), default to 5 mins if error
        sleep_time = config.get("interval", 5) * 60
        time.sleep(sleep_time)

if __name__ == '__main__':
    # Start background loop for syncing DNS records
    threading.Thread(target=background_scheduler, daemon=True).start()
    # Run server on port 5555 internally matching our compose mappings
    app.run(host='0.0.0.0', port=5555)
