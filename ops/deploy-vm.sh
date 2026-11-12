#!/usr/bin/env bash
# Publish the single-container demo to a plain Ubuntu server (Azure VM, AWS EC2, any VPS).
#   ops/deploy-vm.sh <server-public-ip> </path/to/key.pem>
#   SSH_USER=azureuser ops/deploy-vm.sh ...    (Azure VMs use azureuser; AWS Ubuntu images use ubuntu, the default)
# Copies the project over SSH, builds the Docker image ON the server, runs it behind Caddy with a free HTTPS name
# (<ip>.sslip.io), and creates the two secrets on the server. Nothing secret is printed or stored on your laptop.
set -euo pipefail
IP="${1:?usage: ops/deploy-vm.sh <server-public-ip> </path/to/key.pem>}"
KEY="${2:?usage: ops/deploy-vm.sh <server-public-ip> </path/to/key.pem>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
U="${SSH_USER:-ubuntu}"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "$U@$IP")
HOST="${IP//./-}.sslip.io"

echo "== copying project"
"${SSH[@]}" "sudo apt-get update -qq && sudo apt-get install -y -qq rsync >/dev/null"
rsync -az --delete -e "ssh -i $KEY" \
  --exclude node_modules --exclude .venv --exclude __pycache__ --exclude .pytest_cache --exclude .git --exclude .DS_Store \
  --exclude data-external --exclude backend/data --exclude backend/tests --exclude frontend/dist --exclude frontend/e2e --exclude ops/.data --exclude docs --exclude .impeccable \
  "$ROOT/" "$U@$IP:griha-src/"

echo "== building and starting on the server"
"${SSH[@]}" "HOST=$HOST bash -s" <<'REMOTE'
set -euo pipefail
sudo apt-get install -y -qq docker.io caddy >/dev/null
# The image build (Node + Python installs) needs more memory than a small instance has: add swap when RAM is under 3 GB (a free-tier t3.micro has 1 GB).
if [ "$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)" -lt 3000 ] && [ ! -f /swapfile ]; then
  sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile >/dev/null && sudo swapon /swapfile
fi
# Secrets are created once, on the server, readable by root only. Case links keep working across redeploys.
if [ ! -f /etc/griha.env ]; then
  M=$(python3 -c 'import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')
  S=$(python3 -c 'import secrets;print(secrets.token_hex(32))')
  printf 'GRIHA_MASTER_KEY=%s\nGRIHA_SECRET=%s\n' "$M" "$S" | sudo tee /etc/griha.env >/dev/null
  sudo chmod 600 /etc/griha.env
fi
# The admin password is separate from the published officer password. Created once; read it with: sudo grep GRIHA_ADMIN_PASSWORD /etc/griha.env
if ! sudo grep -q '^GRIHA_ADMIN_PASSWORD=' /etc/griha.env; then
  A=$(python3 -c 'import secrets;print(secrets.token_urlsafe(12))')
  printf 'GRIHA_ADMIN_PASSWORD=%s\n' "$A" | sudo tee -a /etc/griha.env >/dev/null
fi
sudo docker build -t griha ~/griha-src
sudo docker rm -f griha >/dev/null 2>&1 || true
sudo docker run -d --name griha --restart unless-stopped --env-file /etc/griha.env -v griha-data:/data -p 127.0.0.1:7860:7860 griha >/dev/null
# The named site gets HTTPS. The catch-all :80 block serves any other Host over plain HTTP: it is the origin for a CDN (for example CloudFront), which
# terminates HTTPS for visitors itself. Requests for the named host are still redirected to HTTPS by Caddy.
# Caddy 2.6 overwrites X-Forwarded-For with its peer (behind CloudFront: the edge), so the real visitor would be lost. This writes the chain it received plus its peer into
# X-Client-Chain, which the app reads (griha/clientip.py). header_up SETS the header, so a client cannot forge it.
printf '%s {\n  reverse_proxy 127.0.0.1:7860 {\n    header_up X-Client-Chain "{http.request.header.X-Forwarded-For}, {http.request.remote.host}"\n  }\n}\n\n:80 {\n  reverse_proxy 127.0.0.1:7860 {\n    header_up X-Client-Chain "{http.request.header.X-Forwarded-For}, {http.request.remote.host}"\n  }\n}\n' "$HOST" | sudo tee /etc/caddy/Caddyfile >/dev/null
sudo systemctl restart caddy
REMOTE

echo "Live (first HTTPS certificate can take a minute): https://$HOST"
echo "Check: curl -s https://$HOST/api/health"
