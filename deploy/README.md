# Deployment runbook

End-to-end setup for a **publicly hittable showcase URL**. The three pieces
live on three free tiers:

- **Bridge** → your EC2 instance (co-tenants with Provender), behind Caddy for TLS.
- **Viewer** → Cloudflare Pages (static Vue SPA, unlimited bandwidth).
- **FHIR server** → Medplum cloud (free Developer plan).

Estimated time to a live URL: **~90 minutes** end-to-end the first time.

---

## 1. Set up the FHIR server (Medplum)

1. Create an account at [medplum.com](https://www.medplum.com/) → create a Project.
2. Project → **Client Applications** → create one.
3. Copy **Client ID** and **Client Secret** (you'll paste these into `deploy/.env` in step 3).

Medplum's token endpoint is `https://api.medplum.com/oauth2/token` and the FHIR
base URL is `https://api.medplum.com/fhir/R4`.

## 2. DNS + domain

Pick a subdomain for the bridge (e.g. `bridge.sacha-builds.dev`). Create an
**A record** pointing it at your EC2 instance's public IPv4 address.

The viewer gets its own Cloudflare Pages `*.pages.dev` URL for free; optionally
CNAME a friendlier subdomain (e.g. `hl7.sacha-builds.dev`) once the Pages
project is live.

## 3. EC2 host setup (one-time)

SSH into the instance. These commands assume Debian/Ubuntu and that Docker is
already installed (Provender needs it too).

```bash
# Install Caddy for TLS termination
sudo apt update && sudo apt install -y caddy

# Create a dedicated deploy user (optional but tidier than running as ubuntu)
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy

# Clone the repo
sudo mkdir -p /opt/hl7-fhir-bridge
sudo chown deploy:deploy /opt/hl7-fhir-bridge
sudo -u deploy git clone https://github.com/sacha-builds/hl7-fhir-bridge.git /opt/hl7-fhir-bridge

# Create the deploy env
cd /opt/hl7-fhir-bridge/deploy
sudo -u deploy cp .env.example .env
sudo -u deploy vim .env   # paste Medplum creds + FHIR URL
chmod 600 .env            # secrets — keep it readable only by deploy

# Caddy config
sudo cp Caddyfile.example /etc/caddy/Caddyfile
sudo vim /etc/caddy/Caddyfile  # replace bridge.yourdomain.com
sudo systemctl reload caddy

# Bring the bridge up manually the first time
sudo -u deploy ./deploy.sh
```

Verify:

```bash
curl -s https://bridge.yourdomain.com/health
# {"status":"ok","version":"0.1.0"}

curl -s https://bridge.yourdomain.com/metrics | python3 -m json.tool
# uptime_seconds, messages_total: 0, ...
```

## 4. Continuous deployment

GitHub Actions publishes a new `ghcr.io/sacha-builds/hl7-fhir-bridge/bridge:main`
image on every push to `main` (see [.github/workflows/publish.yml](../.github/workflows/publish.yml)).
The EC2 host pulls and restarts automatically via the systemd timer:

```bash
cd /opt/hl7-fhir-bridge
sudo cp deploy/bridge.service   /etc/systemd/system/
sudo cp deploy/redeploy.service /etc/systemd/system/
sudo cp deploy/redeploy.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bridge.service
sudo systemctl enable --now redeploy.timer
```

The timer fires every 10 minutes; if the image SHA hasn't changed, `docker
compose up` is a no-op.

Tail logs:

```bash
sudo journalctl -u bridge -f
docker compose -f /opt/hl7-fhir-bridge/deploy/docker-compose.prod.yml logs -f bridge
```

## 5. Deploy the viewer (Cloudflare Pages)

Two paths — dashboard is easiest, Wrangler is more reproducible.

**Dashboard:**

1. [dash.cloudflare.com](https://dash.cloudflare.com) → Workers & Pages → Create → Pages → Connect to Git.
2. Select the `hl7-fhir-bridge` repo.
3. Framework preset: **Vue**. Root directory: `viewer/`. Build command: `npm run build`. Output: `dist`.
4. Environment variables (both build-time):
   - `VITE_BRIDGE_API_URL` = `https://bridge.yourdomain.com`
   - `VITE_FHIR_BASE_URL` = `https://bridge.yourdomain.com/fhir`
5. Save and deploy.

Cloudflare automatically rebuilds on every push to `main`. The SPA routing
redirect is handled by [viewer/public/_redirects](../viewer/public/_redirects).

## 6. Verify end-to-end

Open the Cloudflare Pages URL. You should see:

- Inbox, slowly populating every 10 min via the background seeder (or
  immediately when you click **Send demo message**).
- Live indicator (green dot) in the nav, fed by the WebSocket through Caddy.
- Patient chart populated once messages flow through.
- Metrics view updating.

If something's off, check (in order):

```bash
# 1. Bridge responding?
curl https://bridge.yourdomain.com/health

# 2. FHIR proxy auth working?
curl https://bridge.yourdomain.com/fhir/Patient

# 3. WebSocket upgrade making it through Caddy?
#    Open browser DevTools → Network → WS tab, should see /ws/messages.

# 4. Bridge logs
sudo journalctl -u bridge -n 100
```

## Rollback

Image tags by commit SHA are all kept on GHCR. To pin a known-good version,
set `BRIDGE_IMAGE=ghcr.io/sacha-builds/hl7-fhir-bridge/bridge:sha-<SHA>` in
`deploy/.env` and rerun `deploy.sh`.
