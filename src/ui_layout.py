import gradio as gr

from src.ui import JSON_CHECK_OK, SUBMIT_BUTTON_TEXT
from src.ui_async_actions import (
    execute_query,
    format_query,
    get_mapping,
    init_elasticsearch_index,
    json_check,
    load_quest,
    submit_answer,
)

with gr.Blocks(fill_width=True, fill_height=True) as demo:
    with gr.Row(equal_height=True, scale=1):
        with gr.Column(scale=2):
            ui_chat = gr.Chatbot(type="messages")
        with gr.Column(scale=1):
            ui_user_query = gr.Textbox(
                "{}",
                lines=20,
                label="JSON形式でクエリを書いて「採点」ボタンを押してください",
                scale=5,
            )
            with gr.Column():
                ui_quest_id = gr.Number(1, label="クエストID選択")
                ui_json_validator = gr.Markdown(JSON_CHECK_OK)
                ui_execute_button = gr.Button("▶️  テスト実行 ▶️", variant="secondary")
                ui_format_button = gr.Button("✨ 自動整形 ✨")
                ui_mapping_button = gr.Button("マッピング取得")
                ui_submit_button = gr.Button(SUBMIT_BUTTON_TEXT, variant="primary")
                ui_renew_index_button = gr.Button("(インデックス再構築)")
                ui_book_select = gr.Dropdown(
                    ["default.json", "part2.json"], interactive=True
                )

    # onload
    demo.load(
        load_quest,
        inputs=[ui_quest_id],
        outputs=[ui_chat],
    )

    # select quest
    gr.on(
        [ui_user_query.change],
        fn=json_check,
        inputs=[ui_user_query],
        outputs=[ui_json_validator],
    )

    # load quest
    gr.on(
        [ui_quest_id.change],
        fn=load_quest,
        inputs=[ui_quest_id],
        outputs=[ui_chat],
    )

    # submit query
    gr.on(
        [ui_submit_button.click],
        fn=submit_answer,
        inputs=[ui_quest_id, ui_user_query, ui_chat],
        outputs=[ui_chat, ui_submit_button],
    )

    # execute query
    gr.on(
        [ui_execute_button.click],
        fn=execute_query,
        inputs=[ui_user_query, ui_chat],
        outputs=[ui_chat],
    )

    # format query
    gr.on(
        [ui_format_button.click],
        fn=format_query,
        inputs=[ui_user_query],
        outputs=[ui_user_query],
    )

    # get mapping
    gr.on(
        [ui_mapping_button.click],
        fn=get_mapping,
        inputs=[ui_chat],
        outputs=[ui_chat],
    )

    # reset elasticsearch index
    gr.on(
        [ui_renew_index_button.click],
        fn=init_elasticsearch_index,
        inputs=[ui_chat],
        outputs=[ui_chat],
    )
