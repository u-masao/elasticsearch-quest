# src/ui.py (エントリーポイント)

# レイアウトモジュールの gr.Blocks() をインポート
import gradio as gr

from src.ui_actions import (
    check_query_format,
    format_query,
    get_mapping,
    init_elasticsearch_index,
    load_quest,
    submit_answer,
    test_run_query,
)
from src.ui_asset import (
    APP_TITLE,
    FORMAT_QUERY_BUTTON_TEXT,
    JSON_CHECK_OK,
    MAPPING_BUTTON_TEXT,
    RENEW_INDEX_BUTTON_TEXT,
    SUBMIT_BUTTON_TEXT,
    TEST_RUN_BUTTON_TEXT,
)

css = """
.large_font textarea {font-size: 1.5em; !important}
"""
with gr.Blocks(fill_width=True, fill_height=True, css=css) as demo:
    gr.Markdown(f"# {APP_TITLE}", max_height=30)
    with gr.Row(equal_height=True, scale=1):
        with gr.Column(scale=2):
            ui_chat = gr.Chatbot(type="messages", show_label=False)
        with gr.Column(scale=1):
            ui_quest_id = gr.Number(1, label="クエストID選択")
            ui_user_query = gr.Textbox(
                """{}""",
                lines=10,
                label="JSON 形式でクエリを書いて"
                f"「{SUBMIT_BUTTON_TEXT}」ボタンを押してください",
                scale=5,
                elem_classes="large_font",
            )
            ui_json_validator = gr.Markdown(JSON_CHECK_OK)
            with gr.Column():
                ui_format_button = gr.Button(FORMAT_QUERY_BUTTON_TEXT)
                ui_test_run_button = gr.Button(
                    TEST_RUN_BUTTON_TEXT, variant="secondary"
                )
                ui_submit_button = gr.Button(SUBMIT_BUTTON_TEXT, variant="primary")
                ui_mapping_button = gr.Button(MAPPING_BUTTON_TEXT)
                ui_book_select = gr.Dropdown(
                    [
                        ("default", "fixtures/books/default.json"),
                        ("part2", "fixtures/books/part2.json"),
                    ],
                    interactive=True,
                    label="ブック選択(インデックス再構築で反映)",
                )
                ui_renew_index_button = gr.Button(RENEW_INDEX_BUTTON_TEXT)

    # 一時的に無向にするボタン
    ui_buttons = [
        ui_format_button,
        ui_test_run_button,
        ui_submit_button,
        ui_mapping_button,
        ui_renew_index_button,
    ]

    # load quest
    gr.on(
        [demo.load, ui_quest_id.change, ui_book_select.change],
        fn=load_quest,
        inputs=[ui_quest_id, ui_book_select],
        outputs=[ui_chat],
    )

    # json_checker
    gr.on(
        [ui_user_query.change],
        fn=check_query_format,
        inputs=[ui_user_query],
        outputs=[ui_json_validator] + ui_buttons,
    )

    # submit query - using async action: submit_answer from src/ui_async_actions
    gr.on(
        [ui_submit_button.click],
        fn=submit_answer,
        inputs=[ui_quest_id, ui_user_query, ui_chat, ui_book_select],
        outputs=[ui_chat] + ui_buttons,
    )

    # test_run query - using async action: test_run_query from src/ui_async_actions
    gr.on(
        [ui_test_run_button.click],
        fn=test_run_query,
        inputs=[ui_user_query, ui_chat],
        outputs=[ui_chat] + ui_buttons,
    )

    # format query - using async action: format_query from src/ui_async_actions
    gr.on(
        [ui_format_button.click],
        fn=format_query,
        inputs=[ui_user_query],
        outputs=[ui_user_query] + ui_buttons,
    )

    # get mapping - using async action: get_mapping from src/ui_async_actions
    gr.on(
        [ui_mapping_button.click],
        fn=get_mapping,
        inputs=[ui_chat],
        outputs=[ui_chat] + ui_buttons,
    )

    # reset elasticsearch index - using async action:
    # init_elasticsearch_index from src/ui_async_actions
    gr.on(
        [ui_renew_index_button.click],
        fn=init_elasticsearch_index,
        inputs=[ui_chat, ui_book_select],
        outputs=[ui_chat] + ui_buttons,
    )

if __name__ == "__main__":
    demo.launch(share=False, debug=True)
