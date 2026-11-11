# Deploying Griha

Two layers. The first is the link you put in the submission. The second is for presenting.

## 1. Always-on public demo: a small AWS server (free-plan credits, new project)

Hugging Face Docker Spaces need a paid plan, so the hosted demo runs on an AWS EC2 server, paid from the account's free-plan credits. It lives in its own **new project** so that nothing else in the account is touched. One Docker container serves the built React app and the API in `inline` mode, so Temporal, Prometheus and Grafana are not part of it (the Operations page says so; the walkthrough video shows them). Caddy in front gives it HTTPS on a free `<ip>.sslip.io` name.

### Create a new project (never use or change an existing project)
1. Open <https://settings.aws.com/projects> and click **Create project**. Name it `griha`.
2. Read each screen before continuing. Stop if it asks for a card, for a paid plan, or to **Upgrade plan** or **Activate advanced features**, and ask for help instead.
3. When the project is Active, use its **AWS Console** button, not Hearth's.

### Launch the server (console → EC2 → Launch instance)
1. Region: **Asia Pacific (Mumbai) ap-south-1** if available.
2. **Name:** `griha`. **Image:** Ubuntu Server 24.04 LTS.
3. **Instance type:** only one marked **Free tier eligible**, the smallest is fine (a `t3.micro` has 1 GB; the script adds swap for the build).
4. **Key pair:** create new, RSA, `.pem`, name `griha`, and keep the download: `mv ~/Downloads/griha.pem ~/.ssh/ && chmod 400 ~/.ssh/griha.pem`.
5. **Network:** auto-assign public IP on; new security group allowing **SSH (22) from My IP**, **HTTP (80)** and **HTTPS (443)** from anywhere.
6. **Storage:** 20 GiB. Launch. Copy the **Public IPv4 address** once it is Running.

### Publish
```bash
ssh -i ~/.ssh/griha.pem ubuntu@<public-ip> "echo connected"
ops/deploy-vm.sh <public-ip> ~/.ssh/griha.pem
```
The script copies the project, builds the image on the server (10 to 15 minutes on a small server), starts it, creates the two secrets on the server (never printed), and sets up HTTPS. It prints `https://<ip-with-dashes>.sslip.io`. Check with `curl -s https://<that-name>/api/health`; it should include `"public_demo":true`.

If the HTTPS certificate does not appear after a few minutes, the shared sslip.io name may be rate limited. Fallback: a free `yourname.duckdns.org` name pointing at the IP, put in `/etc/caddy/Caddyfile` on the server.

### After it is live
- Walk through: home page live case, Apply, Lender desk login, Governance (verify chain, erase), Simulator, Hindi toggle, phone width.
- Redeploy any time by running the script again. Private case links keep working because the secrets stay on the server.
- Never click **Upgrade plan**. On the free plan, services stop when credits run out instead of billing you.
- When judging is over, **terminate** the instance (EC2 → Instances → Instance state → Terminate). Do not stop and start it meanwhile: the public address changes.
- The script has not run against a real server. If a step fails, send the error text.

### Backup plan: Azure for Students
A college email gets $100 of credit with no card. Create an Ubuntu VM (username `azureuser`, ports 22, 80, 443 open), then run `SSH_USER=azureuser ops/deploy-vm.sh <public-ip> <key.pem>`. The same script works.

## 2. Full stack for a live session: Cloudflare Tunnel (free)

Runs the real Temporal, Grafana and Prometheus on your laptop and gives the audience a public URL. The laptop must stay on and awake.

```bash
brew install cloudflared
ops/start.sh
cloudflared tunnel --url http://127.0.0.1:5173
```

It prints a random `https://….trycloudflare.com` address. The Vite dev server proxies `/api` to the backend, so one tunnel is enough. Stop the tunnel with Ctrl-C when done. Do not leave it running unattended: the demo logins are reachable through it.

## Environment reference

| Variable | Purpose | Default |
|---|---|---|
| `GRIHA_ORCHESTRATOR` | `auto`, `temporal`, `inline` | `auto` (`inline` in the image) |
| `GRIHA_MASTER_KEY` | base64 32-byte key wrapping case keys | generated into the data dir |
| `GRIHA_SECRET` | signing secret for sessions and case links | generated into the data dir |
| `GRIHA_DEMO_PASSWORD` | password of the demo officer and admin (leave unset: the login screen prints the default) | `griha-demo` |
| `GRIHA_DATA_DIR` | audit log and key files | `backend/data` (`/data` in the image) |
| `GRIHA_STATIC_DIR` | serve the built frontend from the API | unset (Vite serves it in development) |
| `GRIHA_PUBLIC_DEMO` | show the synthetic-data banner and hosted wording | unset |
| `GRIHA_API_LIMIT`, `GRIHA_LOGIN_LIMIT` | requests per minute per client | 240, 10 |

## Backups and retention (DPDP Rules 2025 rule 6; KYC Directions 2025 para 47)
Take an online backup of the audit log and key store (the hash chain is verified on the copy; `master.key` is not included):

```bash
docker exec griha python -m griha.backup --data-dir /data --dest /data/backups --keep 14
```

Copy the backup folder off the machine, and keep `master.key` somewhere separate and access-controlled. A backup on the same disk does not protect against losing the disk.

`GRIHA_RETENTION_HOLD=1` (the default) makes erasure wait for the five-year record-keeping period of the KYC Directions. The public demo sets it to `0` because every record in it is synthetic; a real deployment must leave it at `1`.

## A stable, hard-to-block address: Elastic IP + CloudFront

`<ip>.sslip.io` works, but it changes whenever the server's public IP changes, and some school and office networks block it as a dynamic-DNS name. An address on `*.cloudfront.net` is AWS's own, free at this scale, and stays the same.

1. **Elastic IP (keeps the server's address fixed).** EC2 → Elastic IPs → *Allocate Elastic IP address* → *Allocate*. Select it → *Actions* → *Associate Elastic IP address* → choose the `griha` instance → *Associate*. The server's public IP changes once, to this one, and then never again. Re-run `ops/deploy-vm.sh <new-ip> ~/.ssh/griha.pem` so the sslip.io name matches.
2. **CloudFront distribution.** CloudFront → *Create distribution*, and choose the **pay-as-you-go / free** option. Never click *Upgrade plan*.
   - Origin domain: the instance's **Public IPv4 DNS** (`ec2-…compute.amazonaws.com`, from the EC2 instance page).
   - Protocol: **HTTP only**, port 80. (The server's Caddy has a catch-all `:80` block for this; visitors still get HTTPS from CloudFront.)
   - Viewer protocol policy: *Redirect HTTP to HTTPS*. Allowed methods: *GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE*.
   - Cache policy: **CachingDisabled**. Origin request policy: **AllViewer**. (The API relies on the `Authorization` and `X-Case-Key` headers and must never be cached.)
   - Web Application Firewall: leave off.
3. Wait until the distribution is *Deployed* (a few minutes). Its **Distribution domain name** (`dxxxxxxxxxxxx.cloudfront.net`) is the stable address. Check `https://<that-name>/api/health`.

Traffic between CloudFront and the server is plain HTTP over the internet. That is acceptable here because all data is synthetic. For real data, put the origin behind HTTPS with its own certificate and restrict the security group to CloudFront.
