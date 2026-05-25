import os
import json
import datetime
import threading
import secrets
import requests

from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

CONFIG_FILE = "/app/config/config.json"

try:
    version_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "VERSION"
    )

    with open(version_path, "r") as f:
        APP_VERSION = f.read().strip()

except Exception:
    APP_VERSION = os.environ.get("APP_VERSION", "unknown")

DEFAULT_CONFIG = {
    "configured": False,
    "admin_username": "",
    "admin_password_hash": "",
    "token": "",
    "zone_name": "",
    "zone_id": "",
    "record_id": "",
    "timezone": "America/New_York",
    "proxied": False,
    "interval": "60",
    "last_known_ip": ""
}

LAST_CHECKED_TIME = "Never"
CURRENT_WAN_IP = "Loading..."
CURRENT_CLOUDFLARE_IP = "Loading..."
ENGINE_STATUS = "Initializing"

wake_up_event = threading.Event()


def now_string():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_config():
    config = DEFAULT_CONFIG.copy()

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)

            if isinstance(saved, dict):
                config.update(saved)

        except Exception:
            pass

    return config


def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    merged = DEFAULT_CONFIG.copy()
    merged.update(config)

    with open(CONFIG_FILE, "w") as f:
        json.dump(merged, f, indent=4)


def ensure_secret_key():
    config = load_config()

    if not config.get("flask_secret_key"):
        config["flask_secret_key"] = secrets.token_hex(32)
        save_config(config)

    app.secret_key = config["flask_secret_key"]


def auth_is_configured(config=None):
    if config is None:
        config = load_config()

    return bool(
        config.get("admin_username")
        and config.get("admin_password_hash")
    )


def config_is_complete(config=None):
    if config is None:
        config = load_config()

    return all([
        config.get("configured"),
        config.get("token"),
        config.get("zone_name"),
        config.get("zone_id"),
        config.get("record_id"),
        auth_is_configured(config)
    ])


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        config = load_config()

        if not auth_is_configured(config):
            return redirect(url_for("setup"))

        if not session.get("logged_in"):
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


def api_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        config = load_config()

        if not auth_is_configured(config):
            return jsonify({
                "success": False,
                "error": "Authentication is not configured"
            }), 401

        if not session.get("logged_in"):
            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401

        return view(*args, **kwargs)

    return wrapped


def cloudflare_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def get_public_ip():
    response = requests.get("https://api.ipify.org", timeout=10)
    response.raise_for_status()
    return response.text.strip()


def fetch_cloudflare_zones(token):
    response = requests.get(
        "https://api.cloudflare.com/client/v4/zones",
        headers=cloudflare_headers(token),
        timeout=10
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise Exception(data.get("errors", "Cloudflare zone fetch failed"))

    return [
        {"id": zone["id"], "name": zone["name"]}
        for zone in data.get("result", [])
    ]


def resolve_root_a_record(token, zone_name):
    zones = fetch_cloudflare_zones(token)

    zone_id = ""

    for zone in zones:
        if zone["name"] == zone_name:
            zone_id = zone["id"]
            break

    if not zone_id:
        raise Exception(f"Zone not found: {zone_name}")

    response = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
        headers=cloudflare_headers(token),
        params={
            "type": "A",
            "name": zone_name
        },
        timeout=10
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise Exception(data.get("errors", "Cloudflare DNS record fetch failed"))

    records = data.get("result", [])

    if not records:
        raise Exception(f"Root A record not found for {zone_name}")

    return zone_id, records[0]["id"]


def get_cloudflare_record(config):
    response = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{config['zone_id']}/dns_records/{config['record_id']}",
        headers=cloudflare_headers(config["token"]),
        timeout=10
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise Exception(data.get("errors", "Cloudflare record fetch failed"))

    return data["result"]


def update_cloudflare_record(config, new_ip):
    payload = {
        "type": "A",
        "name": config["zone_name"],
        "content": new_ip,
        "proxied": bool(config.get("proxied", False))
    }

    response = requests.put(
        f"https://api.cloudflare.com/client/v4/zones/{config['zone_id']}/dns_records/{config['record_id']}",
        headers=cloudflare_headers(config["token"]),
        json=payload,
        timeout=10
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise Exception(data.get("errors", "Cloudflare record update failed"))

    return data["result"]


def sync_once(force_cloudflare_check=False):
    global LAST_CHECKED_TIME
    global CURRENT_WAN_IP
    global CURRENT_CLOUDFLARE_IP
    global ENGINE_STATUS

    config = load_config()

    if not config_is_complete(config):
        LAST_CHECKED_TIME = now_string()
        ENGINE_STATUS = "Configuration Incomplete"
        return

    current_ip = get_public_ip()

    CURRENT_WAN_IP = current_ip
    LAST_CHECKED_TIME = now_string()

    last_known_ip = config.get("last_known_ip", "")

    if not force_cloudflare_check and last_known_ip == current_ip:
        CURRENT_CLOUDFLARE_IP = current_ip
        ENGINE_STATUS = "IP Stable"
        return

    cloudflare_record = get_cloudflare_record(config)
    cloudflare_ip = cloudflare_record.get("content", "")

    CURRENT_CLOUDFLARE_IP = cloudflare_ip

    if cloudflare_ip == current_ip:
        config["last_known_ip"] = current_ip
        save_config(config)
        CURRENT_CLOUDFLARE_IP = current_ip
        ENGINE_STATUS = "IP Stable"
        return

    update_cloudflare_record(config, current_ip)

    config["last_known_ip"] = current_ip
    save_config(config)

    CURRENT_CLOUDFLARE_IP = current_ip
    ENGINE_STATUS = "IP Updated"


def ddns_worker():
    global LAST_CHECKED_TIME
    global ENGINE_STATUS

    first_run = True

    while True:
        try:
            sync_once(force_cloudflare_check=first_run)
            first_run = False

        except Exception as e:
            LAST_CHECKED_TIME = now_string()
            ENGINE_STATUS = f"Error: {e}"

        config = load_config()

        try:
            interval = int(config.get("interval", "60"))

        except Exception:
            interval = 60

        wake_up_event.wait(timeout=interval)
        wake_up_event.clear()


@app.route("/")
@login_required
def index():
    return render_template(
        "status.html",
        version=APP_VERSION
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    config = load_config()

    if not auth_is_configured(config):
        return redirect(url_for("setup"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if (
            username == config.get("admin_username")
            and check_password_hash(config.get("admin_password_hash", ""), password)
        ):
            session["logged_in"] = True
            session["username"] = username

            if config_is_complete(config):
                return redirect(url_for("index"))

            return redirect(url_for("setup"))

        return render_template(
            "login.html",
            error="Invalid username or password",
            version=APP_VERSION
        )

    if session.get("logged_in"):
        return redirect(url_for("index"))

    return render_template(
        "login.html",
        error="",
        version=APP_VERSION
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/setup", methods=["GET", "POST"])
def setup():
    config = load_config()
    first_run = not auth_is_configured(config)

    if not first_run and not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        token = request.form.get("token", "").strip()
        zone_name = request.form.get("zone_name", "").strip()
        timezone = request.form.get("timezone", "America/New_York").strip()
        interval = request.form.get("interval", config.get("interval", "60")).strip()
        proxied = request.form.get("proxied") == "true"

        admin_username = config.get("admin_username", "")
        admin_password_hash = config.get("admin_password_hash", "")

        if first_run:
            admin_username = request.form.get("admin_username", "").strip()
            admin_password = request.form.get("admin_password", "")
            admin_password_confirm = request.form.get("admin_password_confirm", "")

            if not admin_username:
                return render_template(
                    "setup.html",
                    config=config,
                    first_run=first_run,
                    error="Admin username is required",
                    version=APP_VERSION
                )

            if not admin_password:
                return render_template(
                    "setup.html",
                    config=config,
                    first_run=first_run,
                    error="Admin password is required",
                    version=APP_VERSION
                )

            if admin_password != admin_password_confirm:
                return render_template(
                    "setup.html",
                    config=config,
                    first_run=first_run,
                    error="Passwords do not match",
                    version=APP_VERSION
                )

            admin_password_hash = generate_password_hash(admin_password)

        zone_id, record_id = resolve_root_a_record(token, zone_name)

        save_config({
            "configured": True,
            "admin_username": admin_username,
            "admin_password_hash": admin_password_hash,
            "token": token,
            "zone_name": zone_name,
            "zone_id": zone_id,
            "record_id": record_id,
            "timezone": timezone,
            "proxied": proxied,
            "interval": interval,
            "last_known_ip": config.get("last_known_ip", ""),
            "flask_secret_key": config.get("flask_secret_key", secrets.token_hex(32))
        })

        session["logged_in"] = True
        session["username"] = admin_username

        wake_up_event.set()

        return redirect(url_for("index"))

    return render_template(
        "setup.html",
        config=config,
        first_run=first_run,
        error="",
        version=APP_VERSION
    )


@app.route("/api/fetch_zones", methods=["POST"])
def api_fetch_zones():
    try:
        token = request.get_json().get("token", "").strip()
        zones = fetch_cloudflare_zones(token)

        return jsonify({
            "success": True,
            "zones": zones
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "zones": []
        }), 400


@app.route("/api/resolve_record", methods=["POST"])
def api_resolve_record():
    try:
        data = request.get_json()

        token = data.get("token", "").strip()
        zone_name = data.get("zone_name", "").strip()

        zone_id, record_id = resolve_root_a_record(token, zone_name)

        return jsonify({
            "success": True,
            "zone_id": zone_id,
            "record_id": record_id
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "zone_id": "",
            "record_id": ""
        }), 400


@app.route("/api/status")
@api_login_required
def api_status():
    config = load_config()

    return jsonify({
        "success": True,
        "wan_ip": CURRENT_WAN_IP,
        "cloudflare_ip": CURRENT_CLOUDFLARE_IP,
        "dns_record": config.get("zone_name", ""),
        "updated": LAST_CHECKED_TIME,
        "engine_status": ENGINE_STATUS,
        "interval": config.get("interval", "60"),
        "proxied": config.get("proxied", False),
        "version": APP_VERSION
    })


@app.route("/api/update_interval", methods=["POST"])
@api_login_required
def api_update_interval():
    data = request.get_json()
    interval = str(data.get("interval", "60"))

    config = load_config()
    config["interval"] = interval
    save_config(config)

    wake_up_event.set()

    return jsonify({
        "success": True
    })


@app.route("/api/update_proxy", methods=["POST"])
@api_login_required
def api_update_proxy():
    global LAST_CHECKED_TIME
    global CURRENT_WAN_IP
    global CURRENT_CLOUDFLARE_IP
    global ENGINE_STATUS

    try:
        data = request.get_json()
        proxied = bool(data.get("proxied", False))

        config = load_config()

        if not config_is_complete(config):
            ENGINE_STATUS = "Configuration Incomplete"
            LAST_CHECKED_TIME = now_string()

            return jsonify({
                "success": False,
                "error": "Configuration incomplete"
            }), 400

        config["proxied"] = proxied
        save_config(config)

        current_ip = get_public_ip()

        CURRENT_WAN_IP = current_ip
        CURRENT_CLOUDFLARE_IP = current_ip
        LAST_CHECKED_TIME = now_string()

        update_cloudflare_record(config, current_ip)

        config["last_known_ip"] = current_ip
        save_config(config)

        ENGINE_STATUS = "Proxy Status Updated"

        return jsonify({
            "success": True
        })

    except Exception as e:
        LAST_CHECKED_TIME = now_string()
        ENGINE_STATUS = f"Error: {e}"

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


@app.route("/api/force_sync", methods=["POST"])
@api_login_required
def api_force_sync():
    global LAST_CHECKED_TIME
    global ENGINE_STATUS

    try:
        sync_once(force_cloudflare_check=True)

        return jsonify({
            "success": True
        })

    except Exception as e:
        LAST_CHECKED_TIME = now_string()
        ENGINE_STATUS = f"Error: {e}"

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


ensure_secret_key()

threading.Thread(target=ddns_worker, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555)
