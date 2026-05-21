import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_public_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except Exception as e:
        print(f"Error fetching IP: {e}")
        return None

def update_cloudflare():
    token = os.getenv('CF_API_TOKEN')
    zone_id = os.getenv('CF_ZONE_ID')
    record_name = os.getenv('RECORD_NAME')
    proxied = os.getenv('CF_PROXIED', 'true').lower() == 'true'

    ip = get_public_ip()
    if not ip:
        return

    print(f"Checking Cloudflare for {record_name}. Current public IP: {ip}")
    # Logic for Cloudflare API calls will go here in the next iteration
    # For now, this confirms the script can read your .env and reach the web
