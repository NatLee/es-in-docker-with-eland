# Elasticsearch in Docker with Eland

[English](README.md) | [繁體中文](README.zh-TW.md)

A local tutorial for connecting Python to Elasticsearch, exploring indexed data with Eland, and understanding when to use pandas. The examples generate reproducible data without downloading an external dataset.

The stack contains one Elasticsearch node and Kibana with a Basic license. Elasticsearch uses HTTPS and authentication; Python verifies the generated CA certificate. Both published ports bind to `127.0.0.1`. Kibana's browser endpoint uses HTTP, so this configuration is intended for learning on your own machine.

## Versions and prerequisites

| Component | Tutorial baseline |
| --- | --- |
| Elasticsearch and Kibana | `9.5.5`, pinned together in [.env.example](.env.example) |
| Eland | `9.2.0`; package pins are in [requirements.txt](requirements.txt) |
| Python | `3.11`–`3.13`; use `3.12` for the integration-tested baseline |
| Docker | Docker Engine or Docker Desktop, with the `docker compose` plugin supporting `up --wait` |
| Memory | Allocate at least 4 GB to Docker; allow additional memory for Jupyter |

The Elastic version was checked against the [official Docker guide](https://www.elastic.co/docs/deploy-manage/deploy/self-managed/install-elasticsearch-docker-compose) on 2026-10-23. Exact pins make the starting point explicit; future releases still need compatibility checks and validation.

**Eland's latest stable release is `9.2.0`**, checked on 2026-10-23; it was published on 2025-10-30. This tutorial upgrades its previous `8.15.0` pin to `9.2.0`. The release adds NumPy 2 and Python 3.13 support and drops Python 3.9. See [PyPI](https://pypi.org/project/eland/) and the [official release notes](https://github.com/elastic/eland/releases/tag/v9.2.0).

Eland and Elasticsearch have independent release versions: matching major versions is sufficient for these DataFrame examples, so Eland 9.2.0 can accompany Elasticsearch 9.5.5. NLP/PyTorch model imports require matching minor versions and are outside this tutorial. Eland requires Python `>=3.10,<3.14` and supports pandas 1.5/2; this project's dependency baseline uses Python 3.11–3.13 and pandas 2. See [Eland compatibility](https://github.com/elastic/eland/tree/v9.2.0#compatibility).

On Linux, check `sysctl vm.max_map_count`. If it is below `1048576`, apply `sudo sysctl -w vm.max_map_count=1048576` and configure persistence for your host. On Docker Desktop or WSL, the setting belongs to the Docker Linux VM. Follow Elastic's [platform-specific instructions](https://www.elastic.co/docs/deploy-manage/deploy/self-managed/install-elasticsearch-docker-prod#set-vm-max-map-count); do not run Linux kernel commands on the macOS host.

## Quick start: a new environment

Run commands from the repository root using bash or zsh; Windows users can use WSL. **If you already have an `.env` or data from the old 8.x tutorial, follow the [migration guide](docs/UPGRADING.md) first.**

1. Create the local configuration:

   ```bash
   python3 scripts/init_env.py
   ```

   This reads the tracked `.env.example` template, generates passwords and stable Kibana encryption keys, and creates a private, Git-ignored `.env`. It refuses to overwrite an existing file. Review the settings in your editor and keep the file private. `ELASTIC_PASSWORD` is the `elastic` login password; `KIBANA_PASSWORD` is for the internal `kibana_system` account.

2. Validate and start the services:

   ```bash
   docker compose config --quiet
   docker compose up -d --wait --wait-timeout 300
   docker compose ps -a
   ```

   The first image download may take several minutes. `backend-es-setup` creates certificates and exits; Elasticsearch starts next; `backend-kibana-setup` initializes the service account and exits; then Kibana starts. Exit code `0` for the two setup services is expected. Named Docker volumes store data and certificates; no `es-data` directory or permission changes are needed.

3. Copy the public CA certificate:

   ```bash
   bash dev-cp-cert.sh
   ```

   This writes `ca.crt` in the repository root without exporting private keys. Repeat after switching clusters or regenerating certificates.

4. Create a Python environment and install packages:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   python -m pip check
   ```

   Ensure `python3` refers to a supported version; substitute `python3.12` if needed. A Conda environment with Python 3.12 also works with the same pip installation commands.

5. Check the connection and exercise the examples:

   ```bash
   python scripts/check_connection.py
   python scripts/smoke_test.py
   ```

   The connection check is read-only. It rejects red cluster health; yellow can occur on a single node when replica shards cannot be assigned. The smoke test writes the two tutorial indices below, verifies mappings, filters, aggregations, and retrieval beyond 10,000 rows, and leaves the data for inspection. Rerunning uses stable document IDs; it does not delete indices.

6. Start Jupyter and run the notebooks from top to bottom:

   ```bash
   python -m jupyterlab
   ```

   Use the Python kernel from the environment where you installed the packages.

Open [Kibana](http://localhost:5601) and sign in as `elastic` using your local `ELASTIC_PASSWORD`. `kibana_system` is not a browser login. The Elasticsearch API uses `https://localhost:9200`; use the Python connection check to verify its private CA and authentication.

## Learning path

| Notebook | Data and concepts |
| --- | --- |
| [eland-test.ipynb](notebooks/eland-test.ipynb) | 1,000 fictional flights: explicit mappings, Eland filters and aggregations, a bounded pandas plot, and an equivalent Elasticsearch aggregation |
| [eland-over-10000-test.ipynb](notebooks/eland-over-10000-test.ipynb) | 20,000 events: counts beyond 10,000, UTC time ranges, boolean/text queries, server-side sorting, grouped statistics, and pandas export |

The notebooks and smoke test share `eland-tutorial-flights-v1` and `eland-tutorial-events-v1`. Seeding checks tutorial ownership metadata and expected mappings before writing. Reserve these indices for sample data: rerunning overwrites sample document IDs; extra documents can change expected counts.

| Tool | Data location | Use it for |
| --- | --- | --- |
| Elasticsearch Python client | Elasticsearch | Index management, explicit Query DSL, sorting, and full API access |
| Eland DataFrame | Elasticsearch; supported operations run on the server | Familiar DataFrame filters and aggregations without first downloading all documents |
| pandas DataFrame | Your Python process | Local transformations and plotting after fetching a bounded result |

Eland implements part of pandas' API. Creating an Eland DataFrame does not download the entire index; `ed.eland_to_pandas(...)` materializes selected rows and needs local memory. Filter and select columns before conversion. See the [Eland DataFrame documentation](https://eland.readthedocs.io/en/latest/reference/dataframe.html).

**10,000 is a default search pagination boundary, not an index capacity limit.** Counts and aggregations can cover more documents. `track_total_hits=True` affects count accuracy, not the number of returned hits. For application pagination beyond this boundary, use `search_after` with a point in time as described in [Elastic's pagination guide](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/paginate-search-results). The large notebook retrieves data without increasing `index.max_result_window`.

## Configuration and everyday commands

| Setting | Purpose |
| --- | --- |
| `STACK_VERSION` | One pinned version for Elasticsearch and Kibana |
| `COMPOSE_PROJECT_NAME` | Defaults to `eland-tutorial-v9`; determines the named volumes |
| `ES_PORT`, `KIBANA_PORT` | Host ports; defaults `9200`, `5601` |
| `ES_MEM_LIMIT`, `KIBANA_MEM_LIMIT` | Container memory limits; defaults `2g`, `1g` |
| `KIBANA_SECURITY_KEY`, `KIBANA_SAVED_OBJECTS_KEY`, `KIBANA_REPORTING_KEY` | Generated encryption keys; preserve them when reusing the environment |
| `ELASTIC_CA_CERT` | Python CA file, default `ca.crt`; relative to the repository root |
| `ELASTICSEARCH_URL` | Optional Python endpoint override; otherwise HTTPS on localhost using `ES_PORT` |
| `ELASTIC_ENV_FILE` | Optional Python config file, such as `.env.v9`; pair with Compose's `--env-file` |

Exported shell variables override `.env`; stale exports can select unexpected settings. Changing `ELASTIC_PASSWORD` in `.env` does not reset the password stored in an existing data volume.

```bash
# Inspect startup problems.
docker compose logs --tail=100 backend-es-setup backend-elasticsearch backend-kibana-setup backend-kibana

# Pause and resume the existing environment.
docker compose stop
docker compose start

# Apply configuration changes and wait for readiness.
docker compose up -d --wait --wait-timeout 300

# Remove containers and network, preserving named volumes.
docker compose down

# Open a shell in Elasticsearch.
bash dev-es-bash.sh
```

Keep the same project name to reuse your data. Adding `--volumes` to `docker compose down`, or deleting project volumes in Docker Desktop, removes data and certificates; this is not a routine restart.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Startup timeout / unhealthy services | Inspect `docker compose ps -a` and logs. Confirm Docker memory and `vm.max_map_count`; initial image downloads may take longer. |
| `401` / authentication failure | Use `elastic` and this volume's original password. Check shell overrides and the selected env file. Changing bootstrap configuration does not reset an existing account. |
| Missing CA / certificate verification failure | Run `bash dev-cp-cert.sh` for the same project, check `ELASTIC_CA_CERT`, and use `localhost` or `127.0.0.1`. Keep certificate verification enabled. |
| Kibana URL fails | Use `http://localhost:5601` and confirm Kibana setup completed. |
| Port already allocated | Stop the service using it, or change `ES_PORT` / `KIBANA_PORT` and use the new URLs. |
| Read-only index / disk watermarks | Free space in Docker's disk allocation and inspect logs; keep disk protection enabled. |
| ARM JVM SVE-related illegal instruction | Update Docker and inspect the JVM crash log. Only for this identified issue, set `ES_JAVA_OPTS=-XX:UseSVE=0` and recreate services. |
| Notebook import errors / old packages | Select the `.venv` kernel, restart after package changes, and run `python -m pip check`. |
| Incompatible tutorial index mapping | Create an isolated environment with a new `COMPOSE_PROJECT_NAME`; inspect existing data before manually deleting anything. |

## Validation and maintenance

Run offline checks after changing Python examples:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Run `python scripts/smoke_test.py` against a healthy local cluster for integration coverage, then run both notebooks from clean kernels. Static checks and unit tests alone do not verify Docker startup or a live connection.

Validated on 2026-10-23 with ARM64 Docker and Python 3.12.9: Elasticsearch/Kibana 9.5.5 reached healthy status, all 21 unit tests passed, both notebooks executed completely, 20,000 rows exported, and data survived container recreation. Recovery after interrupted certificate initialization was also verified.

[GitHub Actions](.github/workflows/ci.yml) runs for pushes to `main`, all pull requests, manual runs, and a monthly schedule. Python 3.11/3.13 unit tests must pass before the Python 3.12 integration job starts Docker, runs the smoke test twice, and executes both notebooks. New commits cancel superseded runs. Actions use pinned commit SHAs, and integration failure diagnostics are retained for seven days.

[Dependabot](.github/dependabot.yml) checks pip and Actions updates weekly and groups updates within each ecosystem. Major pip package upgrades require a separate compatibility review.

NumPy is pinned to `2.4.6`, which supports Python 3.11. Dependabot excludes NumPy `>=2.5` because that series requires Python 3.12 or later. Revisit this limit when changing the tutorial's minimum Python version; even minor package updates must pass the full Python matrix. See the [NumPy 2.4.6](https://pypi.org/project/numpy/2.4.6/) and [2.5.4](https://pypi.org/project/numpy/2.5.4/) package metadata.

For future dependency updates, migration, and preserving existing data, see [Upgrading and migration](docs/UPGRADING.md).
