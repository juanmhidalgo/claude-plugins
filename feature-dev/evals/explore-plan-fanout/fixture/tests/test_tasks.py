import unittest

from app.tasks import TaskStore, serialize


class TaskStoreTest(unittest.TestCase):
    def setUp(self):
        self.store = TaskStore()

    def test_add_rejects_empty_title(self):
        with self.assertRaises(ValueError):
            self.store.add("   ")

    def test_list_filters_by_status(self):
        first = self.store.add("write docs")
        self.store.add("ship release")
        self.store.complete(first.id)
        self.assertEqual([t.title for t in self.store.list(status="done")], ["write docs"])
        self.assertEqual([t.title for t in self.store.list(status="open")], ["ship release"])

    def test_serialize_shape(self):
        task = self.store.add("review plan")
        self.assertEqual(set(serialize(task)), {"id", "title", "status"})


if __name__ == "__main__":
    unittest.main()
