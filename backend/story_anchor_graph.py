"""Authored Story→review→Wardrobe→one anchor batch, on the original thread."""

from typing import NotRequired

from langgraph.graph import END
from langgraph.types import interrupt

from backend.image_graph import image_result_ref, initial_image_state
from backend.image_group_store import read_image_group, register_story_anchor_group
from backend.image_group_results import read_image_group_result, read_image_group_wake, join_image_group_result
from backend.story_graph import StoryState, story_graph_builder
from backend.wardrobe_store import read_committed_wardrobe_plan


class StoryAnchorState(StoryState):
    group_ref: NotRequired[dict[str, str]]
    wait_ref: NotRequired[dict[str, str]]
    result_ref: NotRequired[dict[str, str]]
    batch_outputs: NotRequired[str | None]


def anchor_group_state(group):
    return {k: v for k, v in initial_image_state(group).items() if k in ('group_ref', 'wait_ref')}


def validate_anchor_state(db, state):
    execution = state['execution_id']
    committed = read_committed_wardrobe_plan(db, execution, state['review_ref']['request_id'])
    if (state['wardrobe_plan'] != committed.ref.model_dump(mode='json')
            or state['approved_story'] != committed.pins.story_ref.model_dump(mode='json')
            or state['wardrobe_transition'] != committed.next_activation
            or state['wardrobe_activation'] != committed.pins.activation_id):
        raise ValueError('Story/anchor committed handoff mismatch')
    return committed


def build_story_anchor_graph(db, saver, produce_story, *, character_root=None):
    async def prepare_anchor_batch(state):
        validate_anchor_state(db, state)
        register_story_anchor_group(db, state['execution_id'], state['review_ref']['request_id'])
        return anchor_group_state(read_image_group(db, state['execution_id']))

    async def batch_wait(state):
        # Pure before interrupt: exact persisted refs only, no registration or I/O.
        answer = interrupt(state['wait_ref'])
        execution = state['execution_id']
        group = read_image_group(db, execution)
        wake = read_image_group_wake(db, execution)
        result = read_image_group_result(db, execution)
        validate_anchor_state(db, state)
        if (wake is None or answer != image_result_ref(result)
                or {key: state[key] for key in ('group_ref', 'wait_ref')} != anchor_group_state(group)
                or (wake.checkpoint_id, wake.task_id, wake.interrupt_id) !=
                   (group.checkpoint_id, group.task_id, group.interrupt_id)):
            raise ValueError('Unsolicited Story/anchor batch resume')
        return {'result_ref': image_result_ref(result)}

    async def exact_join(state):
        validate_anchor_state(db, state)
        execution = state['execution_id']
        group, result = read_image_group(db, execution), read_image_group_result(db, execution)
        if (state['result_ref'] != image_result_ref(result)
                or {key: state[key] for key in ('group_ref', 'wait_ref')} != anchor_group_state(group)):
            raise ValueError('Story/anchor join result mismatch')
        joined = join_image_group_result(db, execution, wait_id=group.receipt.wait_id,
            result_id=result.result_id, expected_result_digest=result.digest,
            expected_request_digest=group.receipt.request_digest)
        return {'batch_outputs': joined.batch_outputs}

    graph = story_graph_builder(db, produce_story, wardrobe=True, anchor_batch=True,
                               state_schema=StoryAnchorState, character_root=character_root)
    graph.add_node('prepare_anchor_batch', prepare_anchor_batch)
    graph.add_node('batch_wait', batch_wait)
    graph.add_node('exact_join', exact_join)
    graph.add_edge('wardrobe', 'prepare_anchor_batch')
    graph.add_edge('prepare_anchor_batch', 'batch_wait')
    graph.add_edge('batch_wait', 'exact_join')
    graph.add_edge('exact_join', END)
    return graph.compile(checkpointer=saver)
