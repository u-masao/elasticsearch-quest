# src/ui.py (エントリーポイント)

# レイアウトモジュールの gr.Blocks() をインポート
import gradio as gr

from src.ui_actions import (
    execute_query,
    format_query,
    get_mapping,
    init_elasticsearch_index,
    json_check,
    load_quest,
    submit_answer,
)
from src.ui_asset import JSON_CHECK_OK, SUBMIT_BUTTON_TEXT

css = """
.large_font textarea {font-size: 1.5em; !important}
"""
with gr.Blocks(fill_width=True, fill_height=True, css=css) as demo:
    with gr.Row(equal_height=True, scale=1):
        with gr.Column(scale=2):
            ui_chat = gr.Chatbot(type="messages")
        with gr.Column(scale=1):
            ui_user_query = gr.Textbox(
                "{}",
                lines=10,
                label="JSON形式でクエリを書いて「採点」ボタンを押してください",
                scale=5,
                elem_classes="large_font",
            )
            with gr.Column():
                ui_quest_id = gr.Number(1, label="クエストID選択")
                ui_json_validator = gr.Markdown(JSON_CHECK_OK)
                ui_execute_button = gr.Button("▶️  テスト実行 ▶️", variant="secondary")
                ui_format_button = gr.Button("✨ 自動整形 ✨")
                ui_submit_button = gr.Button(SUBMIT_BUTTON_TEXT, variant="primary")
                ui_mapping_button = gr.Button("(マッピング取得)")
                ui_book_select = gr.Dropdown(
                    [
                        ("default", "fixtures/books/default.json"),
                        ("part2", "fixtures/books/part2.json"),
                    ],
                    interactive=True,
                )
                ui_renew_index_button = gr.Button("(インデックス再構築)")

    # json_checker
    gr.on(
        [ui_user_query.change],
        fn=json_check,
        inputs=[ui_user_query],
        outputs=[ui_json_validator],
    )

    # load quest
    gr.on(
        [demo.load, ui_quest_id.change, ui_book_select.change],
        fn=load_quest,
        inputs=[ui_quest_id, ui_book_select],
        outputs=[ui_chat],
    )

    # submit query - using async action: submit_answer from src/ui_async_actions
    gr.on(
        [ui_submit_button.click],
        fn=submit_answer,
        inputs=[ui_quest_id, ui_user_query, ui_chat, ui_book_select],
        outputs=[ui_chat, ui_submit_button],
    )

    # execute query - using async action: execute_query from src/ui_async_actions
    gr.on(
        [ui_execute_button.click],
        fn=execute_query,
        inputs=[ui_user_query, ui_chat],
        outputs=[ui_chat],
    )

    # format query - using async action: format_query from src/ui_async_actions
    gr.on(
        [ui_format_button.click],
        fn=format_query,
        inputs=[ui_user_query],
        outputs=[ui_user_query],
    )

    # get mapping - using async action: get_mapping from src/ui_async_actions
    gr.on(
        [ui_mapping_button.click],
        fn=get_mapping,
        inputs=[ui_chat],
        outputs=[ui_chat],
    )

    # reset elasticsearch index - using async action:
    # init_elasticsearch_index from src/ui_async_actions
    gr.on(
        [ui_renew_index_button.click],
        fn=init_elasticsearch_index,
        inputs=[ui_chat, ui_book_select],
        outputs=[ui_chat],
    )

if __name__ == "__main__":
    demo.launch(share=False, debug=True)
