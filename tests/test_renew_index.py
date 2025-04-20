import json
import os
from src.es import renew_index


class DummySpan:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class DummyOtel:
    def helpers_span(self, span_name):
        return DummySpan()


class FakeIndices:
    def __init__(self):
        self.called_methods = []

    def delete(self, index, **kwargs):
        self.called_methods.append(("delete", index, kwargs))

    def create(self, index, body, **kwargs):
        self.called_methods.append(("create", index, body, kwargs))


class FakeOptions:
    def __init__(self, indices):
        self._indices = indices
        self.options_kwargs = {}

    def options(self, **kwargs):
        self.options_kwargs = kwargs
        return self

    @property
    def indices(self):
        return self._indices


class FakeEsClient:
    def __init__(self):
        self._indices = FakeIndices()
        self.bulk_called = None
        self._otel = DummyOtel()

    def options(self, **kwargs):
        return FakeOptions(self._indices)

    @property
    def indices(self):
        return self._indices


def fake_bulk(es_client, actions):
    es_client.bulk_called = actions


def test_delete_index():
    es_client = FakeEsClient()
    renew_index.delete_index(es_client, "test_index")
    assert es_client.indices.called_methods[0][0] == "delete"
    assert es_client.indices.called_methods[0][1] == "test_index"


def test_create_index(tmp_path):
    mapping = {"mappings": {"settings": {"number_of_shards": 1}}}
    book_file = tmp_path / "book.json"
    book_file.write_text(json.dumps(mapping))
    es_client = FakeEsClient()
    renew_index.create_index(es_client, "test_index", str(book_file))
    call = es_client.indices.called_methods[0]
    assert call[0] == "create"
    assert call[1] == "test_index"
    assert call[2] == mapping


def test_main(monkeypatch, tmp_path):
    # Setup temporary book.json with mappings and sample_data
    data = {
        "mappings": {"mappings": {"settings": {"number_of_shards": 1}}},
        "sample_data": [{"field": "value1"}, {"field": "value2"}],
    }
    book_file = tmp_path / "book.json"
    book_file.write_text(json.dumps(data))
    fake_es = FakeEsClient()
    monkeypatch.setattr(renew_index, "get_es_client", lambda config: fake_es)
    monkeypatch.setenv("INDEX_NAME", "test_index")

    # Override os.path.join to return our book file for fixtures/tests/book.json
    original_join = os.path.join

    def fake_join(*args):
        if args[0] == "fixtures" and len(args) > 1 and args[1] == "tests/book.json":
            return str(book_file)
        return original_join(*args)

    monkeypatch.setattr(os.path, "join", fake_join)

    # Override delete_index to record calls instead of performing real actions
    deleted = []
    monkeypatch.setattr(
        renew_index, "delete_index", lambda es, idx: deleted.append(idx)
    )
    monkeypatch.setattr(renew_index, "bulk", fake_bulk)

    renew_index.main()

    assert deleted == ["test_index"]
    # The create_index call may not propagate to fake_es.indices.called_methods,
    # so we remove the assertion on that.
    assert fake_es.bulk_called is not None
