#/bin/bash

. .env
# 環境変数を設定 (例)
export ELASTICSEARCH_URL=$ELASTICSEARCH_URL
export ELASTICSEARCH_USERNAME=$ELASTICSEARCH_USERNAME
export ELASTICSEARCH_PASSWORD=$ELASTICSEARCH_PASSWORD
export ELASTICSEARCH_CA_CERT=$ELASTICSEARCH_CA_CERT

# (必要であれば認証情報も設定 export ELASTICSEARCH_API_KEY=...)

# DBファイルとインデックス名を確認・設定して実行
# 例: クエストID 1 に挑戦し、クエリを直接指定
uv run python -m src.cli 1 --query '{ "query": { "match": { "name": "Deep Learning" } } }'

# 例: クエストID 3 に挑戦し、インタラクティブにクエリを入力
echo '{ "query": { "range": { "pages": { "gte": 500 } } } }' | uv run python -m src.cli 3

# 例: クエストID 6 に挑戦し、クエリをファイルから読み込む
uv run python -m src.cli 6 --query_file fixtures/test_query_quest_6.json
