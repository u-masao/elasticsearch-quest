
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
