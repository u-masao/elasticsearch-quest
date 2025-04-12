#!/bin/bash

# === 設定項目 ===
# リポジトリ名
REPO="u-masao/elasticsearch-quest"

# 付与したいラベル (カンマ区切り、なければ空文字 "")
LABELS=""

# 担当者 (@me で自分自身を指定)
ASSIGNEE="@me"

# マイルストーン名 (必要なら設定、なければ空文字 "")
MILESTONE=""
# ================

# リポジトリ名のチェック
if [ "$REPO" = "OWNER/REPO" ]; then
  echo "エラー: スクリプト内の REPO 変数をあなたのリポジトリ名に書き換えてください。"
  exit 1
fi

# マイルストーンオプションの組み立て
MILESTONE_OPT=""
if [ -n "$MILESTONE" ]; then
  MILESTONE_OPT="--milestone \"$MILESTONE\""
fi

echo "GitHubリポジトリ '$REPO' にフェーズ1のタスクをIssueとして登録します..."

# 1. 環境構築
gh issue create -R "$REPO" -t "環境構築: 開発環境セットアップ" \
  -b "Python, Docker (for Elasticsearch), Gradio, OpenAI SDK, elasticsearch-py等の開発に必要な環境をセットアップする。" \
  -l "$LABELS" -a "$ASSIGNEE" $MILESTONE_OPT
echo "Issue '環境構築' を作成しました。"

# 2. サンプルデータ準備
gh issue create -R "$REPO" -t "データ準備: 固定サンプルデータ作成と投入スクリプト" \
  -b "学習に使用する固定のサンプルデータ（JSON形式）を選定または作成し、Elasticsearchに投入するためのスクリプトを用意する。" \
  -l "$LABELS" -a "$ASSIGNEE" $MILESTONE_OPT
echo "Issue 'サンプルデータ準備' を作成しました。"

# 3. クエスト定義
gh issue create -R "$REPO" -t "クエスト定義: フェーズ1対象クエストの実装" \
  -b "フェーズ1で扱う基本クエスト（match, term, range, bool等）の問題文、期待結果、評価基準、ヒント案などを定義し、SQLite等に格納する形式を決定・実装する。" \
  -l "$LABELS" -a "$ASSIGNEE" $MILESTONE_OPT
echo "Issue 'クエスト定義' を作成しました。"

# 4. 基本UI作成 (Gradio)
gh issue create -R "$REPO" -t "UI実装: Gradioによる基本画面作成" \
  -b "Gradioを使用して、クエスト表示、クエリ入力エリア、実行ボタン、結果表示エリア、フィードバック表示エリアなどの基本的なUIコンポーネントを作成する。" \
  -l "$LABELS" -a "$ASSIGNEE" $MILESTONE_OPT
echo "Issue '基本UI作成 (Gradio)' を作成しました。"

# 5. バックエンド実装 (コア)
gh issue create -R "$REPO" -t "バックエンド実装: コアロジック" \
  -b "ユーザーからのリクエストを受け付け、クエリをElasticsearchで実行し、基本的な正誤判定を行い、クエストの進行を管理するコアロジックを実装する。" \
  -l "$LABELS" -a "$ASSIGNEE" $MILESTONE_OPT
echo "Issue 'バックエンド実装 (コア)' を作成しました。"

# 6. LLM連携 (基本)
gh issue create -R "$REPO" -t "LLM連携: OpenAI Assistant基本設定とヒント生成" \
  -b "OpenAI Assistantの基本的な設定（システムプロンプト、Elasticsearch実行ツールの定義など）を行い、ユーザーが行き詰まった際に基本的なヒントを生成する機能を実装する。" \
  -l "$LABELS" -a "$ASSIGNEE" $MILESTONE_OPT
echo "Issue 'LLM連携 (基本)' を作成しました。"

# 7. DB設計・実装 (基本)
gh issue create -R "$REPO" -t "DB実装: SQLite基本スキーマとCRUD" \
  -b "SQLiteを使用して、ユーザー情報、クエスト定義、学習履歴などを格納するための基本的なテーブルスキーマを設計し、基本的なデータの読み書き（CRUD）処理を実装する。" \
  -l "$LABELS" -a "$ASSIGNEE" $MILESTONE_OPT
echo "Issue 'DB設計・実装 (基本)' を作成しました。"

echo "Issueの登録が完了しました。"
