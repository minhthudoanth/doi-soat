#!/usr/bin/env bash
# ================================================================
# SCRIPT TRIEN KHAI WEB SCM DASHBOARD TREN SERVER NOI BO KINGFOOD
# ================================================================
set -e

echo "=== [1/4] Kiem tra Docker & Docker Compose ==="
if ! command -v docker &> /dev/null; then
    echo "[!] Docker chua duoc cai dat. Dang cai dat Docker tu dong..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

echo "=== [2/4] Cap nhat ma nguon moi nhat tu GitHub ==="
if [ -d ".git" ]; then
    git pull origin main
else
    git clone https://github.com/minhthudoanth/doi-soat.git /opt/kingfood_scm_bot
    cd /opt/kingfood_scm_bot
fi

echo "=== [3/4] Khoi chay he thong bang Docker Compose ==="
if command -v docker-compose &> /dev/null; then
    docker-compose down || true
    docker-compose up -d --build
else
    docker compose down || true
    docker compose up -d --build
fi

echo "=== [4/4] Kiem tra trang thai ==="
sleep 3
docker ps | grep kingfood_scm_web

echo "================================================================"
echo "  TRIEN KHAI THANH CONG TREN SERVER NOI BO!"
echo "  Truy cap Web tai: http://$(hostname -I | awk '{print $1}'):5000"
echo "================================================================"
