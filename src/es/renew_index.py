import json

from elasticsearch.helpers import bulk

from src.config import load_config
from src.es.client import get_es_client


def delete_index(es_client, index_name):
    """
    Elasticsearch からインデックスを削除します。
    インデックスが存在しない場合はエラーを無視します。
    """
    es_client.options(ignore_status=[400, 404]).indices.delete(index=index_name)


def create_index(es_client, index_name, book_file):
    """
    マッピングファイルを用いて Elasticsearch にインデックスを作成します。
    """
    try:
        with open(book_file, encoding="utf-8") as f:
            book = json.load(f)
    except Exception as e:
        raise e

    # クエリ発行
    es_client.options(ignore_status=[400]).indices.create(
        index=index_name, body=book.get("mappings", {})
    )


def main():
    # AppConfig から設定を読み込み Elasticsearch クライアントを初期化
    config = load_config()
    es = get_es_client(config)

    # インデックス名を取得
    index_name = config.index_name

    # 入力 JSON ファイルの取得 (fixters/tests/book.json)
    with open(config.book_path, encoding="utf-8") as f:
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
