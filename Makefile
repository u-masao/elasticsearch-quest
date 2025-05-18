# default target
default: usage

# 使い方を表示
usage:
	echo make run : バックエンドの初期化とUI起動

# バックエンドを初期化して UI を起動
run: setup ui

# Elasticsearch & kibana を初期化
setup:
	./shells/init_client_credentials.sh

# GUI のバックエンドを実行
ui:
	PYTHONPATH=. uv run gradio src/ui.py

# Elasticsearch チャットボットを実行
es_chatbot:
	uv run python -m src.misc.es_chatbot

# 開発用: テスト実行
test:
	PYTHONPATH=. uv run pytest -v tests

# 開発用: フォーマッタ
lint:
	uv run ruff format src tests
	uv run ruff check --fix src tests

# kibana 接続トークンを生成
kibana_token:
	docker compose exec -it elasticsearch \
        /usr/share/elasticsearch/bin/elasticsearch-create-enrollment-token \
        -f -s kibana

# kibana ログイン認証コードを生成
kibana_verification:
	docker compose exec kibana /usr/share/kibana/bin/kibana-verification-code

