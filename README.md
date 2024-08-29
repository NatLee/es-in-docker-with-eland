# Example of Elasticsearch in Docker with Eland

[EN|[TW](./README.zh-TW.md)]

This is an example of Elasticsearch in Docker with Eland.

## Usage

> In some cases, you may need to increase the maximum of virtual memory by running `sysctl -w vm.max_map_count=262144`.

1. Check `.env` file and set the values if needed.

2. Create a folder for Elasticsearch data:
    > If you don't change the mode of the folder, you may encounter permission errors with Elasticsearch.
    ```bash
    mkdir ./es-data && chmod 777 ./es-data
    ```

3. Start Elasticsearch stacks:
    ```bash
    docker-compose up -d
    ```

4. When Elasticsearch is running, you can copy the cert files to host with the following command:
    ```bash
    bash dev-cp-cert.sh
    ```

5. Create an environment and install the required packages:
    ```bash
    conda create -n es-test python=3.11
    conda activate es-test
    pip install -r requirements.txt
    ```

6. Check 2 ipynb files in `notebooks` folder for examples.

    - `eland-test.ipynb`: Basic Elasticsearch operations with Eland.
    - `eland-over-10000-test.ipynb`: Basic Elasticsearch operations with Eland for over 10000 records.

7. (Optional) Visit `Kibana` with the following URL:
    ```
    https://localhost:5601
    ```

    The default username is `elastic` and the password is in the `.env` file.

