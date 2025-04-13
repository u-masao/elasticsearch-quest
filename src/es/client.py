# src/es/client.py (修正例)
from elasticsearch import Elasticsearch

from ..config import AppConfig  # AppConfig をインポート

# from ..exceptions import InitializationError # 必要なら


def get_es_client(config: AppConfig) -> Elasticsearch:
    """Elasticsearchクライアントを取得する (設定オブジェクトを使用)"""
    common_args = {"request_timeout": 60}  # 共通設定

    if config.elastic_cloud_id:
        # クラウドIDを使用
        if not config.elasticsearch_username or not config.elasticsearch_password:
            # 警告を出すかエラーにする
            print(
                "警告: Cloud IDを使用する場合、ELASTICSEARCH_USERNAME と ELASTICSEARCH_PASSWORD の設定が必要です。"
            )
            # raise InitializationError("Cloud ID認証にはユーザー名とパスワードが必要です。")
        return Elasticsearch(
            cloud_id=config.elastic_cloud_id,
            basic_auth=(config.elasticsearch_username, config.elasticsearch_password),
            **common_args,
        )
    elif config.elasticsearch_url:
        # URLを使用
        auth = None
        if config.elasticsearch_username and config.elasticsearch_password:
            auth = (config.elasticsearch_username, config.elasticsearch_password)

        ca_certs_path = (
            str(config.elasticsearch_ca_cert) if config.elasticsearch_ca_cert else None
        )

        return Elasticsearch(
            [str(config.elasticsearch_url)],
            basic_auth=auth,
            ca_certs=ca_certs_path,
            verify_certs=bool(ca_certs_path),  # CA証明書があれば検証する
            **common_args,
        )
    else:
        # デフォルト (localhost)
        return Elasticsearch(["http://localhost:9200"], **common_args)
