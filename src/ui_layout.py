import gradio as gr
from src.ui import (
    load_quest,
    json_check,
    submit_answer,
    execute_query,
    format_query,
    get_mapping,
    init_elasticsearch_index,
    SUBMIT_BUTTON_TEXT,
    JSON_CHECK_OK
)

from src.ui_layout import demo
