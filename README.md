# Elasticsearch Quest 🗺️✨

Elasticsearch Quest 🗺️✨ は、Elasticsearch を用いたクエスト形式の学習プラットフォームです。ユーザーはクエストに挑戦し、Elasticsearch のクエリやデータ操作のスキルを磨くことができます。

## 特徴

- **クエスト形式の学習**: 各クエストは特定の Elasticsearch の機能やクエリに焦点を当てており、実践的なスキルを身につけることができます。
- **フィードバックシステム**: クエストの結果に基づいて、詳細なフィードバックが提供され、学習をサポートします。
- **非同期処理**: 非同期処理を活用し、スムーズなユーザー体験を提供します。

## インストール

以下のコマンドを実行します。

1. リポジトリのクローン
2. uv のインストール
3. 仮想環境の構築
4. バックエンドの初期化とフロントエンドの実行

```bash
git clone https://github.com/yourusername/elasticsearch-quest.git
cd elasticsearch-quest
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
make run
```

## 使い方

1. クエストを選択し、クエリを作成します。
2. クエリを実行し、結果を確認します。
3. フィードバックを受け取り、スキルを向上させます。

## 貢献

貢献を歓迎します。バグ報告や機能提案は、GitHub の Issue トラッカーを通じて行ってください。

## ライセンス

このプロジェクトは MIT ライセンスの下でライセンスされています。詳細は LICENSE ファイルを参照してください。

## 外部ライブラリ

本プロジェクトでは、以下の外部ライブラリを利用しています。

* **Elasticsearch/OpenSearch MCP Server** (v2.0.4 - 2025-04-22)
    * オリジナルリポジトリ: https://github.com/cr7258/elasticsearch-mcp-server
    * ライセンス: Apache License 2.0
    * ライセンス条文: [mcp/elasticsearch-mcp-server/LICENSE](mcp/elasticsearch-mcp-server/LICENSE)
