import json
import os

from src.es import renew_index


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
    mapping = {"mappings":{"settings": {"number_of_shards": 1}}}
    mapping_file = tmp_path / "mapping_book.json"
    mapping_file.write_text(json.dumps(mapping))
    es_client = FakeEsClient()
    renew_index.create_index(es_client, "test_index", str(mapping_file))
    call = es_client.indices.called_methods[0]
    assert call[0] == "create"
    assert call[1] == "test_index"
    assert call[2] == mapping


def test_append_documents(monkeypatch, tmp_path):
    docs = {"sample_data":[{"field": "value1"}, {"field": "value2", "_index": "custom_index"}]}
    ndjson_file = tmp_path / "sample_data_book.json"
    with ndjson_file.open("w") as f:
        for doc in docs:
            f.write(json.dumps(doc) + "\n")
    es_client = FakeEsClient()
    monkeypatch.setattr(renew_index, "bulk", fake_bulk)
    renew_index.append_documents(es_client, "test_index", str(ndjson_file))
    actions = es_client.bulk_called
    assert actions[0]["_index"] == "test_index"
    assert actions[0]["field"] == "value1"
    assert actions[1]["_index"] == "custom_index"
    assert actions[1]["field"] == "value2"


def test_main(monkeypatch, tmp_path):
    # Setup temporary mapping and ndjson files
    mapping = {"mappings":{"settings": {"number_of_shards": 1}}}
    mapping_file = tmp_path / "mappings_book.json"
    mapping_file.write_text(json.dumps(mapping))
    docs = {"sampled_data":[{"field": "value1"}, {"field": "value2"}]}
    ndjson_file = tmp_path / "sample_data_book.json"
    with ndjson_file.open("w") as f:
        for doc in docs:
            f.write(json.dumps(doc) + "\n")
    fake_es = FakeEsClient()
    monkeypatch.setattr(renew_index, "get_es_client", lambda config: fake_es)
    monkeypatch.setenv("INDEX_NAME", "test_index")

    # Override os.path.join to use our tmp_path when "fixtures" is the base directory
    original_join = os.path.join

    def fake_join(a, b):
        if a == "fixtures":
            return str(tmp_path / b)
        return original_join(a, b)

    monkeypatch.setattr(os.path, "join", fake_join)

    # Override delete_index, create_index, append_documents to record calls
    # instead of performing real actions
    deleted = []
    created = []
    appended = []
    monkeypatch.setattr(
        renew_index, "delete_index", lambda es, idx: deleted.append(idx)
    )
    monkeypatch.setattr(
        renew_index,
        "create_index",
        lambda es, idx, mapping_file: created.append((idx, mapping_file)),
    )
    monkeypatch.setattr(
        renew_index,
        "append_documents",
        lambda es, idx, ndjson_file: appended.append((idx, ndjson_file)),
    )

    renew_index.main()

    assert deleted == ["test_index"]
    assert created[0][0] == "test_index"
    assert appended[0][0] == "test_index"
