# CV Maker — VPS Deployment Guide

This document covers the one-time setup required on a VPS before the GitHub Actions CI/CD pipeline can deploy automatically. After this setup, every push to `main` triggers an automated build and deploy.

## Architecture Overview

```
Browser <--HTTPS--> Cloudflare <--HTTP--> VPS (Nginx on port 80) <--proxy--> Backend (port 8000)
```

- **Cloudflare** terminates TLS (Flexible SSL mode) and proxies to the VPS over HTTP
- **Nginx** (inside the frontend Docker container) serves the Vue SPA and proxies `/api/*` to the backend
- **Backend** (FastAPI + uvicorn) runs inside a Docker container on port 8000
- **GitHub Actions** builds Docker images, pushes to GHCR, and deploys via SSH

## Prerequisites

- A VPS with a public IP address (Ubuntu 22.04+ or Debian 12+ recommended)
- Root SSH access to the VPS
- A Cloudflare account managing the `xenohass.work` domain
- The GitHub repository at `github.com/naheedroomy/cv-maker`

## Step 1: Create Deploy User

SSH into the VPS as root and create a dedicated deploy user:

```bash
# Create user with home directory
useradd -m -s /bin/bash deploy

# Add to docker group (created in Step 2)
# Run this AFTER installing Docker
usermod -aG docker deploy
```

## Step 2: Install Docker

```bash
# Install Docker using the official convenience script
curl -fsSL https://get.docker.com | sh

# Verify installation
docker --version
docker compose version

# Add deploy user to docker group (if not done in Step 1)
usermod -aG docker deploy
```

## Step 3: Set Up SSH Key Authentication

On your **local machine** (not the VPS), generate a dedicated deploy key:

```bash
# Generate ED25519 key pair
ssh-keygen -t ed25519 -a 200 -C "github-actions-deploy" -f ~/.ssh/cv-maker-deploy

# Copy the public key to VPS
ssh-copy-id -i ~/.ssh/cv-maker-deploy.pub root@YOUR_VPS_IP

# Move the authorized key to the deploy user
# (SSH into VPS as root first)
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
# Or add just the deploy key:
# echo "ssh-ed25519 AAAA... github-actions-deploy" >> /home/deploy/.ssh/authorized_keys
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh
```

## Step 4: Create App Directory

```bash
# As root on VPS
mkdir -p /opt/cv-maker
chown deploy:deploy /opt/cv-maker
```

## Step 5: Create Production .env

Create `/opt/cv-maker/.env` with production secrets:

```bash
# As the deploy user on VPS
su - deploy
cat > /opt/cv-maker/.env << 'ENVEOF'
# Authentication
GOOGLE_CLIENT_ID=your-production-client-id.apps.googleusercontent.com
JWT_SECRET=generate-with-python-c-import-secrets-print-secrets-token_urlsafe-64

# AI Providers (at least one required)
GEMINI_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...

# Optional
# OPENAI_API_KEY=sk-proj-...
ENVEOF

# Secure the file
chmod 600 /opt/cv-maker/.env
```

> **Important:** Do NOT set `CV_MAKER_DB_PATH`, `BASE_CV_PATH`, or `CORS_ORIGINS` in this file. These are set by `docker-compose.prod.yml` in the `environment:` section.

## Step 6: Authenticate Docker to GHCR

The VPS needs to pull images from GitHub Container Registry. Create a GitHub Personal Access Token (classic) with `read:packages` scope only:

1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select only the `read:packages` scope
4. Copy the token

```bash
# As the deploy user on VPS
su - deploy
echo "ghp_YOUR_READ_PACKAGES_PAT" | docker login ghcr.io -u naheedroomy --password-stdin
```

This writes `~/.docker/config.json` and persists across deploys. You only need to do this once (or when the PAT expires).

## Step 7: Set GitHub Actions Secrets

On your local machine (with `gh` CLI installed and authenticated):

```bash
# VPS connection details
gh secret set VPS_HOST --body "YOUR_VPS_IP_ADDRESS"
gh secret set VPS_USER --body "deploy"

# Private key contents (the ENTIRE file including -----BEGIN/END----- headers)
gh secret set SSH_PRIVATE_KEY < ~/.ssh/cv-maker-deploy
```

These are the **only** secrets needed. The `GITHUB_TOKEN` for GHCR push is provided automatically by GitHub Actions.

## Step 8: Configure Cloudflare DNS

1. Log in to Cloudflare dashboard
2. Select the `xenohass.work` domain
3. Go to **DNS > Records**
4. Add a new record:
   - **Type:** A
   - **Name:** `resume`
   - **IPv4 address:** Your VPS IP address
   - **Proxy status:** **Proxied** (orange cloud icon) — this enables Cloudflare SSL
   - **TTL:** Auto
5. Go to **SSL/TLS > Overview**
6. Set encryption mode to **Flexible**
7. Go to **SSL/TLS > Edge Certificates**
8. Enable **Always Use HTTPS:** ON — this redirects all HTTP requests to HTTPS (required — ensures no plain-text access)
9. Set **Minimum TLS Version:** TLS 1.2
10. Enable **Automatic HTTPS Rewrites:** ON

> **Note:** With Flexible mode, Cloudflare terminates TLS at the edge and connects to your VPS over plain HTTP (port 80). No SSL certificate is needed on the VPS. "Always Use HTTPS" ensures browsers can never access the site over plain HTTP.

## Step 9: First Deploy

After completing all steps above, trigger the first deploy:

```bash
# From your local machine, in the cv-maker repo
git push origin main
```

Or manually trigger by pushing any commit to `main`. Monitor the deploy:

```bash
# Watch the GitHub Actions run
gh run watch

# Or check the Actions tab in the browser
# https://github.com/naheedroomy/cv-maker/actions
```

### Verify the Deployment

```bash
# SSH check — containers running
ssh deploy@YOUR_VPS_IP "docker compose -f /opt/cv-maker/docker-compose.prod.yml ps"

# Local health check (from VPS)
ssh deploy@YOUR_VPS_IP "curl -sf http://localhost/api/"

# Public health check
curl -sf https://resume.xenohass.work/api/

# Full app check — open in browser
open https://resume.xenohass.work
```

## Troubleshooting

### Containers not starting
```bash
# Check logs
ssh deploy@YOUR_VPS_IP "docker compose -f /opt/cv-maker/docker-compose.prod.yml logs --tail 50"

# Check backend specifically
ssh deploy@YOUR_VPS_IP "docker compose -f /opt/cv-maker/docker-compose.prod.yml logs backend --tail 50"
```

### GHCR pull fails (401 Unauthorized)
```bash
# Re-authenticate on VPS
ssh deploy@YOUR_VPS_IP
echo "ghp_NEW_PAT" | docker login ghcr.io -u naheedroomy --password-stdin
```

### Health check fails
```bash
# Check if backend is actually running
ssh deploy@YOUR_VPS_IP "docker compose -f /opt/cv-maker/docker-compose.prod.yml ps"

# Check if the .env file exists and has correct values
ssh deploy@YOUR_VPS_IP "ls -la /opt/cv-maker/.env"

# Check backend logs for startup errors
ssh deploy@YOUR_VPS_IP "docker compose -f /opt/cv-maker/docker-compose.prod.yml logs backend"
```

### DNS not resolving
- Verify the A record in Cloudflare dashboard points to the correct VPS IP
- Ensure proxy status is "Proxied" (orange cloud)
- DNS propagation can take up to 5 minutes for Cloudflare
- Check: `dig resume.xenohass.work`

### CORS errors in browser
- Verify `CORS_ORIGINS` in `docker-compose.prod.yml` is `https://resume.xenohass.work` (with HTTPS, matching what the browser sees)
- Do NOT set `CORS_ORIGINS` in the `.env` file (it's set in compose `environment:` and would be overridden)

## File Layout on VPS

After a successful deploy, the VPS has:

```
/opt/cv-maker/
    docker-compose.prod.yml    # Synced by GitHub Actions on each deploy
    .env                       # Production secrets (manually created, Step 5)

/home/deploy/
    .docker/config.json        # GHCR authentication (Step 6)
    .ssh/authorized_keys       # Deploy key (Step 3)

# Docker-managed (do not modify directly):
# cv-data volume              # Persists SQLite DB and base CV data
```

## Maintenance

### Manual Rollback
```bash
# SSH into VPS
ssh deploy@YOUR_VPS_IP

# Pull a specific version by git SHA tag
cd /opt/cv-maker
docker compose -f docker-compose.prod.yml pull  # pulls :latest
# Or for a specific SHA:
# docker pull ghcr.io/naheedroomy/cv-maker-backend:<sha>
# docker pull ghcr.io/naheedroomy/cv-maker-frontend:<sha>
# Then edit docker-compose.prod.yml to use the SHA tag instead of :latest

docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

### Disk Cleanup
```bash
# Remove unused Docker data (images, containers, volumes not in use)
ssh deploy@YOUR_VPS_IP "docker system prune -f"

# More aggressive — also removes unused volumes (WARNING: may delete data)
# ssh deploy@YOUR_VPS_IP "docker system prune -af --volumes"
```

### Updating Cloudflare IP Ranges
Cloudflare publishes IP ranges at:
- IPv4: https://www.cloudflare.com/ips-v4
- IPv6: https://www.cloudflare.com/ips-v6

If ranges change, update `set_real_ip_from` directives in `nginx.conf` and redeploy. Check yearly — ranges rarely change. Stale ranges only affect IP logging accuracy, not functionality.
