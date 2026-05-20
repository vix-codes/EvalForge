#!/bin/bash
set -euo pipefail

# EvalForge VPS Deployment Script
# Usage: ./scripts/deploy.sh [VPS_IP]

VPS_IP="${1:-143.198.160.235}"
VPS_USER="${VPS_USER:-root}"
DEPLOY_DIR="/opt/evalforge"
SSH_KEY="${SSH_KEY:-~/.ssh/id_ed25519}"

echo "==> Deploying EvalForge to ${VPS_USER}@${VPS_IP}"

# Inspect existing services on VPS before deploying
echo "==> Inspecting existing services..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${VPS_USER}@${VPS_IP}" '
  echo "=== Running containers ==="
  docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}" 2>/dev/null || echo "Docker not found or no containers"
  echo ""
  echo "=== Listening ports ==="
  ss -tlnp 2>/dev/null | head -30 || netstat -tlnp 2>/dev/null | head -30 || echo "Could not check ports"
  echo ""
  echo "=== Nginx sites ==="
  ls /etc/nginx/sites-enabled/ 2>/dev/null || ls /etc/nginx/conf.d/ 2>/dev/null || echo "Nginx not configured"
'

echo ""
echo "==> Syncing code to VPS..."
rsync -avz --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'node_modules' \
  --exclude '.env' \
  --exclude 'frontend/dist' \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  ./ "${VPS_USER}@${VPS_IP}:${DEPLOY_DIR}/"

echo "==> Running remote setup..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${VPS_USER}@${VPS_IP}" "
  set -euo pipefail
  cd ${DEPLOY_DIR}

  # Ensure .env exists
  if [ ! -f .env ]; then
    cp .env.example .env
    echo 'WARNING: Created .env from .env.example — update with real values!'
  fi

  # Install Ollama if not present
  if ! command -v ollama &>/dev/null; then
    echo '==> Installing Ollama...'
    curl -fsSL https://ollama.ai/install.sh | sh
    systemctl enable ollama --now || true
    sleep 5
  fi

  # Pull default model
  echo '==> Pulling Ollama model phi4...'
  ollama pull phi4 || echo 'WARNING: Could not pull phi4 — may need manual setup'

  # Docker Compose pull and build
  echo '==> Building Docker images...'
  docker compose pull --ignore-pull-failures || true
  docker compose build --parallel

  # Run migrations
  echo '==> Running database migrations...'
  docker compose run --rm api alembic upgrade head

  # Deploy with zero-downtime restart
  echo '==> Starting services...'
  docker compose up -d --remove-orphans

  # Install nginx config
  echo '==> Configuring Nginx...'
  cp ${DEPLOY_DIR}/nginx/evalforge.conf /etc/nginx/sites-available/evalforge 2>/dev/null || \
    cp ${DEPLOY_DIR}/nginx/evalforge.conf /etc/nginx/conf.d/evalforge.conf

  if [ -d /etc/nginx/sites-enabled ]; then
    ln -sf /etc/nginx/sites-available/evalforge /etc/nginx/sites-enabled/evalforge 2>/dev/null || true
  fi

  # Validate nginx config
  nginx -t && systemctl reload nginx

  echo '==> Deployment complete!'
  echo ''
  echo 'Services status:'
  docker compose ps
"

echo ""
echo "==> EvalForge deployed successfully to ${VPS_IP}"
echo "==> Configure your subdomain DNS to point to ${VPS_IP}"
echo "==> Update nginx/evalforge.conf with your actual domain"
echo "==> Setup SSL: certbot --nginx -d evalforge.your-domain.com"
