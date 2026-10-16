"""Image work handler for the existing runner, not a second invocation lifetime."""

from langgraph.types import Command, Interrupt

from backend.image_graph import image_result_ref, initial_image_state
from backend.image_group_store import bind_image_wait, read_image_group
from backend.image_group_results import read_image_group_result, read_image_group_wake, join_image_group_result
from backend.story_control import cancel_requested


def check_image_control(db, execution_id, stop):
    if stop is not None and stop.is_set():
        from backend.story_runner import _WorkerStopped
        raise _WorkerStopped()
    if cancel_requested(db, execution_id):
        raise ValueError('Image work cancelling')  # Dispatcher finalizes control, not an integrity block.


def _joined_result(db, group, result):
    execution_id = group.receipt.execution_id
    joined = db.execute('SELECT 1 FROM image_group_joins WHERE group_id=?', (group.receipt.group_id,)).fetchone()
    outcome = db.execute('SELECT 1 FROM execution_outcomes WHERE execution_id=?', (execution_id,)).fetchone()
    if joined is None and outcome is None:
        return None
    if joined is None or result is None:
        raise ValueError('Image terminal outcome lacks its exact join receipt')
    # Existing receipt only: this revalidates offline lineage/outcome and performs no writes.
    return join_image_group_result(db, execution_id, wait_id=group.receipt.wait_id,
        result_id=result.result_id, expected_result_digest=result.digest,
        expected_request_digest=group.receipt.request_digest)


async def inspect_image_checkpoint(saver, graph, group, *, db=None, stop=None, anchor=False):
    """Validate every raw ancestor/task/write, including a consumed exact resume.

    Explicit snapshot configs avoid projected pending writes concealing raw state.
    Opening checkpoints keep their frozen shape; result refs appear only after wait.
    """
    if anchor:
        return await inspect_anchor_checkpoint(db, saver, graph, group, stop=stop)
    execution_id = group.receipt.execution_id
    expected = initial_image_state(group)
    def check_control():
        if db is not None:
            check_image_control(db, execution_id, stop)

    saved = await saver.aget_tuple({'configurable': {'thread_id': execution_id}})
    check_control()
    bound = (group.checkpoint_id, group.task_id, group.interrupt_id)
    if saved is None:
        if bound != (None, None, None):
            raise ValueError('Bound image wait has no checkpoint')
        if db is not None and db.execute('SELECT 1 FROM execution_outcomes WHERE execution_id=?',
                                        (execution_id,)).fetchone():
            raise ValueError('Image terminal outcome has no checkpoint/join lineage')
        return None, None
    result = wake = joined = None
    if db is not None:
        # Absence is allowed; corrupt/unpublished rows are never resume authorization.
        row = db.execute('SELECT publication_state FROM image_group_results WHERE group_id=?',
                         (group.receipt.group_id,)).fetchone()
        if row == ('published',):
            result = read_image_group_result(db, execution_id)
            wake = read_image_group_wake(db, execution_id)
        joined = _joined_result(db, group, result)
    ref = image_result_ref(result) if result is not None else None
    cursor = saved
    latest_step = step = saved.metadata.get('step')
    if type(step) is not int or step not in (-1, 0, 1, 2, 3):
        raise ValueError('Unsupported image checkpoint position')
    if step >= 2 and (ref is None or wake is None):
        raise ValueError('Image postwait checkpoint has no exact durable result/wake')
    if joined is not None and step < 2:
        raise ValueError('Image join receipt precedes its consumed wait')
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
        node = {-1: '__start__', 0: 'prepare_accepted_group', 1: 'group_wait',
                2: 'exact_complete_set_join', 3: None}[step]
        state = {**expected, **({'result_ref': ref} if step >= 2 else {}),
                 **({'batch_outputs': joined.batch_outputs} if step == 3 and joined is not None else {})}
        values = ({'__start__': expected} if step == -1 else
                  {**state, **({'branch:to:' + node: None} if node is not None else {})})
        if cursor.checkpoint['channel_values'] != values or (step == 3 and joined is None):
            raise ValueError('Image checkpoint state/token mismatch')
        snapshot = await graph.aget_state(cursor.config)
        check_control()
        if (snapshot.values != ({} if step == -1 else state)
                or snapshot.next != ((node,) if node else ())
                or len(snapshot.tasks) != (1 if node else 0)):
            raise ValueError('Image checkpoint task mismatch')
        if node is None:
            if cursor.pending_writes:
                raise ValueError('Image END checkpoint has pending writes')
        else:
            task = snapshot.tasks[0]
            if task.name != node or task.path != ('__pregel_pull', node):
                raise ValueError('Image checkpoint task mismatch')
            allowed = ({**expected, 'branch:to:prepare_accepted_group': None} if step == -1 else
                       {'branch:to:group_wait': None} if step == 0 else
                       {'result_ref': ref, 'branch:to:exact_complete_set_join': None} if step == 1 else
                       {'batch_outputs': joined.batch_outputs} if joined is not None else {})
            output_channels = set()
            resumed = False
            interrupted = False
            for task_id, channel, value in cursor.pending_writes:
                if task_id != task.id:
                    raise ValueError('Image pending write task mismatch')
                if channel == '__interrupt__' and step == 1:
                    if (not isinstance(value, (list, tuple)) or len(value) != 1
                            or not isinstance(value[0], Interrupt)
                            or value[0].value != group.wait_token or not value[0].id
                            or snapshot.interrupts != tuple(value) or task.interrupts != tuple(value)):
                        raise ValueError('Image interrupt token mismatch')
                    binding = (identity['checkpoint_id'], task.id, value[0].id)
                    interrupted = True
                elif channel == '__resume__' and step == 1:
                    if wake is None or value != [ref]:
                        raise ValueError('Conflicting or unsolicited image persisted resume')
                    resumed = True
                elif channel == '__error__' and isinstance(value, str):
                    pass  # Retry unfinished work with None, never a new resume authorization.
                elif channel not in allowed or value != allowed[channel]:
                    raise ValueError('Unexpected image pending write or resume')
                else:
                    output_channels.add(channel)
            if output_channels and output_channels != set(allowed):
                raise ValueError('Incomplete image pending task output')
            if step < latest_step and output_channels != set(allowed):
                raise ValueError('Image child checkpoint lacks its parent task output')
            if step == 1:
                if (resumed or output_channels or latest_step >= 2) and not (interrupted and resumed):
                    raise ValueError('Image wait output lacks its exact source interrupt/resume')
                if resumed:
                    assert wake is not None
                    if binding != (wake.checkpoint_id, wake.task_id, wake.interrupt_id):
                        raise ValueError('Image persisted resume is for another wait')
        parent = cursor.parent_config
        if step == -1:
            if parent is not None:
                raise ValueError('Unexpected image input checkpoint parent')
            break
        if (parent is None or parent.get('configurable', {}).get('thread_id') != execution_id
                or parent['configurable'].get('checkpoint_ns') != ''):
            raise ValueError('Image checkpoint parent mismatch')
        cursor = await saver.aget_tuple(parent)
        check_control()
        if cursor is None:
            raise ValueError('Image checkpoint ancestor missing')
        step -= 1
    if bound != (None, None, None) and binding != bound:
        raise ValueError('Image wait binding differs from checkpoint')
    return saved, binding


async def inspect_anchor_checkpoint(db, saver, graph, group, *, stop=None):
    """Validate the concrete three-node tail and its exact applied Story ancestor.

    Story loops have variable length, so use authored node positions, not the
    historical image-only route's absolute superstep numbers.
    """
    from backend.story_anchor_graph import anchor_group_state
    from backend.wardrobe_store import read_committed_wardrobe_plan
    from backend.story_runner import _source_wait
    execution = group.receipt.execution_id
    request = group.batch.prepared_input.story_approval.approval_request_id
    committed = read_committed_wardrobe_plan(db, execution, request)
    review = db.execute('SELECT trigger_activation,request_revision,previous_request_id,checkpoint_id,task_id,interrupt_id '
                        'FROM review_requests WHERE execution_id=? AND request_id=?', (execution, request)).fetchone()
    base = dict(project_id=committed.ref.project_id, execution_id=execution,
        story_activation=review[0], story_ref=committed.pins.story_ref.model_dump(mode='json'),
        binding_revision=committed.pins.story_binding_revision,
        review_ref=dict(request_id=request, revision=review[1], digest=committed.pins.approval_request_digest,
                        binding_revision=committed.pins.story_binding_revision),
        decision_id='', approved_story=committed.pins.story_ref.model_dump(mode='json'),
        wardrobe_activation=committed.pins.activation_id, wardrobe_plan=committed.ref.model_dump(mode='json'),
        wardrobe_transition=committed.next_activation)
    if review[2] is not None:
        base['previous_request_id'] = review[2]
    saved = await saver.aget_tuple({'configurable': {'thread_id': execution}})
    check_image_control(db, execution, stop)
    if saved is None:
        raise ValueError('Registered Story/anchor group has no checkpoint')
    published = db.execute('SELECT publication_state FROM image_group_results WHERE group_id=?',
                           (group.receipt.group_id,)).fetchone() == ('published',)
    result = read_image_group_result(db, execution) if published else None
    wake = read_image_group_wake(db, execution) if published else None
    joined = _joined_result(db, group, result)
    ref = image_result_ref(result) if result is not None else None
    nodes = ('prepare_anchor_batch', 'batch_wait', 'exact_join', None)
    values = saved.checkpoint['channel_values']
    branches = [n for n in nodes[:-1] if 'branch:to:' + n in values]
    if len(branches) > 1:
        raise ValueError('Story/anchor checkpoint has competing tail tasks')
    phase = nodes.index(branches[0]) if branches else 3
    if phase >= 2 and (result is None or wake is None):
        raise ValueError('Story/anchor postwait lacks exact result/wake')
    if joined is not None and phase < 2:
        raise ValueError('Story/anchor join precedes consumed wait')
    cursor, binding = saved, None
    step = saved.metadata.get('step')
    if type(step) is not int:
        raise ValueError('Story/anchor checkpoint step missing')
    latest_phase = phase
    while phase >= 0:
        identity = cursor.config['configurable']
        if (identity.get('thread_id') != execution or identity.get('checkpoint_ns') != ''
                or cursor.checkpoint['id'] != identity.get('checkpoint_id')
                or cursor.metadata.get('step') != step or cursor.metadata.get('source') != 'loop'
                or cursor.metadata.get('parents') != {}):
            raise ValueError('Story/anchor tail checkpoint lineage mismatch')
        node = nodes[phase]
        state = {**base, **(anchor_group_state(group) if phase >= 1 else {}),
                 **({'result_ref': ref} if phase >= 2 else {}),
                 **({'batch_outputs': joined.batch_outputs} if phase == 3 and joined else {})}
        expected = {**state, **({'branch:to:' + node: None} if node else {})}
        if cursor.checkpoint['channel_values'] != expected or (phase == 3 and joined is None):
            raise ValueError('Story/anchor tail state/token mismatch')
        snapshot = await graph.aget_state(cursor.config)
        check_image_control(db, execution, stop)
        if snapshot.values != state or snapshot.next != ((node,) if node else ()) or len(snapshot.tasks) != bool(node):
            raise ValueError('Story/anchor tail task mismatch')
        allowed = ({**anchor_group_state(group), 'branch:to:batch_wait': None} if phase == 0 else
                   {'result_ref': ref, 'branch:to:exact_join': None} if phase == 1 else
                   {'batch_outputs': joined.batch_outputs} if joined is not None else {})
        outputs, resumed, interrupted = set(), False, False
        for task_id, channel, value in cursor.pending_writes:
            if not node or task_id != snapshot.tasks[0].id:
                raise ValueError('Story/anchor pending task mismatch')
            if channel == '__interrupt__' and phase == 1:
                if (not isinstance(value, (list, tuple)) or len(value) != 1 or not isinstance(value[0], Interrupt)
                        or value[0].value != group.wait_token or not value[0].id
                        or snapshot.interrupts != tuple(value) or snapshot.tasks[0].interrupts != tuple(value)):
                    raise ValueError('Story/anchor batch interrupt mismatch')
                binding = (identity['checkpoint_id'], task_id, value[0].id)
                interrupted = True
            elif channel == '__resume__' and phase == 1:
                if wake is None or value != [ref]:
                    raise ValueError('Conflicting Story/anchor persisted resume')
                resumed = True
            elif channel == '__error__' and isinstance(value, str):
                pass
            elif channel not in allowed or value != allowed[channel]:
                raise ValueError('Unexpected Story/anchor pending output')
            else:
                outputs.add(channel)
        if (outputs and outputs != set(allowed)) or (phase < latest_phase and outputs != set(allowed)):
            raise ValueError('Incomplete Story/anchor pending output')
        if phase == 1:
            if (resumed or outputs or latest_phase >= 2) and not (resumed and interrupted):
                raise ValueError('Story/anchor wait lacks exact interrupt/resume')
            if resumed and binding != (wake.checkpoint_id, wake.task_id, wake.interrupt_id):
                raise ValueError('Story/anchor resume belongs to another wait')
        if phase == 0:
            break
        cursor = await saver.aget_tuple(cursor.parent_config) if cursor.parent_config else None
        check_image_control(db, execution, stop)
        if cursor is None:
            raise ValueError('Story/anchor tail ancestor missing')
        phase, step = phase - 1, step - 1
    # A valid tail cannot borrow an approval from a different checkpoint fork.
    while cursor is not None and cursor.config['configurable']['checkpoint_id'] != review[3]:
        cursor = await saver.aget_tuple(cursor.parent_config) if cursor.parent_config else None
        check_image_control(db, execution, stop)
    _source_wait(cursor, review[3], review[4], review[5], request)
    if [v for t, c, v in cursor.pending_writes if t == review[4] and c == '__resume__'] != [[committed.pins.decision_id]]:
        raise ValueError('Story/anchor approval lacks persisted exact resume')
    bound = (group.checkpoint_id, group.task_id, group.interrupt_id)
    if bound != (None, None, None) and binding != bound:
        raise ValueError('Story/anchor wait binding differs from checkpoint')
    return saved, binding


async def run_image_work(db, saver, graph, work, stop, invoke):
    work_id, execution_id, kind, source_id, payload_digest, resume_ref = work
    group = read_image_group(db, execution_id)
    receipt = group.receipt
    result = wake = None
    if kind == 'resume':
        result = read_image_group_result(db, execution_id)
        if (source_id, payload_digest, resume_ref) != (receipt.wait_id, result.digest, result.result_id):
            raise ValueError('Image resume work identity mismatch')
        wake = read_image_group_wake(db, execution_id)
        # read_result verified the sole wake row even before it can be delivered.
        if db.execute("SELECT work_id FROM execution_work WHERE execution_id=? AND kind='resume'",
                      (execution_id,)).fetchone() != (work_id,):
            raise ValueError('Image resume work identity mismatch')
    elif kind in ('start', 'reconcile'):
        if payload_digest != receipt.request_digest or resume_ref is not None:
            raise ValueError('Image work digest/resume mismatch')
        if kind == 'start' and (work_id, source_id) != (receipt.work_id, execution_id):
            raise ValueError('Image start work identity mismatch')
        if kind == 'reconcile':
            wake = read_image_group_wake(db, execution_id)
            if wake is not None:
                result = read_image_group_result(db, execution_id)
    else:
        raise ValueError('Unsupported image work kind')
    saved, binding = await inspect_image_checkpoint(saver, graph, group, db=db, stop=stop)
    check_image_control(db, execution_id, stop)
    if kind == 'reconcile' and (saved is None or saved.config['configurable']['checkpoint_id'] != source_id):
        raise ValueError('Image reconcile checkpoint mismatch')
    if kind == 'resume' and wake is None:
        db.execute("UPDATE execution_work SET status='pending',work_version=work_version+1 WHERE work_id=?", (work_id,))
        return  # Start/reconcile owns reaching and binding the pure opening wait.
    terminal = db.execute('SELECT 1 FROM execution_outcomes WHERE execution_id=?', (execution_id,)).fetchone()
    config = {'configurable': {'thread_id': execution_id}}
    if not terminal:
        step = saved.metadata['step'] if saved is not None else -2
        persisted_resume = saved is not None and any(c == '__resume__' for _, c, _ in saved.pending_writes)
        if wake is not None or binding is None or persisted_resume or step >= 2:
            invocation = initial_image_state(group) if saved is None else None
            if wake is not None and step == 1 and not persisted_resume:
                assert result is not None
                invocation = Command(resume={wake.interrupt_id: image_result_ref(result)})
            if not await invoke(db, graph, invocation, config, execution_id, stop):
                return
            check_image_control(db, execution_id, stop)
            group = read_image_group(db, execution_id)
            saved, binding = await inspect_image_checkpoint(saver, graph, group, db=db, stop=stop)
            check_image_control(db, execution_id, stop)
        if binding is None:
            raise ValueError('Image segment has no exact durable wait')
        if group.checkpoint_id is None:
            checkpoint_id, task_id, interrupt_id = binding
            bind_image_wait(db, execution_id, receipt.wait_id, expected_request_digest=receipt.request_digest,
                            checkpoint_id=checkpoint_id, task_id=task_id, interrupt_id=interrupt_id)
        if kind == 'resume' and not db.execute('SELECT 1 FROM execution_outcomes WHERE execution_id=?',
                                              (execution_id,)).fetchone():
            raise ValueError('Image resumed segment has no exact terminal join')
    assert saved is not None
    checkpoint_id = saved.config['configurable']['checkpoint_id']
    db.execute("UPDATE execution_work SET status='completed',settled_checkpoint_id=?,"
               'work_version=work_version+1 WHERE work_id=?', (checkpoint_id, work_id))
