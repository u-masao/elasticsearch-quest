include .env

# run es chatbot
es_chatbot:
	uv run python -m src.es_chatbot

# run cli version
run:
	uv run python -m src.main

# run gui version
ui:
	uv run gradio src/ui.py

# run test
test:
	PYTHONPATH=. uv run pytest -v tests

# run formatter and linter
lint:
	uv run ruff check src tests
	uv run ruff format src tests

# バックエンドの elasticsearch を起動
# アクセス情報をホスト側へ展開
setup:
	docker compose up -d
	./shells/copy_http_ca_cert.sh
	./shells/generate_es_password.sh

# Elasticsearch にサンプルデータを投入
setup_es_index:
	uv run python -m src.setup_es_index \
    sample_books \
    fixtures/sample_books.json 2>&1 \
    | tee logs/setup_sample_books_index.log

# sqlite のスキーマ定義
DB_FILEPATH=.db.sqlite3
setup_backend_db:
	echo 'drop table if exists quests' | sqlite3 $(DB_FILEPATH)
	cat fixtures/create_quests_table.sql | sqlite3 $(DB_FILEPATH)
	cat fixtures/insert_quests.sql | sqlite3 $(DB_FILEPATH)
	echo 'select * from quests' | sqlite3 $(DB_FILEPATH)

# Index のダンプ
INDEX_NAME=sample_books
dump_index:
	curl --cacert ./certs/http_ca.crt \
    -u $(ELASTICSEARCH_USERNAME):$(ELASTICSEARCH_PASSWORD) \
    -d '{"size": 1000}' \
    -H 'Content-Type: application/json' \
    https://127.0.0.1:9200/$(INDEX_NAME)/_search/ \
    | jq .hits.hits > fixtures/sample_books_dump.json

