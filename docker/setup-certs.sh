#!/usr/bin/env bash
set -euo pipefail
cd /usr/share/elasticsearch

case "${STACK_VERSION:-}" in
  9.*) ;;
  *) echo "This tutorial requires Elasticsearch 9.x. Follow the README migration steps for an existing .env." >&2; exit 1 ;;
esac

cert_dir=config/certs
mkdir -p "$cert_dir"
temp_dir=$(mktemp -d)
trap 'rm -rf "$temp_dir"' EXIT
ca_regenerated=false
# Persist across interrupted runs, including a crash midway through extraction.
recovery_marker="$cert_dir/.setup-incomplete"
if [[ -e "$recovery_marker" || ! -s "$cert_dir/ca/ca.crt" || ! -s "$cert_dir/ca/ca.key" ]]; then
  touch "$recovery_marker"
  echo "Creating the local certificate authority"
  bin/elasticsearch-certutil ca --silent --pem --out "$temp_dir/ca.zip"
  unzip -o "$temp_dir/ca.zip" -d "$cert_dir"
  ca_regenerated=true
fi

if [[ "$ca_regenerated" == true || ! -s "$cert_dir/elasticsearch/elasticsearch.crt" || ! -s "$cert_dir/elasticsearch/elasticsearch.key" ]]; then
  touch "$recovery_marker"
  cat > "$cert_dir/instances.yml" <<'YAML'
instances:
  - name: elasticsearch
    dns:
      - backend-elasticsearch
      - localhost
    ip:
      - 127.0.0.1
YAML
  echo "Creating the Elasticsearch certificate"
  bin/elasticsearch-certutil cert --silent --pem --out "$temp_dir/certs.zip" \
    --in "$cert_dir/instances.yml" --ca-cert "$cert_dir/ca/ca.crt" --ca-key "$cert_dir/ca/ca.key"
  unzip -o "$temp_dir/certs.zip" -d "$cert_dir"
fi

# Elastic containers run with group 0. Restrict changes to this volume only.
chown -R root:root "$cert_dir"
find "$cert_dir" -type d -exec chmod 750 {} +
find "$cert_dir" -type f -exec chmod 640 {} +
rm -f "$recovery_marker"
echo "Certificates ready"
