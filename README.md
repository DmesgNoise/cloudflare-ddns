# Cloudflare DDNS

A lightweight, Docker Cloudflare Dynamic DNS utility with a modern web UI, secure first-run setup, automatic Cloudflare domain discovery, and native proxy controls.

No config files. No hunting for Zone IDs. No environment variable juggling.

Deploy the container, complete the guided setup, click **Fetch Domains**, and you're running.

---

## Features

✓ Secure first-run setup with admin account creation  
✓ Login / logout authentication system  
✓ Lightweight Docker deployment  
✓ Modern mobile-friendly web UI  
✓ Automatic domain discovery  
✓ Automatic Zone ID + Record ID resolution  
✓ Single-domain auto-select and auto-populate logic  
✓ Cloudflare proxy toggle (**Proxied / DNS Only**)  
✓ WAN IP monitoring  
✓ Cloudflare DNS IP visibility directly in the dashboard  
✓ Force Sync button  
✓ Configurable update interval  
✓ Expanded timezone selector  
✓ Persistent configuration storage  
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

## First-Run Setup

On first launch, the application walks you through setup.

1. Create your admin username and password.

2. Enter your Cloudflare API token.

3. Click:

```text
Fetch Domains
```

4. Select your domain.

The application automatically resolves:

- Zone ID
- Record ID

Single-domain accounts are auto-detected and populated automatically.

5. Configure:

- Timezone
- Update interval
- Proxy status (**Proxied / DNS Only**)

6. Click:

```text
Save Settings
```

Done.

Future access uses the built-in login page.

---

## Dashboard

The dashboard provides:

- Current WAN IP
- Current Cloudflare DNS IP
- DNS record status
- Proxy state
- Update interval controls
- Force Sync button
- Real-time status indicators
- Settings access
- Secure logout

---

## How It Works

The utility periodically checks your public WAN IP.

If your IP has not changed:

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
ghcr.io/dmesgnoise/cloudflare-ddns:1.2
ghcr.io/dmesgnoise/cloudflare-ddns:1.1
```

`latest` always tracks the newest official release.

---

## License

Licensed under the GNU General Public License v3.0 (GPL-3.0).

You are free to use, modify, and distribute this project, but derivative works must remain open source under the same license.

See the LICENSE file for details.
