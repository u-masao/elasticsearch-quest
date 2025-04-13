# src/exceptions.py
class QuestCliError(Exception):
    """CLIアプリケーションのベース例外"""

    pass


class InitializationError(QuestCliError):
    """初期化関連のエラー"""

    pass


class DatabaseError(QuestCliError):
    """データベース関連のエラー"""

    pass


class ElasticsearchError(QuestCliError):
    """Elasticsearch関連のエラー"""

    pass


class QuestNotFoundError(QuestCliError):
    """クエストが見つからないエラー"""

    pass


class InvalidQueryError(QuestCliError):
    """無効なクエリやクエリソースに関するエラー"""

    pass


class AgentError(QuestCliError):
    """エージェント関連のエラー"""

    pass
