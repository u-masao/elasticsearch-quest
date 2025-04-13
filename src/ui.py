import gradio as gr

with gr.Blocks() as demo:
    gr.Markdown("Hello world")

if __name__ == "__main__":
    demo.launch(share=False, debug=True)
