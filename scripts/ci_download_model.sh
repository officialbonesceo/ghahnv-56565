#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${MODEL_DIR}"
if [ ! -f "${MODEL_DIR}/${MODEL_FILE}" ]; then
  curl -L --fail -o "${MODEL_DIR}/${MODEL_FILE}" "${MODEL_URL}" || true
fi
if [ ! -f "${MODEL_DIR}/${MODEL_FILE}" ]; then
  curl -L --fail -o "${MODEL_DIR}/${MODEL_FILE}" \
    "https://huggingface.co/Qwen/Qwen2-0.5B-Instruct-GGUF/resolve/main/qwen2-0_5b-instruct-q4_0.gguf"
fi
ls -lh "${MODEL_DIR}" || true
