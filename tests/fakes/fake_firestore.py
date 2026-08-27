"""Minimal in-memory stand-in for a Firestore client, just enough to test
that FirestoreService never crosses uid boundaries (SECURITY-001)."""
from __future__ import annotations


class FakeSnapshot:
    def __init__(self, data: dict | None):
        self._data = data

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict | None:
        return self._data


class FakeDocRef:
    def __init__(self, path: str, store: dict):
        self.path = path
        self._store = store

    def set(self, data: dict) -> None:
        self._store[self.path] = dict(data)

    def update(self, data: dict) -> None:
        current = self._store.get(self.path, {})
        current.update(data)
        self._store[self.path] = current

    def get(self) -> FakeSnapshot:
        return FakeSnapshot(self._store.get(self.path))

    def collection(self, name: str) -> "FakeCollectionRef":
        return FakeCollectionRef(f"{self.path}/{name}", self._store)


class FakeCollectionRef:
    def __init__(self, path: str, store: dict):
        self.path = path
        self._store = store

    def document(self, doc_id: str) -> FakeDocRef:
        return FakeDocRef(f"{self.path}/{doc_id}", self._store)

    def where(self, *args, **kwargs) -> "FakeCollectionRef":
        return self

    def order_by(self, *args, **kwargs) -> "FakeCollectionRef":
        return self

    def limit(self, *args, **kwargs) -> "FakeCollectionRef":
        return self

    def stream(self):
        prefix = self.path + "/"
        for path, data in self._store.items():
            if path.startswith(prefix) and "/" not in path[len(prefix):]:
                yield FakeSnapshot(data)


class FakeFirestoreClient:
    """Backs every path with one shared dict, keyed by full document path —
    close enough to real Firestore's tree-of-documents shape for these tests."""

    def __init__(self):
        self._store: dict[str, dict] = {}

    def collection(self, name: str) -> FakeCollectionRef:
        return FakeCollectionRef(name, self._store)
