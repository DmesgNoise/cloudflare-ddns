from flask import Flask, render_template
from apscheduler.schedulers.background import BackgroundScheduler
import ddns_logic
import os

app = Flask(__name__)

# Scheduler to run the DDNS update check every 5 minutes
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(func=ddns_logic.update_cloudflare, trigger="interval", minutes=5)
scheduler.start()

@app.route('/')
def index():
    # Placeholder status for the GUI
    status = {"last_run": "Never", "current_ip": "0.0.0.0"}
    return render_template('index.html', status=status)

if __name__ == "__main__":
    # We use port 5555 as we decided
    app.run(host='0.0.0.0', port=5555)
