import json
import os

from elasticsearch.helpers import bulk

from src.config import AppConfig
from src.es.client import get_es_client


def delete_index(es_client, index_name):
    """
    Elasticsearch からインデックスを削除します。
    インデックスが存在しない場合はエラーを無視します。
    """
    es_client.options(ignore_status=[400, 404]).indices.delete(index=index_name)


def create_index(es_client, index_name, mapping_file):
    """
    マッピングファイルを用いて Elasticsearch にインデックスを作成します。
    """
    with open(mapping_file, encoding="utf-8") as f:
        mapping = json.load(f)
    es_client.options(ignore_status=[400]).indices.create(
        index=index_name, body=mapping
    )


def append_documents(es_client, index_name, ndjson_file):
    """
    ndjson ファイルから読み込んだデータを bulk API を使って Elasticsearch に登録します。
    """
    actions = []
    with open(ndjson_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                doc = json.loads(line)
                if "_index" not in doc:
                    doc["_index"] = index_name
                actions.append(doc)
    if actions:
        bulk(es_client, actions)


def main():
    # AppConfig から設定を読み込み Elasticsearch クライアントを初期化
    config = AppConfig()
    es = get_es_client(config)

    # インデックス名、入力 JSON ファイルの取得 (fixters/tests/book.json)
    index_name = os.environ.get("INDEX_NAME", "sample_books")
    input_file = os.path.join("fixters/tests", "book.json")

    with open(input_file, encoding="utf-8") as f:
        data = json.load(f)
    mapping = data["mappings"]
    sample_data = data["sample_data"]

    print(f"Deleting index: {index_name}")
    delete_index(es, index_name)

    print(f"Creating index: {index_name}")
    es.options(ignore_status=[400]).indices.create(index=index_name, body=mapping)

    print("Appending documents from input file")
    actions = []
    for doc in sample_data:
        if "_index" not in doc:
            doc["_index"] = index_name
        actions.append(doc)
    if actions:
        bulk(es, actions)

    print("Setup ES index complete.")


if __name__ == "__main__":
    main()
