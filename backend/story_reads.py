"""SQL-only read projections of committed internal Story records (not file integrity checks)."""

import json
import sqlite3

from backend.domain import OwnerResponseV1, make_operation_id, sha256_digest
from backend.review_store import REVIEW_ACTION_LIMIT
from backend.story_start import GRAPH_ID


def _rows(db: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    cursor = db.execute(sql, params)
    return [dict(zip((column[0] for column in cursor.description), row)) for row in cursor.fetchall()]


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


def story_projection(db: sqlite3.Connection, execution_id: str) -> dict | None:
    """Read only canonical business metadata; no checkpoint, graph or artifact-body access."""
    executions = _rows(db, "SELECT project_id,input_message,shot_ids,client_key,start_digest,"
                       "graph_id,graph_version,graph_digest FROM executions "
                       "WHERE execution_id=? AND graph_id=?", (execution_id, GRAPH_ID))
    if not executions:
        return None
    row = executions[0]
    project_id = row["project_id"]
    overview = _overview(db, execution_id)
    outcome, binding = overview["outcome"], overview["binding"]
    artifacts = _rows(db, "SELECT a.artifact_id,a.operation_id,a.digest,a.uri,a.schema_id,a.schema_version,"
                      "a.produced_by_stage,o.expected_revision,o.artifact_id AS committed_artifact_id "
                      "FROM artifacts a LEFT JOIN story_operations o ON o.operation_id=a.operation_id "
                      "AND o.execution_id=a.execution_id WHERE a.execution_id=? ORDER BY a.rowid", (execution_id,))
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
                if (not outcome or outcome["outcome"] != "completed"
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
            "start_digest": row["start_digest"]},
            "graph": {"id": row["graph_id"], "version": row["graph_version"], "digest": row["graph_digest"]},
            "work": overview["work"], "stories": stories, "reviews": reviews, "review": overview["review"],
            "remaining_actions": remaining, "allowed_actions": allowed}


def recent_story_executions(db: sqlite3.Connection, limit: int) -> list[dict]:
    ids = db.execute("SELECT execution_id,project_id,input_message FROM executions WHERE graph_id=? "
                     "ORDER BY rowid DESC LIMIT ?", (GRAPH_ID, limit)).fetchall()
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
