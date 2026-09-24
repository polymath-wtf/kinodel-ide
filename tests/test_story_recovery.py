"""Empirical checkpoint/recovery windows on the pinned SQLite saver and Story route."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from langgraph.types import Command

from backend.database import open_database
from backend.domain import StoryV1
from backend.review_store import accept_story_decision, bind_story_wait
from backend.review_store import apply_story_decision
from backend.saver import open_saver
from backend.story_graph import build_story_graph, initial_story_state
from backend.story_store import create_test_execution, read_story


def produce_story(message, shots, prior, feedback):
    return StoryV1(schema_id="story", schema_version="1",
                   hook="Night" if prior else "Light",
                   story="A fox appears.", shots=[dict(
                       shot_id="s1", action="Fox appears", narrative_function="Arrival",
                       subject_ids=[], state_before="Dark", state_after="Light")])


class StoryRecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel recovery ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        self.project, self.execution = str(uuid4()), str(uuid4())
        self.config = {"configurable": {"thread_id": self.execution}}

    async def start(self, db, saver):
        graph = build_story_graph(db, saver, produce_story)
        paused = await graph.ainvoke(initial_story_state(self.project, self.execution),
                                     self.config, durability="sync")
        self.assertEqual(len(paused["__interrupt__"]), 1)
        return graph

    async def bind_and_decide(self, db, graph, action, key):
        snapshot = await graph.aget_state(self.config)
        self.assertEqual(snapshot.next, ("story_wait",))
        self.assertEqual(len(snapshot.interrupts), 1)
        request = snapshot.interrupts[0].value
        bind_story_wait(db, self.execution, request["request_id"],
                        snapshot.config["configurable"]["checkpoint_id"],
                        snapshot.tasks[0].id, snapshot.interrupts[0].id)
        decision = accept_story_decision(db, self.execution, request["request_id"],
                                         request["digest"], request["binding_revision"],
                                         key, action, "Make it darker" if action == "revise" else None)
        return snapshot, request, decision

    async def test_unanswered_interrupt_survives_reopen_and_none_does_not_answer(self):
        with open_database(self.root) as db:
            create_test_execution(db, self.project, self.execution, "A fox", ["s1"])
            async with open_saver(self.root, db) as saver:
                graph = await self.start(db, saver)
                snapshot = await graph.aget_state(self.config)
                saved = await saver.aget_tuple(self.config)
                self.assertEqual(saved.config["configurable"]["checkpoint_id"],
                                 snapshot.config["configurable"]["checkpoint_id"])
                self.assertEqual(saved.checkpoint["channel_values"]["review_ref"],
                                 snapshot.interrupts[0].value)
                self.assertEqual(saved.checkpoint["channel_values"].get("decision_id"), None)
                self.assertTrue(any(task == snapshot.tasks[0].id and channel == "__interrupt__"
                                    and len(value) == 1 and value[0].id == snapshot.interrupts[0].id
                                    for task, channel, value in saved.pending_writes))
                first_id = snapshot.interrupts[0].id

        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                graph = build_story_graph(db, saver, produce_story)
                saved = await saver.aget_tuple(self.config)
                self.assertTrue(any(channel == "__interrupt__" for _, channel, _ in saved.pending_writes))
                paused = await graph.ainvoke(None, self.config, durability="sync")
                self.assertEqual(paused["__interrupt__"][0].id, first_id)
                self.assertEqual((await graph.aget_state(self.config)).next, ("story_wait",))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM review_requests").fetchone(), (1,))

    async def test_persisted_resume_before_apply_continues_with_none_to_new_wait(self):
        with open_database(self.root) as db:
            create_test_execution(db, self.project, self.execution, "A fox", ["s1"])
            async with open_saver(self.root, db) as saver:
                graph = await self.start(db, saver)
                first, request, decision = await self.bind_and_decide(db, graph, "revise", "edit-1")
                original_put = saver.aput
                tripped = False

                async def stop_after_persisted_resume(*args, **kwargs):
                    nonlocal tripped
                    result = await original_put(*args, **kwargs)
                    if not tripped and args[1]["channel_values"].get("decision_id") == decision.decision_id:
                        tripped = True
                        raise RuntimeError("stop after persisted resume, before apply")
                    return result

                saver.aput = stop_after_persisted_resume
                with self.assertRaisesRegex(RuntimeError, "before apply"):
                    await graph.ainvoke(Command(resume={first.interrupts[0].id: decision.decision_id}),
                                        self.config, durability="sync")
                self.assertTrue(tripped)
                self.assertEqual(db.execute("SELECT applied_activation FROM review_requests WHERE request_id=?",
                                            (request["request_id"],)).fetchone(), (None,))

        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                graph = build_story_graph(db, saver, produce_story)
                saved = await saver.aget_tuple(self.config)
                self.assertEqual(saved.checkpoint["channel_values"]["decision_id"], decision.decision_id)
                parent = await saver.aget_tuple(saved.parent_config)
                self.assertEqual(saved.pending_writes, [])
                self.assertTrue(any(task == first.tasks[0].id and channel == "__resume__"
                                    and value == [decision.decision_id]
                                    for task, channel, value in parent.pending_writes),
                                (saved.pending_writes, parent.pending_writes))
                self.assertEqual(parent.config["configurable"]["checkpoint_id"],
                                 first.config["configurable"]["checkpoint_id"])
                self.assertTrue(any(task == first.tasks[0].id and channel == "decision_id"
                                    and value == decision.decision_id
                                    for task, channel, value in parent.pending_writes))
                paused = await graph.ainvoke(None, self.config, durability="sync")
                self.assertEqual(len(paused["__interrupt__"]), 1)
                next_wait = await graph.aget_state(self.config)
                self.assertEqual(next_wait.next, ("story_wait",))
                self.assertNotEqual(next_wait.tasks[0].id, first.tasks[0].id)
                self.assertNotEqual(next_wait.interrupts[0].id, first.interrupts[0].id)
                self.assertNotEqual(next_wait.interrupts[0].value["request_id"], request["request_id"])
                self.assertEqual(next_wait.interrupts[0].value["revision"], 2)
                current = await saver.aget_tuple(self.config)
                self.assertTrue(any(task == next_wait.tasks[0].id and channel == "__interrupt__"
                                    for task, channel, _ in current.pending_writes))
                self.assertFalse(any(channel == "__resume__" for _, channel, _ in current.pending_writes))
                self.assertEqual(read_story(db, self.execution)[1].hook, "Night")
                self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (2,))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM review_requests").fetchone(), (2,))
                with self.assertRaisesRegex(ValueError, "stale or applied"):
                    accept_story_decision(db, self.execution, request["request_id"], request["digest"],
                                          request["binding_revision"], "late-1", "approve", None)
                stale = await graph.ainvoke(Command(resume={first.interrupts[0].id: decision.decision_id}),
                                            self.config, durability="sync")
                self.assertEqual(stale["__interrupt__"][0].id, next_wait.interrupts[0].id)
                self.assertEqual((await graph.ainvoke(None, self.config, durability="sync"))
                                 ["__interrupt__"][0].id, next_wait.interrupts[0].id)
                self.assertEqual(db.execute("SELECT decision_id FROM review_requests WHERE request_id=?",
                                             (next_wait.interrupts[0].value["request_id"],)).fetchone(), (None,))

    async def test_committed_apply_before_next_wait_replays_same_transition(self):
        with open_database(self.root) as db:
            create_test_execution(db, self.project, self.execution, "A fox", ["s1"])
            async with open_saver(self.root, db) as saver:
                graph = await self.start(db, saver)
                first, request, decision = await self.bind_and_decide(db, graph, "revise", "edit-1")

                def stop_after_apply(*args):
                    apply_story_decision(*args)
                    raise RuntimeError("stop after business apply")

                with patch("backend.story_graph.apply_story_decision", side_effect=stop_after_apply):
                    with self.assertRaisesRegex(RuntimeError, "after business apply"):
                        await graph.ainvoke(Command(resume={first.interrupts[0].id: decision.decision_id}),
                                            self.config, durability="sync")
                activation = db.execute("SELECT applied_activation FROM review_requests WHERE request_id=?",
                                        (request["request_id"],)).fetchone()[0]
                self.assertIsNotNone(activation)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (1,))

        with open_database(self.root) as db:
            async with open_saver(self.root, db) as saver:
                graph = build_story_graph(db, saver, produce_story)
                paused = await graph.ainvoke(None, self.config, durability="sync")
                self.assertEqual(paused["__interrupt__"][0].value["revision"], 2)
                self.assertEqual(db.execute("SELECT applied_activation FROM review_requests WHERE request_id=?",
                                            (request["request_id"],)).fetchone(), (activation,))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (2,))
                self.assertEqual(db.execute("SELECT COUNT(*) FROM review_requests").fetchone(), (2,))

if __name__ == "__main__":
    unittest.main()
