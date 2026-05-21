# Cloudflare DDNS

A streamlined, "set-it-and-forget-it" Docker container that keeps your Cloudflare DNS records in perfect sync with your dynamic IP address. 

We believe in security and simplicity: **deploy in seconds, and configure securely through our intuitive web interface.**

## Key Features
* **Security First**: Configure your API token securely through the UI—no hardcoded secrets.
* **Flexible Control**: Select your update interval (in minutes), timezone, and proxy status via the UI.
* **Reliable**: Designed to run silently in the background, ensuring your DNS records are always accurate.

## Getting Your Cloudflare API Token
1. Log into your [Cloudflare Dashboard](https://dash.cloudflare.com/).
2. Click on your profile icon in the top right and go to **My Profile** > **API Tokens**.
3. Click **Create Token**.
4. Use the **Edit zone DNS** template.
5. Under **Zone Resources**, select **Include** > **Specific zone** > [Your Domain].
6. Continue to summary and **Create Token**. Save this token—it will not be shown again.

## Docker Compose
For a persistent setup, use this `docker-compose.yml`:

```yaml
services:
  cloudflare-ddns:
    image: ghcr.io/dmesgnoise/cloudflare-ddns:latest
    container_name: cloudflare-ddns
    ports:
      - "5555:80"
    environment:
      # Optional: Override UI settings manually
      - TZ=America/New_York   # Replace with your local timezone
      - INTERVAL=5            # Interval in minutes
      - PROXIED=true          # Set to 'false' for DNS Only
    restart: unless-stopped
```

## Getting Started
1. **Deploy**: Run the container using the compose file above.
2. **Access the UI**: Navigate to `http://<your-server-ip>:5555` in your browser.
3. **Configure**: 
   - **API Token**: Enter the token you created above.
   - **Timezone**: Select your local timezone.
   - **Update Interval**: Set how often (in minutes) to check for IP changes.
   - **Proxy Status**: Toggle the **Proxied/DNS Only** switch to match your domain settings.
4. **Relax**: Your DNS records will now stay synced automatically.
