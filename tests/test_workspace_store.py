"""Persistence survives separate reads and refuses stale writes."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import workspace_store


class WorkspaceStoreTests(unittest.TestCase):
    def test_persists_and_preserves_newer_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(workspace_store, "DB_PATH", os.path.join(folder, "state.sqlite3")):
                chat = {"msgs": [{"role": "user", "content": "Remember this"}], "mode": "auto"}
                self.assertTrue(workspace_store.save("chat", 20, chat)["saved"])
                self.assertFalse(workspace_store.save("chat", 19, {"msgs": []})["saved"])
                workspace_store.save("runs", 21, [{"task": "Build", "turns": [{"content": "Done"}]}])
                workspace_store.save("drafts", 22, {"project:chat:main": {"ch-in": {"value": "Unsent"}}})
                self.assertEqual(workspace_store.load()["chat"]["value"], chat)
                self.assertEqual(workspace_store.load()["runs"]["value"][0]["turns"][0]["content"], "Done")
                self.assertEqual(workspace_store.load()["drafts"]["value"]["project:chat:main"]["ch-in"]["value"], "Unsent")

    def test_rejects_invalid_sections(self):
        with self.assertRaises(ValueError):
            workspace_store.save("unknown", 1, [])
        with self.assertRaises(ValueError):
            workspace_store.save("history", 1, {})
        with self.assertRaises(ValueError):
            workspace_store.save("chat", 0, {"msgs": []})


if __name__ == "__main__":
    unittest.main()
