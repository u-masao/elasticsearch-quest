# src/ui.py (エントリーポイント)

# レイアウトモジュールの gr.Blocks() をインポート
from src.ui_layout import demo

if __name__ == "__main__":
    demo.launch(share=False, debug=True)
