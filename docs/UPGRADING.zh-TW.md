# 升級與遷移教學環境

[English](UPGRADING.md) | [繁體中文](UPGRADING.zh-TW.md) | [回到教學](../README.zh-TW.md)

## 從舊版 8.x 範例轉移

新版使用 named volumes、獨立的 Compose 專案名稱 `eland-tutorial-v9`、分離的初始化服務，以及 Elasticsearch 9.x 的 Python 環境。原本的 `.env`、`es-data`、`es-certs` 不會自動遷移。舊設定 `PROJECT_NAME`、`MEM_LIMIT` 已由 `COMPOSE_PROJECT_NAME`、`ES_MEM_LIMIT`、`KIBANA_MEM_LIMIT` 取代。

若目的是學習，可建立全新叢集並重新產生範例資料。不要把舊 8.x 資料目錄直接掛到這份 9.x Compose 設定。仍需使用舊環境時，請保留原本的程式碼、設定與資料。

以下方式會保留既有 `.env`：

```bash
python3 scripts/init_env.py --output .env.v9
```

檢查 `.env.v9`，保留 `STACK_VERSION=9.5.5`，並使用不同的 `COMPOSE_PROJECT_NAME`。舊服務仍在執行時，請用原本的 Compose 設定停止它，或在新檔案設定未使用的連接埠，例如 `ES_PORT=19200`、`KIBANA_PORT=15601`。不同專案名稱能隔離資料卷，但無法避免主機連接埠衝突。

```bash
docker compose --env-file .env.v9 config --quiet
docker compose --env-file .env.v9 up -d --wait --wait-timeout 300
bash dev-cp-cert.sh --env-file .env.v9
```

依 README 建立 Python 環境並安裝套件，再於每個 Python 指令指定同一份設定檔：

```bash
ELASTIC_ENV_FILE=.env.v9 python scripts/check_connection.py
ELASTIC_ENV_FILE=.env.v9 python scripts/smoke_test.py
ELASTIC_ENV_FILE=.env.v9 python -m jupyterlab
```

若沒有另外設定 `ELASTICSEARCH_URL`，Python 會依 `ES_PORT` 建立網址。已啟動的 Jupyter 不會取得後續 shell 變更，請以上述方式啟動。`dev-cp-cert.sh` 會把本機公開的 `ca.crt` 換成新叢集的 CA；若要同時操作新舊叢集，請將兩套用戶端環境放在不同目錄。

查看日誌、停止、重啟或移除新容器時，都要繼續指定 `--env-file .env.v9`。輔助腳本也接受相同的 Compose 選項：

```bash
docker compose --env-file .env.v9 ps -a
docker compose --env-file .env.v9 stop
docker compose --env-file .env.v9 start
bash dev-es-bash.sh --env-file .env.v9
```

## 需要保留真實資料的 8.x → 9.x 升級

這需要完整的叢集升級規劃，不能只修改 `STACK_VERSION`。

1. 盤點索引、索引建立版本、外掛、用戶端與 Kibana saved objects。先依確切的起點和目標版本確認[支援的升級路徑](https://www.elastic.co/docs/deploy-manage/upgrade/plan-upgrade)。
2. 設定叢集外的 snapshot repository、建立快照，並在獨立叢集驗證還原。本教學沒有設定自動備份。複製執行中的資料目錄不能取代 Elasticsearch 支援的快照備份。詳見[快照與還原](https://www.elastic.co/docs/deploy-manage/tools/snapshot-and-restore)。
3. 升級到 `9.5.5` 前，先將舊叢集升至最新支援的 `8.19.x` 修補版本。執行 Kibana Upgrade Assistant、解決 critical 項目，並處理 8.0 以前建立的索引。請依[主版本升級準備](https://www.elastic.co/docs/deploy-manage/upgrade/prepare-to-upgrade)完成檢查。
4. 在測試環境演練，驗證查詢與資料。先升級 Elasticsearch，再升級相同目標版本的 Kibana；本專案為單節點，需安排停機。依[Elasticsearch 升級程序](https://www.elastic.co/docs/deploy-manage/upgrade/deployment-or-cluster/elasticsearch)與 [Kibana 升級程序](https://www.elastic.co/docs/deploy-manage/upgrade/deployment-or-cluster/kibana)操作。
5. 伺服器升級完成後才升級 Python client。新版 9.x client 不相容於 8.x 叢集，遷移完成前請保留舊 Python 環境。詳見 [Python client 相容性](https://www.elastic.co/docs/reference/elasticsearch/clients/python#compatibility)。

Elasticsearch 無法將升級後的資料目錄降版。需要復原時，應建立獨立且相容的叢集，還原升級前快照，不能只把既有資料卷搭配的 Docker tag 改回舊版。詳見[升級復原說明](https://www.elastic.co/docs/deploy-manage/upgrade/deployment-or-cluster/elasticsearch)。

## 持續維護教學版本

每次規劃更新時：

1. 閱讀官方版本說明與相容性文件，選定明確的 Elastic Stack 版本，維持 Elasticsearch 與 Kibana 一致；同時檢查 Eland、Elasticsearch Python client、pandas 與 Python 需求。
2. 更新 `.env.example`、套件版本及兩份 README。使用者的私人 `.env` 需自行調整，模板更新不會覆寫它；繼續使用既有環境時，請保留已產生的 Kibana 加密金鑰。
3. 使用獨立 Compose 專案、未使用的連接埠與全新虛擬環境驗證。執行 `python -m pip check`、離線單元測試、smoke test 與兩份 Notebook。確認重跑不會累加筆數、TLS 驗證正常，且停止／啟動後資料仍存在。
4. 在變更說明中記錄版本與實際驗證結果，清楚區分靜態檢查與連線叢集測試。自動提出的套件更新仍需審查與驗證。

Smoke test 只寫入教學索引，無法據此保證其他資料、正式環境負載或第三方外掛的相容性。

## 本機設定與 Git 歷史

原本納入追蹤的 `.env` 已停止版本控制，既有本機檔案內容保持不變，並由 Git 忽略。設定模板只將 `.env.example` 納入版本控制；新 clone 的使用者可執行 `python3 scripts/init_env.py` 建立自己的 `.env`。

既有使用者可保留私人設定，並使用上方的 `.env.v9` 遷移流程。停止 Git 追蹤不會更動執行中的服務或帳號密碼。若真實憑證曾被公開，應更換憑證；移除目前檔案不會消除歷史版本。

CI 會檢查已追蹤的檔名，拒絕加入本機 `.env`／`.env.*`，並允許 `.env.example`；此檢查不會讀取檔案內容。
