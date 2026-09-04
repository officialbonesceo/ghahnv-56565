#!/usr/bin/env bash
set -euo pipefail
if [ -x "${RHUBARB_DIR}/rhubarb" ]; then
  exit 0
fi
mkdir -p "${RHUBARB_DIR}" /tmp/rhubarb
curl -L --fail -o /tmp/rhubarb.zip \
  "https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v${RHUBARB_VERSION}/Rhubarb-Lip-Sync-${RHUBARB_VERSION}-Linux.zip"
unzip -o /tmp/rhubarb.zip -d /tmp/rhubarb
BIN=$(find /tmp/rhubarb -type f -name rhubarb | head -1)
cp "${BIN}" "${RHUBARB_DIR}/rhubarb"
chmod +x "${RHUBARB_DIR}/rhubarb"
DIRNAME=$(dirname "${BIN}")
cp -a "${DIRNAME}/." "${RHUBARB_DIR}/" || true
