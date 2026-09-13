#!/usr/bin/env sh
set -eu
command -v openssl >/dev/null 2>&1 || { echo 'openssl is required' >&2; exit 1; }
mkdir -p "$(dirname "$0")"
openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 7 \
  -keyout "$(dirname "$0")/server.key" \
  -out "$(dirname "$0")/server.crt" \
  -subj '/CN=universal-coder-local' \
  -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'
chmod 600 "$(dirname "$0")/server.key"
echo 'Generated short-lived development certificate. Do not use it for public production.'
