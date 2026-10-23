# 在 Docker 中使用 Elasticsearch 與 Eland

[English](README.md) | [繁體中文](README.zh-TW.md)

這個專案提供本機教學環境，練習以 Python 連線 Elasticsearch、使用 Eland 分析索引中的資料，以及判斷何時該轉成 pandas。範例會自行產生可重現的資料，不需要另外下載資料集。

環境包含單節點 Elasticsearch、Kibana 與 Basic 授權。Elasticsearch 啟用 HTTPS 和帳號驗證，Python 會驗證產生的 CA 憑證。對外連接埠皆綁定 `127.0.0.1`；Kibana 的瀏覽器端使用 HTTP，因此這份設定適合在自己的電腦上學習。

## 版本與環境需求

| 元件 | 教學基準 |
| --- | --- |
| Elasticsearch 與 Kibana | `9.5.5`，在 [.env.example](.env.example) 中統一固定版本 |
| Eland | `9.2.0`；套件版本見 [requirements.txt](requirements.txt) |
| Python | `3.11`–`3.13`；建議使用已進行整合驗證的 `3.12` |
| Docker | Docker Engine 或 Docker Desktop，以及支援 `up --wait` 的 `docker compose` 外掛 |
| 記憶體 | 至少分配 4 GB 給 Docker，並為 Jupyter 保留額外記憶體 |

Elastic 版本於 2026-10-23 依[官方 Docker 文件](https://www.elastic.co/docs/deploy-manage/deploy/self-managed/install-elasticsearch-docker-compose)確認。固定版本提供明確起點，後續更新仍需檢查相容性並驗證。

**截至 2026-10-23，Eland 最新穩定版為 `9.2.0`**，發布日期是 2025-10-30。本教學已從原本的 `8.15.0` 升至 `9.2.0`；新版加入 NumPy 2、Python 3.13 支援，並停止支援 Python 3.9。來源：[PyPI](https://pypi.org/project/eland/) 與[官方版本說明](https://github.com/elastic/eland/releases/tag/v9.2.0)。

Eland 與 Elasticsearch 各自發布版本：這些 DataFrame 範例只需匹配主版本，因此 Eland 9.2.0 可搭配 Elasticsearch 9.5.5；NLP／PyTorch 模型匯入要求次版本一致，不在本教學範圍。Eland 要求 Python `>=3.10,<3.14`，支援 pandas 1.5／2；本專案的套件組合使用 Python 3.11–3.13 與 pandas 2。詳見 [Eland 相容性說明](https://github.com/elastic/eland/tree/v9.2.0#compatibility)。

Linux 請先檢查 `sysctl vm.max_map_count`。若低於 `1048576`，執行 `sudo sysctl -w vm.max_map_count=1048576`，並依系統設定持久化。Docker Desktop／WSL 的設定對象是 Docker 使用的 Linux 虛擬機；請參考[各平台設定方式](https://www.elastic.co/docs/deploy-manage/deploy/self-managed/install-elasticsearch-docker-prod#set-vm-max-map-count)，不要直接在 macOS 主機執行 Linux 核心設定指令。

## 快速開始：建立新環境

以下指令請在專案根目錄使用 bash 或 zsh 執行；Windows 可使用 WSL。**若已經有 `.env` 或舊版 8.x 教學資料，請先閱讀[遷移指南](docs/UPGRADING.zh-TW.md)。**

1. 建立本機設定：

   ```bash
   python3 scripts/init_env.py
   ```

   程式會讀取納入版本控制的 `.env.example`、產生隨機密碼與固定的 Kibana 加密金鑰，並建立限制檔案權限、由 Git 忽略的 `.env`；檔案已存在時會拒絕覆寫。請以編輯器檢查設定並妥善保管。`ELASTIC_PASSWORD` 是 `elastic` 的登入密碼；`KIBANA_PASSWORD` 供內部 `kibana_system` 帳號使用。

2. 檢查設定並啟動服務：

   ```bash
   docker compose config --quiet
   docker compose up -d --wait --wait-timeout 300
   docker compose ps -a
   ```

   首次下載映像檔可能花費數分鐘。`backend-es-setup` 建立憑證後結束，接著 Elasticsearch 啟動；`backend-kibana-setup` 設定服務帳號後結束，最後啟動 Kibana。兩個 setup 服務結束且代碼為 `0` 是正常行為。資料與憑證存於 Docker named volumes，不需要建立 `es-data` 資料夾或修改目錄權限。

3. 複製公開 CA 憑證：

   ```bash
   bash dev-cp-cert.sh
   ```

   憑證存於專案根目錄的 `ca.crt`，程式不會匯出私鑰。切換叢集或重新產生憑證後，請再次執行。

4. 建立 Python 環境並安裝套件：

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   python -m pip check
   ```

   請確認 `python3` 指向支援的版本，必要時改用 `python3.12`。也可以建立 Python 3.12 的 Conda 環境，再執行相同的 pip 安裝指令。

5. 檢查連線並驗證範例：

   ```bash
   python scripts/check_connection.py
   python scripts/smoke_test.py
   ```

   連線檢查只讀取資訊，會拒絕 red 的叢集健康狀態；單節點無法配置副本分片時可能顯示 yellow。Smoke test 會寫入下方列出的兩個教學索引，驗證 mapping、篩選、聚合及超過 10,000 筆的讀取，並保留資料供觀察。重跑使用固定文件 ID，不會刪除索引。

6. 啟動 Jupyter，由上而下執行 Notebook：

   ```bash
   python -m jupyterlab
   ```

   請選用已安裝上述套件的 Python kernel。

開啟 [Kibana](http://localhost:5601)，使用 `elastic` 與本機的 `ELASTIC_PASSWORD` 登入。`kibana_system` 不是瀏覽器登入帳號。Elasticsearch API 使用 `https://localhost:9200`；請透過 Python 連線檢查驗證其私人 CA 與帳密。

## 學習路徑

| Notebook | 資料與教學內容 |
| --- | --- |
| [eland-test.ipynb](notebooks/eland-test.ipynb) | 1,000 筆虛構航班：明確定義 mapping、Eland 篩選與聚合、有限資料的 pandas 繪圖，以及對應的 Elasticsearch 聚合 |
| [eland-over-10000-test.ipynb](notebooks/eland-over-10000-test.ipynb) | 20,000 筆事件：超過 10,000 筆的計數、UTC 時間區間、布林與文字查詢、伺服器排序、分組統計及 pandas 匯出 |

Notebook 與 smoke test 共用 `eland-tutorial-flights-v1`、`eland-tutorial-events-v1`。寫入前會檢查教學專用的擁有權標記與 mapping。這兩個索引請只放範例資料：重跑會覆寫相同文件 ID，額外加入的文件會影響預期筆數。

| 工具 | 資料位置 | 適合用途 |
| --- | --- | --- |
| Elasticsearch Python client | Elasticsearch | 索引管理、明確的 Query DSL、排序及完整 API 操作 |
| Eland DataFrame | Elasticsearch；支援的操作由伺服器執行 | 用熟悉的 DataFrame 語法篩選與聚合，不必先下載全部文件 |
| pandas DataFrame | 本機 Python 程序 | 取回有限資料後，在本機轉換與繪圖 |

Eland 支援 pandas API 的一部分。建立 Eland DataFrame 不會下載整個索引；`ed.eland_to_pandas(...)` 才會把所選資料載入本機記憶體。轉換前應先篩選資料與欄位。詳見 [Eland DataFrame 文件](https://eland.readthedocs.io/en/latest/reference/dataframe.html)。

**10,000 是預設搜尋分頁範圍，不是索引容量上限。** 計數與聚合可以涵蓋更多文件；`track_total_hits=True` 影響總筆數精確度，不會增加回傳文件數。應用程式需要深度分頁時，可依[官方分頁指南](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/paginate-search-results)使用 `search_after` 與 point in time。大量資料 Notebook 不會調高 `index.max_result_window`。

## 設定與日常操作

| 設定 | 用途 |
| --- | --- |
| `STACK_VERSION` | 統一固定 Elasticsearch 與 Kibana 版本 |
| `COMPOSE_PROJECT_NAME` | 預設 `eland-tutorial-v9`，決定使用的 named volumes |
| `ES_PORT`、`KIBANA_PORT` | 主機連接埠，預設 `9200`、`5601` |
| `ES_MEM_LIMIT`、`KIBANA_MEM_LIMIT` | 容器記憶體上限，預設 `2g`、`1g` |
| `KIBANA_SECURITY_KEY`、`KIBANA_SAVED_OBJECTS_KEY`、`KIBANA_REPORTING_KEY` | 自動產生的加密金鑰；繼續使用同一環境時請保留 |
| `ELASTIC_CA_CERT` | Python 使用的 CA，預設 `ca.crt`；相對於專案根目錄 |
| `ELASTICSEARCH_URL` | 可選的 Python 端點；未設定時使用 localhost、HTTPS 與 `ES_PORT` |
| `ELASTIC_ENV_FILE` | 可選的 Python 設定檔，如 `.env.v9`；搭配 Compose 的 `--env-file` |

Shell 中已匯出的環境變數優先於 `.env`，殘留設定可能造成非預期的連線。修改 `.env` 裡的 `ELASTIC_PASSWORD`，不會重設既有資料卷中儲存的帳號密碼。

```bash
# 查看啟動問題。
docker compose logs --tail=100 backend-es-setup backend-elasticsearch backend-kibana-setup backend-kibana

# 暫停及恢復既有環境。
docker compose stop
docker compose start

# 套用設定變更並等待服務就緒。
docker compose up -d --wait --wait-timeout 300

# 移除容器與網路，保留 named volumes。
docker compose down

# 進入 Elasticsearch 容器。
bash dev-es-bash.sh
```

保留相同專案名稱才能繼續使用原本資料。對 `docker compose down` 加上 `--volumes`，或在 Docker Desktop 刪除專案資料卷，會移除資料與憑證；日常重啟不需要這些操作。

## 常見問題

| 問題 | 檢查方式 |
| --- | --- |
| 啟動逾時／服務 unhealthy | 查看 `docker compose ps -a` 與日誌，確認 Docker 記憶體和 `vm.max_map_count`；首次下載映像檔可能較久。 |
| `401`／帳密驗證失敗 | 使用 `elastic` 與此資料卷原有的密碼，檢查 shell 覆寫值及所選設定檔。修改初始設定不會重設既有帳號。 |
| 找不到 CA／憑證驗證失敗 | 對同一專案執行 `bash dev-cp-cert.sh`，確認 `ELASTIC_CA_CERT`，使用 `localhost` 或 `127.0.0.1`，並保持憑證驗證開啟。 |
| Kibana 無法開啟 | 使用 `http://localhost:5601`，確認 Kibana setup 成功結束。 |
| 連接埠被占用 | 停止占用的服務，或修改 `ES_PORT`／`KIBANA_PORT` 並使用新網址。 |
| 索引唯讀／disk watermark | 釋放 Docker 磁碟空間並檢查日誌，保留磁碟保護設定。 |
| ARM JVM 出現 SVE 相關 illegal instruction | 更新 Docker 並查看 JVM crash log；僅在確認此原因時，設定 `ES_JAVA_OPTS=-XX:UseSVE=0` 後重建服務。 |
| Notebook 匯入失敗／套件仍是舊版 | 選用 `.venv` kernel，更新套件後重啟，並執行 `python -m pip check`。 |
| 教學索引 mapping 不相容 | 用新的 `COMPOSE_PROJECT_NAME` 建立獨立環境；手動刪除前先確認資料用途。 |

## 驗證與維護

修改 Python 範例後，可執行不需連線叢集的檢查：

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

本機叢集健康時，再執行 `python scripts/smoke_test.py` 驗證整合，並以重新啟動的 kernel 執行兩份 Notebook。靜態檢查與單元測試本身無法證明 Docker 能成功啟動或實際連線。

2026-10-23 已在 ARM64 Docker 與 Python 3.12.9 實測：Elasticsearch／Kibana 9.5.5 啟動健康、21 個單元測試通過、兩份 Notebook 完整執行、20,000 筆匯出成功，且重建容器後資料仍保留。憑證初始化中斷後的恢復流程也已驗證。

[GitHub Actions](.github/workflows/ci.yml) 會在 push 到 `main`、所有 pull request、手動執行及每月排程時檢查。Python 3.11／3.13 單元測試通過後，才以 Python 3.12 啟動 Docker、重跑兩次 smoke test 並執行兩份 Notebook。新提交會取消同一分支或 PR 過時的執行；Actions 固定於 commit SHA，整合測試失敗的診斷檔保留七天。

[Dependabot](.github/dependabot.yml) 每週檢查 pip 與 Actions 更新，並按套件來源分組。Pip 套件主版本升級需另外檢查相容性。

後續套件更新、遷移與保留既有資料的方法，請閱讀[升級與遷移指南](docs/UPGRADING.zh-TW.md)。
