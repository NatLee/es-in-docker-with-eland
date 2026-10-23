#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
# Extra arguments are Docker Compose options, e.g. --env-file .env.v9.
docker compose "$@" cp backend-elasticsearch:/usr/share/elasticsearch/config/certs/ca/ca.crt ./ca.crt
chmod 644 ./ca.crt
echo "Copied the public CA certificate to ca.crt"
