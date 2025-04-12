CREATE TABLE quests (
    -- 基本情報
    quest_id INTEGER PRIMARY KEY AUTOINCREMENT,  -- クエストを一意に識別するID (自動採番)
    title TEXT NOT NULL,                        -- クエストのタイトル (例: "基本のMatchクエリ")
    description TEXT NOT NULL,                  -- ユーザーに提示する問題文、課題の説明
    difficulty INTEGER NOT NULL DEFAULT 1,      -- クエストの難易度 (例: 1=Easy, 2=Medium, ...)。ステップの順序付けに使用。

    -- クエリと評価に関する情報
    query_type_hint TEXT,                       -- ユーザーが使用を想定される主要クエリタイプ (例: "match", "bool", "range")。学習のヒント用。
    evaluation_type TEXT NOT NULL,              -- 正誤判定の方法を示す識別子。
                                                -- (例: 'result_count', 'doc_ids_include', 'exact_match_query', 'aggregation_result')
    evaluation_data TEXT NOT NULL,              -- 評価に必要な具体的なデータ。evaluation_typeによって内容は変わる。
                                                -- 'result_count'なら期待ヒット数(数値)。
                                                -- 'doc_ids_include'なら含まれるべきIDリスト(JSON配列文字列推奨)。
                                                -- 'aggregation_result'なら期待される集計結果(JSON文字列推奨)。
                                                -- TEXT型にしてJSON文字列で保存するのが柔軟。

    -- サポート情報
    hints TEXT,                                 -- ヒント。複数段階のヒントを提供できるよう、JSON配列文字列での格納を推奨。
                                                -- 例: ["基本的な検索にはmatchクエリを使います。", "フィールド名と検索語を指定しましょう。"]

    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- レコード作成日時
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP   -- レコード更新日時
);

-- (任意) 検索パフォーマンス向上のためのインデックス
CREATE INDEX idx_quests_difficulty ON quests (difficulty);

-- (任意) 更新日時を自動更新するためのトリガー
CREATE TRIGGER trigger_quests_updated_at
AFTER UPDATE ON quests
FOR EACH ROW
BEGIN
    UPDATE quests SET updated_at = CURRENT_TIMESTAMP WHERE quest_id = OLD.quest_id;
END;

