"""Frozen image-only route: validate accepted refs, then one external group wait."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.image_group_store import ImageGroupV1, read_image_group


class ImageState(TypedDict):
    project_id: str
    execution_id: str
    group_ref: dict[str, str]
    wait_ref: dict[str, str]


def initial_image_state(group: ImageGroupV1) -> ImageState:
    receipt = group.receipt
    return {'project_id': group.batch.prepared_input.source_plan_ref.project_id,
            'execution_id': receipt.execution_id,
            'group_ref': dict(group_id=receipt.group_id, batch_id=receipt.batch_id,
                             input_digest=receipt.input_digest), 'wait_ref': group.wait_token}


def build_image_graph(db, saver, group: ImageGroupV1):
    expected = initial_image_state(group)

    async def prepare_accepted_group(state: ImageState):
        if state != initial_image_state(read_image_group(db, group.receipt.execution_id)):
            raise ValueError('Image accepted group checkpoint mismatch')
        return {}

    async def group_wait(state: ImageState):
        if state != expected:
            raise ValueError('Image wait state mismatch')
        interrupt(state['wait_ref'])
        # No durable group result/wake exists in 7.1. Never consume an arbitrary answer.
        raise ValueError('Unsolicited image group resume')

    async def exact_complete_set_join(state: ImageState):
        raise ValueError('Image group has no durable complete-set result')

    graph = StateGraph(ImageState)
    graph.add_node('prepare_accepted_group', prepare_accepted_group)
    graph.add_node('group_wait', group_wait)
    graph.add_node('exact_complete_set_join', exact_complete_set_join)
    graph.add_edge(START, 'prepare_accepted_group')
    graph.add_edge('prepare_accepted_group', 'group_wait')
    graph.add_edge('group_wait', 'exact_complete_set_join')
    graph.add_edge('exact_complete_set_join', END)
    return graph.compile(checkpointer=saver)
