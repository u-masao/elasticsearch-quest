
-- sample_books.json データに基づいたクエストデータ投入コマンド

-- クエスト1: 書籍名検索 (Match)
INSERT INTO quests (title, description, difficulty, query_type_hint, evaluation_type, evaluation_data, hints)
VALUES (
    '書籍名検索 (Match)',
    '書籍名 (`name`) に ''Deep Learning'' という単語が含まれる本を検索してください。',
    1, -- 難易度 Easy
    'match',
    'result_count',
    '3', -- "ゼロから作るDeep Learning" の3冊がヒットするはず
    '["`match` クエリは、指定されたテキストを解析し、一致するドキュメントを検索します。","基本的な構文: `query: { match: { field_name: \"search_term\" } }`"]'
);

-- クエスト2: 出版社検索 (Term)
INSERT INTO quests (title, description, difficulty, query_type_hint, evaluation_type, evaluation_data, hints)
VALUES (
    '出版社検索 (Term)',
    '出版社 (`publisher`) が ''オライリー・ジャパン'' である本を検索してください。完全一致で検索するには `.keyword` フィールドを使います。',
    1, -- 難易度 Easy
    'term',
    'result_count',
    '6', -- オライリーの本は6冊あるはず
    '["完全一致検索には `term` クエリを使います。","テキストフィールドの完全一致検索では、マッピングで定義された `.keyword` サブフィールドを指定するのが一般的です。","構文: `query: { term: { \"publisher.keyword\": \"オライリー・ジャパン\" } }`"]'
);

-- クエスト3: ページ数検索 (Range)
INSERT INTO quests (title, description, difficulty, query_type_hint, evaluation_type, evaluation_data, hints)
VALUES (
    'ページ数検索 (Range)',
    'ページ数 (`pages`) が 500ページ以上 の本を検索してください。',
    2, -- 難易度 Medium
    'range',
    'result_count',
    '3', -- 512, 704, 768, 788ページの4冊のはず -> 訂正: 600, 704, 768, 788, 512 の5冊？ -> 訂正: 600, 704, 768, 788, 512 の5冊
    '["数値の範囲を指定するには `range` クエリを使います。","「以上」を指定するには `gte` (Greater Than or Equal to) を使います。","構文: `query: { range: { pages: { \"gte\": 500 } } }`"]'
);
-- ページ数確認: 304, 312, 432, 424, 400, 304, 432, **600**, 272, **704**, 256, 352, **768**, **788**, 400, 430, **512**, 464, 352, 304 => 5冊
-- 評価データ修正
UPDATE quests SET evaluation_data = '5' WHERE title = 'ページ数検索 (Range)';


-- クエスト4: 複数条件検索 (Bool)
INSERT INTO quests (title, description, difficulty, query_type_hint, evaluation_type, evaluation_data, hints)
VALUES (
    '複数条件検索 (Bool)',
    '出版社 (`publisher.keyword`) が ''技術評論社'' であり、かつページ数 (`pages`) が 400ページ以上 の本を検索してください。',
    2, -- 難易度 Medium
    'bool, term, range',
    'result_count',
    '2', -- 技術評論社の本は4冊。うち400ページ以上は 512, 464ページの2冊のはず -> 訂正: 312, **704**, **512**, **464**, 352 -> 3冊？ -> 訂正: 312, **704**, **512**, **464**, 352 -> 3冊
    '["複数の条件を組み合わせるには `bool` クエリを使います。","すべての条件を満たす必要がある場合、`must` 句または `filter` 句を使います。スコア計算に関係ない場合は `filter` が効率的です。","`filter` 句の中に `term` クエリと `range` クエリを入れてみましょう。"]'
);
-- 技術評論社: 312([6,7]), **704**([9,3]), **512**([9,5]), **464**([8,2]), 352([6,3]) => 3冊
-- 評価データ修正
UPDATE quests SET evaluation_data = '3' WHERE title = '複数条件検索 (Bool)';


-- クエスト5: ベクトル要素アクセス (Script Query)
INSERT INTO quests (title, description, difficulty, query_type_hint, evaluation_type, evaluation_data, hints)
VALUES (
    'ベクトル要素アクセス (Script)',
    'Technical score (`metric_vector[0]`) が 8 以上で、かつ Mathematical score (`metric_vector[1]`) が 6 以上 の本を検索してください。ベクトル要素へのアクセスには `script` クエリを使います。',
    3, -- 難易度 Hard
    'bool, script',
    'result_count',
    '4', -- [8,6], [8,7], [9,7], [8,6] の4冊が該当するはず
    '["`script` クエリを使うと、ドキュメントのフィールド値に基づいてカスタム条件でフィルタリングできます。","`bool` クエリの `filter` 句の中で `script` クエリを2つ使い、それぞれの条件を記述します。","スクリプト内でのベクトル要素へのアクセスは `doc[''metric_vector''][0]` や `doc[''metric_vector''].value[0]` のように行います（マッピングによります）。Painless言語のドキュメントも参考にしましょう。"]'
);

-- クエスト6: ベクトル類似検索 (kNN)
INSERT INTO quests (title, description, difficulty, query_type_hint, evaluation_type, evaluation_data, hints)
VALUES (
    'ベクトル類似検索 (kNN)',
    'ベクトル `[9, 1]` (Technical寄り) にベクトル空間上で最も近い本を上位3件検索してください。Elasticsearch 8.x以降の `knn` オプションを使います。(L2距離)',
    3, -- 難易度 Hard
    'knn',
    'doc_ids_in_order', -- 評価タイプ: 特定ドキュメントIDが指定順に含まれるか (カスタム評価)
    '["10","11","18"]', -- 評価データ: 期待されるISBNのリスト（近い順）。[9,1], [8,2], [9,3]に対応。
    '["`knn` 検索は、クエリベクトルに最も近いベクトルを持つドキュメントを効率的に検索します。マッピングで `dense_vector` フィールドの `index: true` が必要です。","クエリのトップレベルに `knn` オプションを指定します。`field`, `query_vector`, `k`, `num_candidates` が主要なパラメータです。","`query_vector` に `[9, 1]` を、`k` に取得したい件数(3)、`num_candidates` に `k` より大きい値(例: 10)を指定します。"]'
);
