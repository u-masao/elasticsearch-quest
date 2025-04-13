# src/services/agent_service.py
from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServerStdio

from ..config import AppConfig
from ..db.quest_repository import Quest  # Questモデル
from ..exceptions import AgentError
from ..view import QuestView


class AgentService:
    """LLMエージェントの実行を担当するサービスクラス"""

    def __init__(self, config: AppConfig, view: "QuestView"):
        """
        Args:
            config: アプリケーション設定オブジェクト.
            view: CLI表示用オブジェクト (トレース情報表示用).
        """
        self.config = config
        self.view = view  # トレースURL表示などに使用

    def _create_mcp_server_config(self) -> dict:
        """MCP Serverプロセスの設定辞書を作成する"""
        # .env や config から読み込んだ情報を環境変数として渡す
        mcp_env = {
            # MCP Serverが必要とする環境変数を設定
            "ELASTICSEARCH_HOST": str(self.config.elasticsearch_url)
            if self.config.elasticsearch_url
            else None,
            "ELASTICSEARCH_USERNAME": self.config.elasticsearch_username,
            "ELASTICSEARCH_PASSWORD": self.config.elasticsearch_password,
            "ELASTICSEARCH_CA_CERT": str(self.config.elasticsearch_ca_cert)
            if self.config.elasticsearch_ca_cert
            else None,
            # Cloud ID はMCP Server側が対応しているか確認が必要
            "ELASTIC_CLOUD_ID": self.config.elastic_cloud_id,
            # 必要に応じて他の環境変数も追加
            # "LOG_LEVEL": "DEBUG",
        }
        # None の値を持つキーを除去
        mcp_env_filtered = {k: v for k, v in mcp_env.items() if v is not None}

        return {
            "command": self.config.mcp_server_command,
            "args": [
                "--directory",
                str(self.config.mcp_server_directory),  # 絶対パスを使用
                "run",
                self.config.mcp_server_module,
            ],
            "env": mcp_env_filtered,
        }

    async def run_evaluation_agent(
        self, quest: Quest, user_query_str: str, rule_eval_message: str
    ) -> str:
        """
        LLMエージェントを実行し、ユーザーの回答に対する評価フィードバックを取得する。

        Args:
            quest: 対象のQuestオブジェクト.
            user_query_str: ユーザーが入力したクエリ文字列.
            rule_eval_message: ルールベース評価の結果メッセージ.

        Returns:
            エージェントによって生成されたフィードバック文字列.

        Raises:
            AgentError: エージェントの実行中にエラーが発生した場合.
        """
        # エージェントへの指示プロンプト
        # TODO: このプロンプトは目的に合わせて調整・改善が必要
        agent_instructions = f"""
        あなたはElasticsearchのエキスパートです。ユーザーがElasticsearchの
        問題に挑戦し、回答を提出しました。以下の情報に基づいて、ユーザーの
        回答を評価し、改善のための具体的なフィードバックを提供してください。
        適切な絵文字を入れるとユーザーのモチベーションが上がります。

        # 指示
        1.  **問題の意図の理解**: ユーザーのクエリが問題（Quest）の意図を
            正しく理解しているか評価してください。
        2.  **クエリの正確性**: クエリが構文的に正しいか、期待される結果を
            得られるか評価してください。ルールベース評価の結果も参考にして
            ください。
        3.  **改善提案**: もし改善点があれば、より良いクエリの書き方、代替
            アプローチ、考慮すべき点を具体的に指摘してください。
        4.  **形式**: 評価結果とフィードバックを分かりやすく記述してくださ
            い。

        # 入力情報
        ## 問題 (Quest)
        タイトル: {quest.title}
        難易度: {quest.difficulty}
        内容:
        {quest.description}

        ## ユーザーの回答 (Query)
        ```json
        {user_query_str}
        ```

        ## ルールベース評価の結果
        {rule_eval_message}

        # 出力形式

        ## 評価サマリー
        （例：問題の意図を概ね理解していますが、クエリのこの部分に改善の余
        地があります。）

        ## 詳細フィードバック
        （例：
        - match クエリの代わりに match_phrase を使うと、より意図に近い結果
          が得られるでしょう。
        - このフィールドに対する集計は問題の要求と異なります。代わりにyyyy
          フィールドを集計してください。
        - クエリは正しいですが、パフォーマンス向上のために xxxxxx を検討で
          きます。
        ）
        """
        try:
            mcp_server_params = self._create_mcp_server_config()
            async with MCPServerStdio(
                name="MCP Elasticsearch Eval", params=mcp_server_params
            ) as server:
                trace_id = gen_trace_id()
                self.view.display_trace_info(trace_id)  # トレースURLを表示

                # OpenAI Platform でトレースを確認するための設定
                # workflow_name は適宜変更
                with trace(
                    workflow_name="ES Quest Agent Evaluation", trace_id=trace_id
                ):
                    evaluation_agent = Agent(
                        name="elasticsearch_evaluation_expert",
                        instructions=agent_instructions,
                        mcp_servers=[server],
                        # model="gpt-4-turbo" # 必要に応じてモデルを指定
                    )

                    # Runner.run に渡す input は agent_instructions 自体か、
                    # あるいはさらに具体的なタスク指示か、Agentライブラリの仕様による
                    # ここでは instructions に全て含めたので、input はシンプルにするか空にする
                    agent_input = "上記の指示に従って、ユーザーの回答を評価しフィードバックを生成してください。"

                    result = await Runner.run(
                        starting_agent=evaluation_agent, input=agent_input
                    )

                    if result.final_output is None:
                        raise AgentError(
                            "エージェントが最終的な評価フィードバックを生成できませんでした。"
                        )

                    return result.final_output.strip()  # 前後の空白を除去

        except ConnectionRefusedError as e:
            raise AgentError(
                f"MCP Serverへの接続に失敗しました。プロセスが起動しているか確認してください。詳細: {e}"
            ) from e
        except Exception as e:
            # Agentライブラリ固有のエラーや予期せぬエラー
            raise AgentError(
                f"エージェントの実行中に予期せぬエラーが発生しました: {e}"
            ) from e
