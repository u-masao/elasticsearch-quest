# src/elasticsearch_client.py
import os

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()


def get_es_client() -> Elasticsearch:
    """
    環境変数からElasticsearchの接続情報を取得し、
    Elasticsearchクライアントインスタンスを生成して返す。
    """
    # 環境変数からElasticsearchのURLを取得 (例: http://localhost:9200)
    # .env ファイルや Docker Compose の環境変数設定を利用することを推奨
    es_url = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
    es_ca_cert = os.environ.get("ELASTICSEARCH_CA_CERT")
    es_api_key = os.environ.get("ELASTICSEARCH_API_KEY")  # APIキー認証の場合
    es_username = os.environ.get("ELASTICSEARCH_USERNAME")  # Basic認証の場合
    es_password = os.environ.get("ELASTICSEARCH_PASSWORD")  # Basic認証の場合
    es_timeout = int(os.environ.get("ELASTICSEARCH_TIMEOUT", 30))

    cloud_id = os.environ.get("ELASTIC_CLOUD_ID")  # Elastic Cloudの場合

    try:
        if cloud_id and es_api_key:
            # Elastic Cloud (APIキー認証)
            print(f"Connecting to Elastic Cloud: {cloud_id}")
            client = Elasticsearch(
                cloud_id=cloud_id,
                api_key=es_api_key,
                request_timeout=es_timeout,  # タイムアウト設定 (秒)
                ca_certs=es_ca_cert,
            )
        elif cloud_id and es_username and es_password:
            # Elastic Cloud (Basic認証) - 非推奨だが参考として
            print(f"Connecting to Elastic Cloud (Basic Auth): {cloud_id}")
            client = Elasticsearch(
                cloud_id=cloud_id,
                basic_auth=(es_username, es_password),
                request_timeout=es_timeout,
                ca_certs=es_ca_cert,
            )
        elif es_api_key:
            # セルフホスト (APIキー認証)
            print(f"Connecting to {es_url} using API Key")
            client = Elasticsearch(
                es_url,
                api_key=es_api_key,
                request_timeout=es_timeout,
                ca_certs=es_ca_cert,
            )
        elif es_username and es_password:
            # セルフホスト (Basic認証)
            print(f"Connecting to {es_url} using Basic Auth")
            client = Elasticsearch(
                es_url,
                basic_auth=(es_username, es_password),
                request_timeout=es_timeout,
                ca_certs=es_ca_cert,
            )
        else:
            # 認証なし (ローカル開発用など)
            print(f"Connecting to {es_url} without authentication")
            client = Elasticsearch(es_url, request_timeout=es_timeout)

        # 接続確認
        if not client.ping():
            raise ConnectionError("Failed to connect to Elasticsearch.")
        print("Successfully connected to Elasticsearch.")
        return client

    except Exception as e:
        print(f"Error connecting to Elasticsearch: {e}")
        raise
