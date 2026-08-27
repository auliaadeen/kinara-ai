"""SECURITY-001: User A cannot access User B's documents.

Verifies FirestoreService structurally scopes every read/write under the
uid it was constructed with — there is no code path that lets one
instance touch another uid's subtree.
"""
from tests.fakes.fake_firestore import FakeFirestoreClient

from src.services.firestore_service import FirestoreService


def test_created_child_is_scoped_under_owning_uid():
    db = FakeFirestoreClient()
    fs_a = FirestoreService(db, "user-a")

    child = fs_a.create_child("Alice", "Grade 2", None)

    assert f"users/user-a/children/{child.child_id}" in db._store


def test_other_uid_cannot_see_first_users_children():
    db = FakeFirestoreClient()
    fs_a = FirestoreService(db, "user-a")
    fs_b = FirestoreService(db, "user-b")

    fs_a.create_child("Alice", "Grade 2", None)

    assert len(fs_a.list_children()) == 1
    assert len(fs_b.list_children()) == 0


def test_get_child_by_id_does_not_leak_across_uid():
    db = FakeFirestoreClient()
    fs_a = FirestoreService(db, "user-a")
    fs_b = FirestoreService(db, "user-b")

    child = fs_a.create_child("Alice", "Grade 2", None)

    assert fs_a.get_child(child.child_id) is not None
    assert fs_b.get_child(child.child_id) is None


def test_service_rejects_empty_uid():
    db = FakeFirestoreClient()
    try:
        FirestoreService(db, "")
    except ValueError:
        return
    raise AssertionError("expected ValueError for empty uid")
