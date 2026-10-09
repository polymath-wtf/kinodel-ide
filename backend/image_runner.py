"""Image work handler for the existing runner, not a second invocation lifetime."""

from langgraph.types import Interrupt

from backend.image_graph import initial_image_state
from backend.image_group_store import bind_image_wait, read_image_group
from backend.story_control import cancel_requested


async def inspect_image_checkpoint(saver, graph, group):
    """Validate raw lineage/task writes before deciding whether an invocation is safe.

    This frozen opening route has exactly three checkpoint positions. In particular,
    pending writes must not hide a resume or an alien branch behind snapshot.next.
    """
    execution_id = group.receipt.execution_id
    expected = initial_image_state(group)
    config = {'configurable': {'thread_id': execution_id}}
    saved = await saver.aget_tuple(config)
    bound = (group.checkpoint_id, group.task_id, group.interrupt_id)
    if saved is None:
        if bound != (None, None, None):
            raise ValueError('Bound image wait has no checkpoint')
        return None, None
    cursor = saved
    step = saved.metadata.get('step')
    if type(step) is not int or step not in (-1, 0, 1):
        raise ValueError('Unsupported image checkpoint position')
    binding = None
    while cursor is not None:
        identity = cursor.config.get('configurable', {})
        if (identity.get('thread_id') != execution_id or identity.get('checkpoint_ns') != ''
                or not isinstance(identity.get('checkpoint_id'), str)
                or cursor.checkpoint['id'] != identity['checkpoint_id']
                or cursor.metadata.get('step') != step
                or cursor.metadata.get('source') != ('input' if step == -1 else 'loop')
                or cursor.metadata.get('parents') != {}):
            raise ValueError('Image checkpoint lineage mismatch')
        node = {-1: '__start__', 0: 'prepare_accepted_group', 1: 'group_wait'}[step]
        values = ({'__start__': expected} if step == -1 else {**expected, 'branch:to:' + node: None})
        if cursor.checkpoint['channel_values'] != values:
            raise ValueError('Image checkpoint state/token mismatch')
        snapshot = await graph.aget_state(cursor.config)
        if (snapshot.values != ({} if step == -1 else expected) or len(snapshot.tasks) != 1
                or snapshot.tasks[0].name != node or snapshot.tasks[0].path != ('__pregel_pull', node)
                or snapshot.next != (node,)):
            raise ValueError('Image checkpoint task mismatch')
        task = snapshot.tasks[0]
        allowed = ({**expected, 'branch:to:prepare_accepted_group': None} if step == -1
                   else {'branch:to:group_wait': None} if step == 0 else {})
        for task_id, channel, value in cursor.pending_writes:
            if task_id != task.id:
                raise ValueError('Image pending write task mismatch')
            if channel == '__interrupt__' and step == 1:
                if (len(cursor.pending_writes) != 1 or not isinstance(value, (list, tuple)) or len(value) != 1
                        or not isinstance(value[0], Interrupt)
                        or value[0].value != group.wait_token or not value[0].id
                        or snapshot.interrupts != tuple(value) or task.interrupts != tuple(value)
                        or task.error is not None or task.result is not None):
                    raise ValueError('Image interrupt token mismatch')
                if cursor is saved:
                    binding = (identity['checkpoint_id'], task.id, value[0].id)
            elif channel == '__error__' and isinstance(value, str):
                pass  # Unfinished pure task, recover with None; never a resume authorization.
            elif channel not in allowed or value != allowed[channel]:
                raise ValueError('Unexpected image pending write or resume')
        parent = cursor.parent_config
        if step == -1:
            if parent is not None:
                raise ValueError('Unexpected image input checkpoint parent')
            break
        if (parent is None or parent.get('configurable', {}).get('thread_id') != execution_id
                or parent['configurable'].get('checkpoint_ns') != ''):
            raise ValueError('Image checkpoint parent mismatch')
        cursor = await saver.aget_tuple(parent)
        if cursor is None:
            raise ValueError('Image checkpoint ancestor missing')
        step -= 1
    if bound != (None, None, None) and binding != bound:
        raise ValueError('Image wait binding differs from checkpoint')
    return saved, binding


async def run_image_work(db, saver, graph, work, stop, invoke):
    work_id, execution_id, kind, source_id, payload_digest, resume_ref = work
    group = read_image_group(db, execution_id)
    receipt = group.receipt
    if payload_digest != receipt.request_digest or resume_ref is not None:
        raise ValueError('Image work digest/resume mismatch')
    if kind == 'start':
        if (work_id, source_id) != (receipt.work_id, execution_id):
            raise ValueError('Image start work identity mismatch')
    elif kind != 'reconcile':
        raise ValueError('Unsupported image work kind')
    if db.execute('SELECT 1 FROM execution_outcomes WHERE execution_id=?', (execution_id,)).fetchone():
        raise ValueError('Image work has unexpected terminal outcome')
    saved, binding = await inspect_image_checkpoint(saver, graph, group)
    if kind == 'reconcile' and (saved is None or saved.config['configurable']['checkpoint_id'] != source_id):
        raise ValueError('Image reconcile checkpoint mismatch')
    if binding is None:
        config = {'configurable': {'thread_id': execution_id}}
        if not await invoke(db, graph, initial_image_state(group) if saved is None else None,
                            config, execution_id, stop):
            return
        saved, binding = await inspect_image_checkpoint(saver, graph, read_image_group(db, execution_id))
    if cancel_requested(db, execution_id):
        return
    if binding is None:
        raise ValueError('Image segment has no exact durable wait')
    checkpoint_id, task_id, interrupt_id = binding
    bind_image_wait(db, execution_id, receipt.wait_id, expected_request_digest=receipt.request_digest,
                    checkpoint_id=checkpoint_id, task_id=task_id, interrupt_id=interrupt_id)
    db.execute("UPDATE execution_work SET status='completed',settled_checkpoint_id=?,"
               'work_version=work_version+1 WHERE work_id=?', (checkpoint_id, work_id))
