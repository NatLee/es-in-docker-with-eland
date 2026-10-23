# Upgrading and migrating the tutorial

[English](UPGRADING.md) | [繁體中文](UPGRADING.zh-TW.md) | [Back to the tutorial](../README.md)

## Moving from the previous 8.x example

The new tutorial uses named volumes, an isolated Compose project name (`eland-tutorial-v9`), separate setup services, and an Elasticsearch 9.x Python environment. Your old `.env`, `es-data`, and `es-certs` are not automatically migrated. The old `PROJECT_NAME` and `MEM_LIMIT` settings have been replaced by `COMPOSE_PROJECT_NAME`, `ES_MEM_LIMIT`, and `KIBANA_MEM_LIMIT`.

For learning, create a fresh cluster and regenerate the example data. Do not attach an old 8.x data directory directly to this 9.x Compose stack. Keep the original checkout, configuration, and data if you still need the old environment.

The following path keeps your existing `.env` untouched:

```bash
python3 scripts/init_env.py --output .env.v9
```

Review `.env.v9`. Keep `STACK_VERSION=9.5.5` and a new, distinct `COMPOSE_PROJECT_NAME`. If the old stack is still running, either stop it using its original Compose configuration or change the new file to unused ports, for example `ES_PORT=19200` and `KIBANA_PORT=15601`. A different project name isolates volumes, but does not prevent host-port collisions.

```bash
docker compose --env-file .env.v9 config --quiet
docker compose --env-file .env.v9 up -d --wait --wait-timeout 300
bash dev-cp-cert.sh --env-file .env.v9
```

Create the Python environment and install packages as described in the README, then use the matching configuration for every Python command:

```bash
ELASTIC_ENV_FILE=.env.v9 python scripts/check_connection.py
ELASTIC_ENV_FILE=.env.v9 python scripts/smoke_test.py
ELASTIC_ENV_FILE=.env.v9 python -m jupyterlab
```

Python derives the URL from `ES_PORT` unless `ELASTICSEARCH_URL` overrides it. An already-running Jupyter server does not inherit later shell changes; start it with the environment above. `dev-cp-cert.sh` replaces the local public `ca.crt` with the new cluster's CA, so keep old and new client environments in separate directories if you use both.

Continue supplying `--env-file .env.v9` when viewing logs, stopping, restarting, or removing the new containers. The helper scripts accept the same Compose options:

```bash
docker compose --env-file .env.v9 ps -a
docker compose --env-file .env.v9 stop
docker compose --env-file .env.v9 start
bash dev-es-bash.sh --env-file .env.v9
```

## Keeping real data during an 8.x → 9.x upgrade

This requires a cluster upgrade plan; changing `STACK_VERSION` alone is insufficient.

1. Inventory indices, index creation versions, plugins, clients, and Kibana saved objects. Check the [supported upgrade path](https://www.elastic.co/docs/deploy-manage/upgrade/plan-upgrade) for your exact starting and target versions.
2. Configure an off-cluster snapshot repository, take a snapshot, and verify recovery on a separate cluster. This tutorial does not configure automatic backups. A copy of a running data directory is not a supported replacement for an Elasticsearch snapshot. See [snapshot and restore](https://www.elastic.co/docs/deploy-manage/tools/snapshot-and-restore).
3. Upgrade the old cluster to the latest supported `8.19.x` patch before targeting `9.5.5`. Run Kibana's Upgrade Assistant, resolve critical issues, and handle indices created before 8.0. Follow the [major upgrade preparation](https://www.elastic.co/docs/deploy-manage/upgrade/prepare-to-upgrade) instructions.
4. Rehearse the upgrade and validate your queries and data. Upgrade Elasticsearch first, followed by Kibana at the same target version. Account for downtime with this single-node topology. Follow the [Elasticsearch upgrade procedure](https://www.elastic.co/docs/deploy-manage/upgrade/deployment-or-cluster/elasticsearch) and [Kibana upgrade procedure](https://www.elastic.co/docs/deploy-manage/upgrade/deployment-or-cluster/kibana).
5. Upgrade the Python client after the server. The new 9.x client is not compatible with an 8.x cluster; keep the old Python environment available until migration completes. See [Python client compatibility](https://www.elastic.co/docs/reference/elasticsearch/clients/python#compatibility).

Elasticsearch cannot downgrade a data directory after an upgrade. Recovery means creating a separate compatible cluster and restoring the pre-upgrade snapshot, rather than selecting the older Docker tag on the upgraded volume. See the [upgrade recovery guidance](https://www.elastic.co/docs/deploy-manage/upgrade/deployment-or-cluster/elasticsearch).

## Maintaining the tutorial baseline

For each planned update:

1. Review official release notes and compatibility guidance. Choose an exact Elastic Stack version; keep Elasticsearch and Kibana aligned. Check Eland, the Elasticsearch Python client, pandas, and Python requirements together.
2. Update `.env.example`, package pins, and both READMEs. Existing private `.env` files need a deliberate local edit; they are not replaced by a template update. Preserve the generated Kibana encryption keys when reusing an existing environment.
3. Test in a separate Compose project with unused ports and a freshly created virtual environment. Run `python -m pip check`, the offline unit tests, the smoke test, and both notebooks. Verify that a second seed succeeds, counts stay stable, TLS is validated, and data survives stop/start.
4. Record the versions and actual validation results in the change description. Distinguish static checks from tests against a running cluster. Dependency update proposals still require review and validation.

The smoke test writes only the tutorial indices; it does not establish compatibility for your other data, production workload, or third-party plugins.

## Local configuration and repository history

The previously tracked `.env` is no longer version-controlled. Existing local files remain unchanged and are ignored by Git; `.env.example` is the configuration template intended for version control. New clones can create their own `.env` with `python3 scripts/init_env.py`.

Existing users can keep their private configuration and use the `.env.v9` migration path above. Removing Git tracking does not alter running services or account passwords. If a real credential was previously published, rotate it; removing the current file does not remove historical copies.

CI checks tracked filenames and rejects local `.env` / `.env.*` files while allowing `.env.example`; it does not read their contents.
