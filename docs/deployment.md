# CV Maker — VPS Deployment Guide

## Architecture

```
Browser <--HTTPS--> Cloudflare <--HTTP--> VPS (Nginx :80) <--proxy--> Backend (:8000)
```

Cloudflare terminates TLS (Flexible SSL). Nginx serves the Vue SPA and proxies `/api/*` to FastAPI. GitHub Actions deploys on every push to `main` via SSH.

## One-Time VPS Setup

### 1. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
```

### 2. Create deploy user

```bash
useradd -m -s /bin/bash deploy
usermod -aG docker deploy
```

### 3. Clone the repo

```bash
su - deploy
mkdir -p /opt/cv-maker
git clone https://github.com/naheedroomy/cv-maker.git /opt/cv-maker/cv-maker
```

### 4. Create .env

```bash
cd /opt/cv-maker/cv-maker
cp .env.example .env
nano .env
```

Fill in these values:
```
GOOGLE_CLIENT_ID=your-production-client-id.apps.googleusercontent.com
JWT_SECRET=generate-a-long-random-string
GEMINI_API_KEY=your-gemini-key
CORS_ORIGINS=https://resume.xenohass.work
```

> **Note:** Only `GEMINI_API_KEY` is needed server-side — it powers PDF parsing/OCR.
> AI provider keys for CV tailoring (Anthropic, OpenAI, Gemini) are set by each
> user through the Settings page in the app and stored in the database.

### 5. Set up SSH key for GitHub Actions

On your **local machine**:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/cv-maker-deploy
ssh-copy-id -i ~/.ssh/cv-maker-deploy.pub deploy@YOUR_VPS_IP
```

### 6. Set GitHub Actions secrets

```bash
gh secret set VPS_HOST --body "YOUR_VPS_IP"
gh secret set VPS_USER --body "deploy"
gh secret set SSH_PRIVATE_KEY < ~/.ssh/cv-maker-deploy
```

### 7. Configure Cloudflare DNS

1. Add **A record**: `resume` → VPS IP, **Proxied** (orange cloud)
2. SSL/TLS → **Flexible**
3. Enable **Always Use HTTPS**

### 8. First deploy

```bash
git push origin main
gh run watch
```

### 9. Verify

```bash
curl -sf https://resume.xenohass.work/api/
```

## How Deploys Work

Every push to `main`:
1. GitHub Actions SSHes into VPS
2. `git pull` to get latest code
3. `docker compose build` rebuilds images locally
4. `docker compose up -d` restarts containers
5. Health check verifies backend is responding

That's it. No registry, no separate prod compose, no SCP.

## Troubleshooting

```bash
# Check container status
ssh deploy@VPS "cd /opt/cv-maker/cv-maker && docker compose ps"

# Check logs
ssh deploy@VPS "cd /opt/cv-maker/cv-maker && docker compose logs --tail 50"

# Manual redeploy
ssh deploy@VPS "cd /opt/cv-maker/cv-maker && git pull && docker compose build && docker compose up -d"
```
