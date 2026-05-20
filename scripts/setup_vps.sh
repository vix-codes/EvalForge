#!/bin/bash
set -euo pipefail

# VPS Initial Setup Script for EvalForge
# Run once on fresh VPS: bash setup_vps.sh

echo "==> EvalForge VPS Setup"

# Update system
apt-get update -y && apt-get upgrade -y

# Install prerequisites
apt-get install -y \
  curl \
  git \
  nginx \
  certbot \
  python3-certbot-nginx \
  rsync \
  htop \
  jq \
  ufw

# Install Docker
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker --now
  usermod -aG docker "$USER" || true
fi

# Install Docker Compose plugin
if ! docker compose version &>/dev/null 2>&1; then
  apt-get install -y docker-compose-plugin || \
  curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose && \
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

# Install Ollama
if ! command -v ollama &>/dev/null; then
  curl -fsSL https://ollama.ai/install.sh | sh
  systemctl enable ollama --now
fi

# Configure firewall (don't block existing rules)
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw --force enable || true

# Create deploy directory
mkdir -p /opt/evalforge

echo ""
echo "==> VPS setup complete!"
echo "==> Next: run ./scripts/deploy.sh"
