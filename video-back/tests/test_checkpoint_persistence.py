import gc
import sys
import tempfile
import unittest
from pathlib import Path
import sqlite3

sys.path.append(str(Path(__file__).resolve().parents[1]))

from langgraph.graph import StateGraph

from utils.persistent_checkpointer import PersistentInMemorySaver


class PersistentCheckpointTests(unittest.TestCase):
    def test_persistent_saver_restores_latest_checkpoint_after_recreate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "animation.sqlite3"

            builder = StateGraph(dict)
            builder.add_node("increment", lambda state: {"value": state.get("value", 0) + 1})
            builder.set_entry_point("increment")
            builder.set_finish_point("increment")

            first_saver = PersistentInMemorySaver(checkpoint_path)
            graph = builder.compile(checkpointer=first_saver)

            config = {"configurable": {"thread_id": "thread-1"}}
            result = graph.invoke({"value": 1}, config=config)
            self.assertEqual(result["value"], 2)
            self.assertTrue(checkpoint_path.exists())
            conn = sqlite3.connect(checkpoint_path)
            try:
                row = conn.execute(
                    "SELECT COUNT(*) FROM checkpoint_snapshots"
                ).fetchone()
            finally:
                conn.close()
            self.assertEqual(row[0], 1)

            second_saver = PersistentInMemorySaver(checkpoint_path)
            restored = second_saver.get_tuple(config)

            self.assertIsNotNone(restored)
            self.assertEqual(restored.config["configurable"]["thread_id"], "thread-1")
            self.assertEqual(restored.checkpoint["channel_values"]["__root__"]["value"], 2)

            del graph
            del first_saver
            del second_saver
            gc.collect()


if __name__ == "__main__":
    unittest.main()
