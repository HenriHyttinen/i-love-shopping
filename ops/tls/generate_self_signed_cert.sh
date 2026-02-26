#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/certs"
CERT_FILE="${CERT_DIR}/localhost.crt"
KEY_FILE="${CERT_DIR}/localhost.key"

mkdir -p "${CERT_DIR}"

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl is required to generate certificates." >&2
  exit 1
fi

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout "${KEY_FILE}" \
  -out "${CERT_FILE}" \
  -subj "/C=FI/ST=Uusimaa/L=Helsinki/O=HardwareShop/CN=localhost"

echo "Generated:"
echo "  ${CERT_FILE}"
echo "  ${KEY_FILE}"
