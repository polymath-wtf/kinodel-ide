"""Frozen image-only route: validate accepted refs, then one external group wait."""

from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.image_group_store import ImageGroupV1, read_image_group
from backend.image_group_results import (ImageGroupResultV1, read_image_group_result, read_image_group_wake,
                                         join_image_group_result)


class ImageState(TypedDict):
    project_id: str
    execution_id: str
    group_ref: dict[str, str]
    wait_ref: dict[str, str]
    result_ref: NotRequired[dict[str, str]]
    batch_outputs: NotRequired[str | None]


def initial_image_state(group: ImageGroupV1) -> ImageState:
    receipt = group.receipt
    return {'project_id': group.batch.prepared_input.source_plan_ref.project_id,
            'execution_id': receipt.execution_id,
            'group_ref': dict(group_id=receipt.group_id, batch_id=receipt.batch_id,
                             input_digest=receipt.input_digest), 'wait_ref': group.wait_token}


def image_result_ref(result: ImageGroupResultV1) -> dict[str, str]:
    return dict(result_id=result.result_id, digest=result.digest, uri=result.uri, status=result.status)


def build_image_graph(db, saver, group: ImageGroupV1):
    expected = initial_image_state(group)

    async def prepare_accepted_group(state: ImageState):
        if state != initial_image_state(read_image_group(db, group.receipt.execution_id)):
            raise ValueError('Image accepted group checkpoint mismatch')
        return {}

    async def group_wait(state: ImageState):
        if state != expected:
            raise ValueError('Image wait state mismatch')
        answer = interrupt(state['wait_ref'])
        current = read_image_group(db, group.receipt.execution_id)
        wake = read_image_group_wake(db, group.receipt.execution_id)
        if wake is None:
            raise ValueError('Unsolicited image group resume')
        result = read_image_group_result(db, group.receipt.execution_id)
        if (state != initial_image_state(current) or answer != image_result_ref(result)
                or (wake.source_id, wake.resume_ref, wake.payload_digest) !=
                (current.receipt.wait_id, result.result_id, result.digest)
                or (wake.checkpoint_id, wake.task_id, wake.interrupt_id) !=
                (current.checkpoint_id, current.task_id, current.interrupt_id)):
            raise ValueError('Unsolicited image group resume')
        return {'result_ref': image_result_ref(result)}

    async def exact_complete_set_join(state: ImageState):
        result = read_image_group_result(db, group.receipt.execution_id)
        if state != {**expected, 'result_ref': image_result_ref(result)}:
            raise ValueError('Image join state/result mismatch')
        joined = join_image_group_result(db, group.receipt.execution_id, wait_id=group.receipt.wait_id,
            result_id=result.result_id, expected_result_digest=result.digest,
            expected_request_digest=group.receipt.request_digest)
        return {'batch_outputs': joined.batch_outputs}

    graph = StateGraph(ImageState)
    graph.add_node('prepare_accepted_group', prepare_accepted_group)
    graph.add_node('group_wait', group_wait)
    graph.add_node('exact_complete_set_join', exact_complete_set_join)
    graph.add_edge(START, 'prepare_accepted_group')
    graph.add_edge('prepare_accepted_group', 'group_wait')
    graph.add_edge('group_wait', 'exact_complete_set_join')
    graph.add_edge('exact_complete_set_join', END)
    return graph.compile(checkpointer=saver)
