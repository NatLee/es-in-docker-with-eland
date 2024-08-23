# Elasticsearch 在 Docker 中與 Eland 一起使用的範例

[[EN](./README.md)|TW]

這是一個在 Docker 中使用 Elasticsearch 並結合 Eland 的範例。

## 使用方法

1. 檢查 `.env` 文件並根據需要設定相應的值。

2. 為 Elasticsearch 資料建立一個資料夾：
    > 如果不更改資料夾的權限，會遇到 Elasticsearch 存取資料的權限問題。
    ```bash
    mkdir ./es-data && chmod 777 ./es-data
    ```

3. 使用Docker指令啟動 Elasticsearch：
    ```bash
    docker-compose up -d
    ```

4. 當 Elasticsearch 運行時，我們可以使用以下指令將憑證複製到本機：
    ```bash
    bash dev-cp-cert.sh
    ```

5. 建立一個測試環境並安裝所需的套件：
    ```bash
    conda create -n es-test python=3.11
    conda activate es-test
    pip install -r requirements.txt
    ```

6. 查看 `notebooks` 資料夾中的兩個 ipynb 的範例。

    - `eland-test.ipynb`：使用 Eland 進行基本的 Elasticsearch 操作。
    - `eland-over-10000-test.ipynb`：使用 Eland 對超過 10000 條記錄進行基本的 Elasticsearch 操作。

7. （可選）使用以下 URL 訪問 `Kibana`：
    ```
    https://localhost:5601
    ```

    預設的使用者名稱是 `elastic`，密碼在 `.env` 文件中。

