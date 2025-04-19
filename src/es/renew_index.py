import os
import json
from elasticsearch.helpers import bulk
from src.es.client import get_es_client
from src.config import AppConfig


def delete_index(es_client, index_name):
    """
    Elasticsearch からインデックスを削除します。
    インデックスが存在しない場合はエラーを無視します。
    """
    es_client.indices.delete(index=index_name, ignore=[400, 404])


def create_index(es_client, index_name, mapping_file):
    """
    マッピングファイルを用いて Elasticsearch にインデックスを作成します。
    """
    with open(mapping_file, encoding="utf-8") as f:
        mapping = json.load(f)
    es_client.indices.create(index=index_name, body=mapping, ignore=400)


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
                actions.append(doc)
    if actions:
        bulk(es_client, actions)


def main():
    # AppConfig から設定を読み込み Elasticsearch クライアントを初期化
    config = AppConfig()
    es = get_es_client(config)

    # インデックス名、マッピングファイル、ndjson ファイルの取得
    index_name = os.environ.get("INDEX_NAME", "sample_books")
    mapping_file = os.path.join("fixtures", "sample_books_mapping.json")
    ndjson_file = os.path.join("fixtures", "sample_books.ndjson")

    print(f"Deleting index: {index_name}")
    delete_index(es, index_name)

    print(f"Creating index: {index_name}")
    create_index(es, index_name, mapping_file)

    print(f"Appending documents from: {ndjson_file}")
    append_documents(es, index_name, ndjson_file)

    print("Setup ES index complete.")


if __name__ == "__main__":
    main()
