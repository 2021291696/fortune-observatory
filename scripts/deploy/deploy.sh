#!/usr/bin/env bash
# deploy.sh —— destiny 在服务器上执行（由本地打包上传后调用，也可手动跑）
# 职责：解压新版本 → uv sync → 装 systemd/nginx 配置 → 重启
# 铁律：绝不覆盖 /opt/destiny/.env（密钥只在服务器上）
set -euo pipefail

APP_DIR="/opt/destiny"
APP_USER="destiny"
TARBALL="${1:-/tmp/destiny.tar.gz}"

if [[ ! -f "$TARBALL" ]]; then
  echo "找不到上传包 $TARBALL" >&2
  exit 1
fi

echo "==> 1/5 解压新版本"
STAGE="$(mktemp -d)"
sudo tar -xzf "$TARBALL" -C "$STAGE"
sudo mkdir -p "$APP_DIR"
sudo cp -r "$STAGE"/. "$APP_DIR"/
sudo rm -rf "$STAGE"
sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> 2/5 uv sync（对齐 Python 依赖）"
cd "$APP_DIR"
sudo -u "$APP_USER" -H uv sync --frozen || sudo -u "$APP_USER" -H uv sync

echo "==> 3/5 安装 systemd 与 nginx 配置"
sudo install -m 0644 "$APP_DIR/scripts/deploy/destiny.service" /etc/systemd/system/destiny.service
sudo install -m 0644 "$APP_DIR/scripts/deploy/destiny.nginx" /etc/nginx/sites-available/destiny
sudo ln -sf /etc/nginx/sites-available/destiny /etc/nginx/sites-enabled/destiny
sudo systemctl daemon-reload
sudo nginx -t

echo "==> 4/5 重启服务"
sudo chmod 600 "$APP_DIR/.env" 2>/dev/null || true
sudo systemctl enable destiny
sudo systemctl restart destiny
sudo systemctl reload nginx || sudo systemctl restart nginx

echo "==> 5/5 域名 HTTPS：certbot 的 SSL 配置会被第 3 步模板覆盖，检测到证书就重挂（幂等）"
if command -v certbot >/dev/null 2>&1 && certbot certificates 2>/dev/null | grep -q "destiny.solplum.com"; then
  sudo certbot --nginx -d destiny.solplum.com --non-interactive \
    || echo "!! certbot 重挂失败，站点暂时回退 HTTP，手动跑：sudo certbot --nginx -d destiny.solplum.com"
fi

for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8742/api/health >/dev/null 2>&1; then
    echo "部署完成，/api/health 就绪。验收：bash $APP_DIR/scripts/deploy/verify.sh 2>/dev/null || curl -s http://127.0.0.1:8742/api/health"
    exit 0
  fi
  sleep 1
done
echo "!! 服务 30 秒内未就绪，查日志：journalctl -u destiny -n 50" >&2
exit 1
