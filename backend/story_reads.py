"""SQL-only read projections of committed internal Story records (not file integrity checks)."""

import json
import sqlite3

from backend.domain import OwnerResponseV1, canonical_json, make_operation_id, sha256_digest
from backend.review_store import REVIEW_ACTION_LIMIT
from backend.story_start import LIVE_GRAPH_ID, STORY_GRAPH_IDS, reject_retired_wardrobe
from backend import wardrobe_store


def _rows(db: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    cursor = db.execute(sql, params)
    return [dict(zip((column[0] for column in cursor.description), row)) for row in cursor.fetchall()]


def retired_wardrobe_counts(db: sqlite3.Connection) -> dict:
    """SQL-only inventory under data ownership; never load obsolete bodies/checkpoints."""
    retired = (wardrobe_store.RETIRED_GRAPH_ID, wardrobe_store.RETIRED_GRAPH_VERSION, wardrobe_store.RETIRED_GRAPH_DIGEST)
    where = "e.graph_id=? AND e.graph_version=? AND e.graph_digest=?"
    counts = {"executions": db.execute("SELECT COUNT(*) FROM executions e WHERE " + where, retired).fetchone()[0]}
    counts["work_statuses"] = dict(db.execute("SELECT w.status,COUNT(*) FROM execution_work w "
        "JOIN executions e ON e.execution_id=w.execution_id WHERE " + where + " GROUP BY w.status", retired).fetchall())
    for table in ("story_operations", "wardrobe_operations", "artifacts", "review_requests", "execution_controls"):
        counts[table] = db.execute(f"SELECT COUNT(*) FROM {table} r JOIN executions e ON e.execution_id=r.execution_id WHERE "
                                   + where, retired).fetchone()[0]
    return counts


def _ref(artifact: dict, project_id: str, execution_id: str) -> dict:
    return {"artifact_id": artifact["artifact_id"], "project_id": project_id,
            "execution_id": execution_id, "operation_id": artifact["operation_id"],
            "schema_id": artifact["schema_id"], "schema_version": artifact["schema_version"],
            "produced_by_stage": artifact["produced_by_stage"], "digest": artifact["digest"],
            "uri": artifact["uri"], "media_type": "application/json"}


def _overview(db: sqlite3.Connection, execution_id: str) -> dict:
    outcomes = _rows(db, "SELECT outcome,source_id,subject_artifact_id FROM execution_outcomes "
                     "WHERE execution_id=?", (execution_id,))
    outcome = outcomes[0] if outcomes else None
    cancelling = bool(_rows(db, "SELECT 1 FROM execution_controls WHERE execution_id=? AND kind='cancel'",
                            (execution_id,)))
    work = _rows(db, "SELECT work_id,kind,status,blocked_reason,work_version FROM execution_work "
                 "WHERE execution_id=? ORDER BY rowid", (execution_id,))
    bindings = _rows(db, "SELECT artifact_id,binding_revision FROM execution_bindings "
                     "WHERE execution_id=? AND slot='story'", (execution_id,))
    binding = bindings[0] if bindings else None
    candidate = _rows(db, "SELECT r.request_id,r.request_digest,r.request_revision,r.binding_revision,"
                      "r.subject_artifact_id,r.subject_digest,r.checkpoint_id,r.decision_id,"
                      "r.applied_activation,a.digest AS artifact_digest "
                      "FROM review_requests r LEFT JOIN artifacts a ON a.artifact_id=r.subject_artifact_id "
                      "AND a.execution_id=r.execution_id WHERE r.execution_id=? "
                      "ORDER BY r.request_revision DESC LIMIT 1", (execution_id,))
    review = None
    if candidate and not outcome and not cancelling:
        r = candidate[0]
        if (r["checkpoint_id"] is not None and r["decision_id"] is None
                and r["applied_activation"] is None and r["subject_digest"] == r["artifact_digest"]
                and binding == {"artifact_id": r["subject_artifact_id"],
                                "binding_revision": r["binding_revision"]}):
            review = {"request_id": r["request_id"], "digest": r["request_digest"],
                      "revision": r["request_revision"], "binding_revision": r["binding_revision"],
                      "subject_artifact_id": r["subject_artifact_id"]}
    status = (outcome["outcome"] if outcome else "cancelling" if cancelling else "blocked" if any(
        item["status"] == "blocked" for item in work) else "waiting_review" if review else "running")
    return {"outcome": outcome, "work": work, "binding": binding, "review": review, "status": status}


def _wardrobe_projection(db: sqlite3.Connection, execution_id: str, project_id: str, overview: dict) -> dict:
    """Public plan metadata and safe resolution, never frozen provider/image envelopes."""
    plans = _rows(db, "SELECT a.artifact_id,a.operation_id,a.digest,a.uri,a.schema_id,a.schema_version,a.produced_by_stage "
                  "FROM execution_bindings b LEFT JOIN artifacts a ON a.artifact_id=b.artifact_id "
                  "AND a.execution_id=b.execution_id WHERE b.execution_id=? AND b.slot='wardrobe_plan'", (execution_id,))
    ref = None
    if plans:
        plan = plans[0]
        if (plan["schema_id"], plan["schema_version"], plan["produced_by_stage"]) != ("visual_anchor_plan", "2", "wardrobe"):
            raise ValueError("Recorded Wardrobe plan schema/owner mismatch")
        ref = _ref(plan, project_id, execution_id)
    outcome = overview["outcome"]
    if outcome and outcome["outcome"] == "completed" and (ref is None or
            (outcome["source_id"], outcome["subject_artifact_id"]) != (ref["operation_id"], ref["artifact_id"])):
        raise ValueError("Recorded Wardrobe completion does not match its plan")
    stop = None
    explanations = {
        "wardrobe_unavailable": "Wardrobe is temporarily unavailable. Retry uses the same inputs and remaining allowance.",
        "wardrobe_exhausted": "Wardrobe's two completion attempts are exhausted. Cancel or start a new run.",
        "wardrobe_invalid_output": "Wardrobe could not produce a valid plan within its repair allowance. Cancel or start a new run.",
        "wardrobe_invalid": "Wardrobe inputs, configuration or saved result could not be validated. Cancel or start a new run.",
    }
    for work in overview["work"] if overview["status"] == "blocked" else []:
        reason = work["blocked_reason"]
        if work["status"] != "blocked" or reason not in (*explanations, "wardrobe_needs_input", "wardrobe_out_of_scope"):
            continue
        records = _rows(db, "SELECT owner_attempts,candidate_kind,candidate_body,next_activation FROM wardrobe_operations "
                        "WHERE execution_id=? ORDER BY rowid DESC LIMIT 1", (execution_id,))
        record = records[0] if records else None
        explanation = explanations.get(reason)
        if reason in ("wardrobe_needs_input", "wardrobe_out_of_scope"):
            if record is None or record["candidate_kind"] != "response" or record["next_activation"] is None:
                raise ValueError("Recorded Wardrobe stop has no committed explanation")
            response = OwnerResponseV1.model_validate_json(record["candidate_body"])
            if reason != f"wardrobe_{response.status}":
                raise ValueError("Recorded Wardrobe stop status mismatch")
            explanation = response.explanation
        retryable = reason == "wardrobe_unavailable" and (record is None or (
            record["owner_attempts"] < 2 and record["candidate_body"] is None and record["next_activation"] is None))
        stop = {"work_id": work["work_id"], "reason": reason, "explanation": explanation,
                "allowed_actions": (["retry"] if retryable else []) + ["cancel", "new_run"]}
        break
    return {"wardrobe_plan_ref": ref, "wardrobe_stop": stop}


def story_projection(db: sqlite3.Connection, execution_id: str) -> dict | None:
    """Read only canonical business metadata; no checkpoint, graph or artifact-body access."""
    reject_retired_wardrobe(db, execution_id)
    executions = _rows(db, "SELECT project_id,input_message,shot_ids,client_key,start_digest,"
                       "graph_id,graph_version,graph_digest,owner_config FROM executions "
                        "WHERE execution_id=? AND graph_id IN (?,?,?)", (execution_id, *STORY_GRAPH_IDS))
    if not executions:
        return None
    row = executions[0]
    wardrobe = row["graph_id"] == wardrobe_store.GRAPH_ID
    project_id = row["project_id"]
    overview = _overview(db, execution_id)
    outcome, binding = overview["outcome"], overview["binding"]
    artifacts = _rows(db, "SELECT a.artifact_id,a.operation_id,a.digest,a.uri,a.schema_id,a.schema_version,"
                      "a.produced_by_stage,o.expected_revision,o.artifact_id AS committed_artifact_id "
                      "FROM artifacts a LEFT JOIN story_operations o ON o.operation_id=a.operation_id "
                       "AND o.execution_id=a.execution_id WHERE a.execution_id=? AND a.schema_id='story' "
                       "AND a.schema_version IN ('1','2') AND a.produced_by_stage='storytell' ORDER BY a.rowid", (execution_id,))
    stories = [{"ref": _ref(a, project_id, execution_id),
                "version": ((a["expected_revision"] or 0) + 1 if a["committed_artifact_id"] == a["artifact_id"]
                            else binding["binding_revision"] if binding and binding["artifact_id"] == a["artifact_id"]
                            else None),
                "current": bool(binding and binding["artifact_id"] == a["artifact_id"])} for a in artifacts]
    refs = {item["ref"]["artifact_id"]: item["ref"] for item in stories}
    requests = _rows(db, "SELECT r.request_id,r.request_digest,r.request_revision,r.binding_revision,"
                     "r.subject_artifact_id,r.subject_digest,r.previous_request_id,r.checkpoint_id,"
                     "r.decision_id,r.action,r.message,r.applied_activation,"
                     "w.work_id,w.status AS work_status,o.artifact_id AS result_artifact_id,"
                     "o.operation_id AS result_operation_id,o.owner_response,o.prepared_inputs,"
                     "o.input_digest,o.expected_revision,o.next_activation,o.discussion_activation "
                     "FROM review_requests r LEFT JOIN execution_work w ON w.execution_id=r.execution_id "
                     "AND w.kind='resume' AND w.source_id=r.request_id "
                     "LEFT JOIN story_operations o ON o.execution_id=r.execution_id "
                     "AND o.activation_id=r.applied_activation "
                     "WHERE r.execution_id=? ORDER BY r.request_revision", (execution_id,))
    reviews = []
    continued = {request["previous_request_id"] for request in requests}
    for request in requests:
        base = refs.get(request["subject_artifact_id"])
        if base is None or base["digest"] != request["subject_digest"]:
            raise ValueError("Recorded review subject does not match its artifact")
        result = None
        if request["applied_activation"] is not None:
            activation = sha256_digest(json.dumps(
                ["kinodel.story-review-apply.v1", request["request_id"], request["decision_id"], request["action"]],
                ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            if request["applied_activation"] != activation:
                raise ValueError("Recorded review activation does not match its decision")
            if request["action"] == "approve":
                if wardrobe:
                    if (binding != {"artifact_id": base["artifact_id"], "binding_revision": request["binding_revision"]}
                            or request["result_operation_id"] is not None):
                        raise ValueError("Recorded approval does not match its Story handoff")
                elif (not outcome or outcome["outcome"] != "completed"
                        or outcome["source_id"] != request["request_id"]
                        or outcome["subject_artifact_id"] != base["artifact_id"]
                        or request["result_operation_id"] is not None):
                    raise ValueError("Recorded approval does not match its outcome")
                result = {"kind": "approved_subject", "ref": base, "response": None}
            elif request["result_operation_id"] is not None:
                operation = make_operation_id(execution_id, "storytell", activation, request["action"])
                pinned = json.loads(request["prepared_inputs"])
                # The stored owner-v2 tuple pins action, request, exact base, feedback and frozen discussion.
                matching_inputs = (isinstance(pinned, list) and len(pinned) == 6
                                   and pinned[:5] == ["test-story-owner-v2", request["action"], request["request_id"],
                                                      base, request["message"]] and isinstance(pinned[5], list))
                if row["owner_config"] is not None:
                    adapter_version = json.loads(row["owner_config"])["adapter_version"]
                    matching_inputs = (isinstance(pinned, list) and len(pinned) == 7
                                       and pinned[:5] == [f"live-story-owner-v{adapter_version}", request["action"], request["request_id"], base, request["message"]]
                                       and isinstance(pinned[5], list)
                                       and pinned[6] == sha256_digest(row["owner_config"].encode("utf-8")))
                # Match the earlier tuple already supported by prepare_story_operation replay.
                earlier_revision = (request["action"] == "revise" and request["owner_response"] is None
                                    and pinned == ["test-story-revise-v1", base, request["message"]])
                if (not (matching_inputs or earlier_revision) or request["result_operation_id"] != operation
                        or request["expected_revision"] != request["binding_revision"]
                        or request["input_digest"] != sha256_digest(request["prepared_inputs"].encode("utf-8"))):
                    raise ValueError("Recorded owner operation does not match its review inputs")
                if request["result_artifact_id"] is not None:
                    revised = refs.get(request["result_artifact_id"])
                    trigger = sha256_digest(json.dumps(
                        ["kinodel.story-transition.v1", operation, "story-hitl"], separators=(",", ":")).encode("utf-8"))
                    if (request["action"] != "revise" or revised is None or revised == base
                            or revised["operation_id"] != operation or request["owner_response"] is not None
                            or request["discussion_activation"] is not None or request["next_activation"] != trigger):
                        raise ValueError("Recorded revised Story does not match its owner operation")
                    result = {"kind": "revised_story", "ref": revised, "response": None}
                elif request["owner_response"] is not None:
                    response = OwnerResponseV1.model_validate_json(request["owner_response"])
                    trigger = sha256_digest(json.dumps(
                        ["kinodel.story-discussion.v1", operation, request["input_digest"]],
                        separators=(",", ":")).encode("utf-8"))
                    if (response.status not in ({"clarified"} if request["action"] == "clarify"
                                                else {"needs_input", "out_of_scope"})
                            or request["discussion_activation"] != trigger or request["next_activation"] is not None):
                        raise ValueError("Recorded owner response does not match its review action")
                    result = {"kind": "owner_response", "ref": None, "response": response.model_dump(mode="json")}
                elif request["discussion_activation"] is not None or request["next_activation"] is not None:
                    raise ValueError("Recorded owner transition has no committed result")
            if (request["action"] in ("revise", "clarify") and result is None
                    and (request["work_status"] == "completed" or request["request_id"] in continued)):
                raise ValueError("Finished owner review has no committed result")
        reviews.append({"request_id": request["request_id"], "digest": request["request_digest"],
                        "revision": request["request_revision"], "binding_revision": request["binding_revision"],
                        "previous_request_id": request["previous_request_id"], "base_ref": base,
                        "accepted": request["decision_id"] is not None,
                        "applied": request["applied_activation"] is not None,
                        "decision_id": request["decision_id"], "work_id": request["work_id"],
                        "action": request["action"], "message": request["message"], "result": result})
    remaining = {action: max(0, REVIEW_ACTION_LIMIT - sum(r["action"] == action and r["accepted"]
                                                         for r in reviews)) for action in ("revise", "clarify")}
    allowed = (["approve"] + [action for action in ("revise", "clarify") if remaining[action]]
               if overview["review"] else [])
    return {"execution_id": execution_id, "project_id": project_id, "status": overview["status"],
            "outcome": outcome, "submitted": {"input_message": row["input_message"],
            "shot_ids": json.loads(row["shot_ids"]), "client_key": row["client_key"],
             "start_digest": row["start_digest"],
             **({"text_brief": json.loads(row["owner_config"])["brief"],
                 "selected_characters": json.loads(row["owner_config"]).get("selected_characters", [])}
                if row["owner_config"] else {})},
             "graph": {"id": row["graph_id"], "version": row["graph_version"], "digest": row["graph_digest"]},
             **({"model": json.loads(row["owner_config"])["model"]} if row["owner_config"] else {}),
            "work": overview["work"], "stories": stories, "reviews": reviews, "review": overview["review"],
             "remaining_actions": remaining, "allowed_actions": allowed,
             **(_wardrobe_projection(db, execution_id, project_id, overview) if wardrobe else {})}


def recent_story_executions(db: sqlite3.Connection, limit: int) -> list[dict]:
    retired = (wardrobe_store.RETIRED_GRAPH_ID, wardrobe_store.RETIRED_GRAPH_VERSION, wardrobe_store.RETIRED_GRAPH_DIGEST)
    ids = db.execute("SELECT execution_id,project_id,input_message FROM executions WHERE graph_id IN (?,?,?) "
                      "AND NOT (graph_id IS ? AND graph_version IS ? AND graph_digest IS ?) "
                      "ORDER BY rowid DESC LIMIT ?", (*STORY_GRAPH_IDS, *retired, limit)).fetchall()
    items = []
    for execution_id, project_id, message in ids:
        overview = _overview(db, execution_id)
        bindings = _rows(db, "SELECT a.artifact_id,a.operation_id,a.digest,a.uri,a.schema_id,a.schema_version,"
                         "a.produced_by_stage,b.binding_revision FROM execution_bindings b "
                         "JOIN artifacts a ON a.artifact_id=b.artifact_id AND a.execution_id=b.execution_id "
                         "WHERE b.execution_id=? AND b.slot='story'", (execution_id,))
        current = ({"ref": _ref(bindings[0], project_id, execution_id),
                    "version": bindings[0]["binding_revision"], "current": True} if bindings else None)
        items.append({"execution_id": execution_id, "project_id": project_id,
                      "input_preview": message[:160], "status": overview["status"], "current_story": current})
    return items


def story_activity(db: sqlite3.Connection, execution_id: str) -> dict | None:
    """Safe recorded model inputs/results, never provider envelopes or private reasoning."""
    from backend.openrouter import STORY_DIAGNOSTIC, read_owner_config

    projection = story_projection(db, execution_id)
    if projection is None:
        raise LookupError("Unknown Story execution")
    body = db.execute("SELECT owner_config FROM executions WHERE execution_id=?", (execution_id,)).fetchone()[0]
    if body is None:
        if projection["graph"]["id"] in (LIVE_GRAPH_ID, wardrobe_store.GRAPH_ID):
            raise ValueError("Missing frozen Story owner configuration")
        return None  # Historical fixture has no system prompt or provider call.
    config = read_owner_config(body)
    operations = []
    for row in _rows(db, "SELECT operation_id,prepared_inputs,owner_request,owner_request_digest,owner_attempts,owner_repairs,"
                     "artifact_id,owner_response,owner_validation_diagnostic FROM story_operations WHERE execution_id=? ORDER BY rowid", (execution_id,)):
        task = None
        if row["owner_request"] is not None:
            request = json.loads(row["owner_request"])
            if (sha256_digest(row["owner_request"].encode("utf-8")) != row["owner_request_digest"]
                    or request["model"] != config.model
                    or request["messages"][0] != {"role": "system", "content": config.system_prompt}):
                raise ValueError("Recorded Story model request mismatch")
            task = json.loads(request["messages"][1]["content"])
        ref = next((s["ref"] for s in projection["stories"] if s["ref"]["artifact_id"] == row["artifact_id"]), None)
        response = OwnerResponseV1.model_validate_json(row["owner_response"]).model_dump(mode="json") if row["owner_response"] else None
        status = ("saved" if ref or response else "stopped" if projection["status"] in ("cancelled", "cancelling", "failed")
                  else "blocked" if projection["status"] == "blocked" else "attempted" if row["owner_attempts"] else "prepared")
        prepared = json.loads(row["prepared_inputs"])
        action = prepared[1] if prepared[0] == f"live-story-owner-v{config.adapter_version}" else "generate"
        if task is not None and task["action"] != action:
            raise ValueError("Recorded Story activity action mismatch")
        operations.append({"operation_id": row["operation_id"], "action": action,
                           "status": status, "reserved_attempts": row["owner_attempts"], "repairs": row["owner_repairs"],
                           "input": task, "story_ref": ref, "response": response,
                           "validation_diagnostic": (STORY_DIAGNOSTIC.validate_json(row["owner_validation_diagnostic"]).model_dump(mode="json")
                                                     if row["owner_validation_diagnostic"] else None)})
    return {"model": config.model, "system_prompt": config.system_prompt, "prompt_digest": config.prompt_digest,
            "operations": operations}


def wardrobe_activity(db: sqlite3.Connection, execution_id: str, *, include_validation_diagnostic: bool = False) -> dict | None:
    """Allowlisted frozen inspection only; no provider, current environment or library reads."""
    projection = story_projection(db, execution_id)
    if projection is None or projection["graph"] != {"id": wardrobe_store.GRAPH_ID,
            "version": wardrobe_store.GRAPH_VERSION, "digest": wardrobe_store.GRAPH_DIGEST}:
        raise LookupError("Unknown Story-Wardrobe execution")
    rows = db.execute("SELECT operation_id FROM wardrobe_operations WHERE execution_id=?", (execution_id,)).fetchall()
    if not rows:
        stop = projection["wardrobe_stop"]
        if include_validation_diagnostic and stop is not None and stop["reason"] == "wardrobe_invalid":
            from backend.openrouter_wardrobe import wardrobe_input_size_diagnostic

            request = projection["reviews"][-1]["request_id"]
            _, supplied, _ = wardrobe_store.wardrobe_authority(db, execution_id, request)
            diagnostic = wardrobe_input_size_diagnostic(supplied)
            if diagnostic is not None:
                return {"operation_id": None, "approval_request_id": request,
                        "input_digest": sha256_digest(canonical_json(supplied)),
                        "validation_diagnostic": diagnostic.model_dump(mode="json")}
        return None  # Preparation has not been committed; never substitute Story's model or env.
    if len(rows) != 1:
        raise ValueError("Multiple Wardrobe operations")
    record = wardrobe_store.read_wardrobe_operation(db, rows[0][0])
    pins, config = record["pins"], record["config"]
    ref = config.wardrobe_input.narrative_ref.model_dump(mode="json")
    if not any(r["request_id"] == pins.approval_request_id and r["applied"]
               and r["result"] == {"kind": "approved_subject", "ref": ref, "response": None}
               for r in projection["reviews"]):
        raise ValueError("Wardrobe inspection approval mismatch")
    activity = {"operation_id": record["operation_id"], "approval_request_id": pins.approval_request_id,
            "input_digest": config.input_digest, "input": config.wardrobe_input.model_dump(mode="json"),
            "config": {"provider": "OpenRouter", **{key: getattr(config, key) for key in (
                "adapter_version", "model", "system_prompt", "prompt_digest", "model_metadata_digest",
                "timeout_seconds", "max_tokens", "reasoning_effort")},
                "model_metadata": config.model_metadata.model_dump(mode="json")}}
    if include_validation_diagnostic:
        activity["attempts"] = {"reserved_attempts": record["owner_attempts"], "remaining_attempts": 2 - record["owner_attempts"],
                               "repairs": record["owner_repairs"],
                               "diagnostic": record["diagnostic"].model_dump(mode="json") if record["diagnostic"] is not None else None}
    return activity
