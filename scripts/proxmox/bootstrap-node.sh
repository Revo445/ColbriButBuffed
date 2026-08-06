#!/usr/bin/env bash
# Bootstrap a ColbriButBuffed inference node for Proxmox (Debian/Ubuntu).
# Usage: sudo bash scripts/proxmox/bootstrap-node.sh /models/glm52_i4 [/opt/ColbriButBuffed]
set -euo pipefail

MODEL_DIR=${1:-/models/glm52_i4}
REPO_DIR=${2:-/opt/ColbriButBuffed}
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

if [[ $EUID -ne 0 ]]; then
  echo "run as root (sudo)" >&2
  exit 1
fi

id colibri &>/dev/null || useradd --system --home /var/lib/colibri --create-home --shell /usr/sbin/nologin colibri
mkdir -p "$MODEL_DIR" /var/lib/colibri
chown -R colibri:colibri "$MODEL_DIR" /var/lib/colibri

if [[ ! -d "$REPO_DIR/c" ]]; then
  echo "repo not found at $REPO_DIR — clone ColbriButBuffed there first" >&2
  exit 1
fi
chown -R colibri:colibri "$REPO_DIR" || true

UNIT=/etc/systemd/system/coli-serve.service
cp "$SCRIPT_DIR/coli-serve.service" "$UNIT"
# Rewrite paths in the installed unit
sed -i "s|/opt/ColbriButBuffed|$REPO_DIR|g" "$UNIT"
sed -i "s|/models/glm52_i4|$MODEL_DIR|g" "$UNIT"

systemctl daemon-reload
systemctl enable coli-serve.service

echo "Installed coli-serve.service"
echo "  model dir: $MODEL_DIR"
echo "  repo:      $REPO_DIR"
echo
echo "Next:"
echo "  1) Put the GLM-5.2 Colibri int4 container on LOCAL NVMe at $MODEL_DIR"
echo "  2) python3 $REPO_DIR/c/coli doctor --model $MODEL_DIR --policy lowspec"
echo "  3) systemctl start coli-serve"
echo "  4) On the gateway: set COLI_BACKENDS and start coli-cluster-lb.service"
echo
echo "See docs/proxmox-cluster.md"
