import os
import json
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
# Use an environment variable for the secret key for better security
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default-insecure-key')
CONFIG_PATH = '/app/config/config.json'

def get_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return None

@app.route('/')
def index():
    config = get_config()
    if not config:
        return redirect(url_for('setup'))
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return "Dashboard: Welcome. DDNS is active."

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        config = {
            "password": request.form['password'],
            "cf_api_token": request.form['cf_api_token'],
            "cf_zone_id": request.form['cf_zone_id'],
            "record_name": request.form['record_name']
        }
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f)
        return redirect(url_for('login'))
    return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        config = get_config()
        if config and request.form['password'] == config.get('password'):
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555)
