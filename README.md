# Cloudflare DDNS

A lightweight, Docker-first Cloudflare Dynamic DNS utility with a clean web UI, automatic domain discovery, and Cloudflare-native proxy controls.

Tired of hunting down Zone IDs, Record IDs, and editing config files? Deploy the container, paste your API token, click **Fetch Domains**, and you're done.

---

## Features

✓ Lightweight Docker deployment  
✓ Simple web UI configuration  
✓ Automatic domain discovery  
✓ Automatic Zone ID + Record ID resolution  
✓ Cloudflare proxy toggle (**Proxied / DNS Only**)  
✓ Persistent configuration storage  
✓ Force Sync button  
✓ WAN IP monitoring  
✓ Lightweight and self-contained  
✓ No database required

---

## Quick Start

Deploy with Docker Compose:

```yaml
services:
  cloudflare-ddns:
    image: ghcr.io/dmesgnoise/cloudflare-ddns:latest
    container_name: cloudflare-ddns
    ports:
      - "5555:5555"
    volumes:
      - ddns-config:/app/config
    restart: unless-stopped

volumes:
  ddns-config:
```

After deployment, open:

```text
http://<your-server-ip>:5555
```

---

## Getting Your Cloudflare API Token

1. Log into your Cloudflare Dashboard.
2. Navigate to:

```text
My Profile → API Tokens
```

3. Click:

```text
Create Token
```

4. Use the template:

```text
Edit zone DNS
```

5. Under **Zone Resources**, select:

```text
Include → Specific Zone → Your Domain
```

6. Create and copy your token.

---

## Setup

1. Deploy the container.
2. Open the web UI.
3. Enter your Cloudflare API token.
4. Click:

```text
Fetch Domains
```

5. Select your domain.

The utility automatically resolves:

- Zone ID
- Record ID

6. Configure:

- Timezone
- Update interval
- Proxy status (**Proxied / DNS Only**)

7. Click:

```text
Save Settings
```

Done.

---

## How It Works

The utility periodically checks your public WAN IP.

If your IP remains unchanged:

```text
No Cloudflare update occurs.
```

If your WAN IP changes:

```text
The Cloudflare DNS record updates automatically.
```

The application minimizes unnecessary Cloudflare API calls while keeping your DNS record synchronized.

---

## Images / Versioning

Official images are published through GitHub Container Registry (GHCR).

Latest release:

```text
ghcr.io/dmesgnoise/cloudflare-ddns:latest
```

Pinned releases:

```text
ghcr.io/dmesgnoise/cloudflare-ddns:1.1
```

`latest` always tracks the newest official release.

---

## License

Licensed under the GNU General Public License v3.0 (GPL-3.0).

You are free to use, modify, and distribute this project, but derivative works must remain open source under the same license.

See the LICENSE file for details.
