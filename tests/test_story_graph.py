import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from langgraph.types import Command

from backend.database import open_database
from backend.domain import StoryV1
from backend.review_store import accept_story_decision, bind_story_wait
from backend.saver import open_saver
from backend.story_store import create_test_execution, read_story
from backend.story_graph import build_story_graph, initial_story_state


class StoryGraphTests(unittest.IsolatedAsyncioTestCase):
    async def test_revision_then_approval_survives_reopen_without_republishing(self):
        with tempfile.TemporaryDirectory(prefix="kinodel graph ") as directory:
            root = Path(directory) / "data"
            project, execution = str(uuid4()), str(uuid4())
            calls = []

            def produce(message, shots, prior, feedback):
                calls.append((message, shots, prior, feedback))
                return StoryV1(
                    schema_id="story", schema_version="1",
                    hook="Night" if prior else "Light",
                    story="The fox returns." if prior else "A fox appears.",
                    shots=[dict(shot_id="s1", action="Fox appears", narrative_function="Arrival",
                                subject_ids=[], state_before="Dark", state_after="Light")],
                )

            config = {"configurable": {"thread_id": execution}}

            async def bind_and_answer(db, graph, action, message, key):
                snapshot = await graph.aget_state(config)
                self.assertEqual(len(snapshot.interrupts), 1)
                request = snapshot.interrupts[0].value
                self.assertEqual(snapshot.next, ("story_wait",))
                bind_story_wait(db, execution, request["request_id"],
                                snapshot.config["configurable"]["checkpoint_id"],
                                snapshot.tasks[0].id, snapshot.interrupts[0].id)
                decision = accept_story_decision(db, execution, request["request_id"],
                                                 request["digest"], request["binding_revision"],
                                                 key, action, message)
                self.assertEqual(accept_story_decision(db, execution, request["request_id"],
                                                       request["digest"], request["binding_revision"],
                                                       key, action, message), decision)
                return request, decision

            with open_database(root) as db:
                create_test_execution(db, project, execution, "An idea", ["s1"])
                async with open_saver(root, db) as saver:
                    graph = build_story_graph(db, saver, produce)
                    paused = await graph.ainvoke(initial_story_state(project, execution), config, durability="sync")
                    self.assertEqual(len(paused["__interrupt__"]), 1)
                    first, decision = await bind_and_answer(db, graph, "revise", "Make it darker", "edit-1")
                    paused = await graph.ainvoke(
                        Command(resume={paused["__interrupt__"][0].id: decision.decision_id}),
                        config, durability="sync",
                    )
                    self.assertEqual(len(paused["__interrupt__"]), 1)
                    second = paused["__interrupt__"][0].value
                    self.assertNotEqual(first["request_id"], second["request_id"])
                    self.assertEqual(second["revision"], 2)
                    self.assertEqual(second["binding_revision"], 2)
                    self.assertEqual(len(calls), 2)
                    self.assertEqual(calls[1][3], "Make it darker")
                    self.assertEqual(calls[1][2].hook, "Light")
                    self.assertEqual(read_story(db, execution)[1].hook, "Night")

            with open_database(root) as db:
                async with open_saver(root, db) as saver:
                    graph = build_story_graph(db, saver, produce)
                    _, decision = await bind_and_answer(db, graph, "approve", None, "approve-2")
                    done = await graph.ainvoke(
                        Command(resume={ (await graph.aget_state(config)).interrupts[0].id: decision.decision_id}),
                        config, durability="sync",
                    )
                    self.assertEqual(done["approved_story"]["artifact_id"], read_story(db, execution)[0].artifact_id)
                    self.assertEqual((await graph.aget_state(config)).next, ())
                    self.assertEqual(len(calls), 2)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts").fetchone(), (2,))
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM review_requests").fetchone(), (2,))

    async def test_owner_must_return_typed_clarification(self):
        with tempfile.TemporaryDirectory(prefix="kinodel clarify ") as directory:
            root = Path(directory) / "data"
            project, execution = str(uuid4()), str(uuid4())
            config = {"configurable": {"thread_id": execution}}

            def produce(message, shots, prior, feedback):
                return StoryV1(schema_id="story", schema_version="1", hook="Light",
                               story="A fox appears.", shots=[dict(
                                   shot_id="s1", action="Fox appears", narrative_function="Arrival",
                                   subject_ids=[], state_before="Dark", state_after="Light")])

            with open_database(root) as db:
                create_test_execution(db, project, execution, "Idea", ["s1"])
                async with open_saver(root, db) as saver:
                    graph = build_story_graph(db, saver, produce)
                    paused = await graph.ainvoke(initial_story_state(project, execution), config, durability="sync")
                    request = paused["__interrupt__"][0].value
                    snapshot = await graph.aget_state(config)
                    bind_story_wait(db, execution, request["request_id"],
                                    snapshot.config["configurable"]["checkpoint_id"],
                                    snapshot.tasks[0].id, snapshot.interrupts[0].id)
                    decision = accept_story_decision(db, execution, request["request_id"], request["digest"],
                                                     1, "question", "clarify", "Why?")
                    with self.assertRaisesRegex(ValueError, "owner explanation"):
                        await graph.ainvoke(Command(resume={snapshot.interrupts[0].id: decision.decision_id}),
                                            config, durability="sync")
                    self.assertIsNotNone(db.execute("SELECT applied_activation FROM review_requests").fetchone()[0])
                    self.assertEqual(db.execute("SELECT owner_response FROM story_operations "
                                                "WHERE expected_revision=1").fetchone(), (None,))


if __name__ == "__main__":
    unittest.main()
