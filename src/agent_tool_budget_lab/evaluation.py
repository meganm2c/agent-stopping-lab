"""Deterministic, post-run scoring; never imported into model context."""

def metrics(result, scenario):
    retrieved = set(result.evidence_ids_retrieved)
    required = set(scenario.required_evidence)
    relevant = required | set(scenario.optional_supporting_evidence)
    seen, sufficient_at, executed = set(), None, 0
    keys, redundant_indices, outside_indices = [], set(), []
    for call in result.tool_calls:
        if not call.executed:
            continue
        executed += 1
        key = (call.tool_name, call.arguments["component"])
        if key in keys or sufficient_at is not None:
            redundant_indices.add(call.tool_index)
        keys.append(key)
        if "evidence_id" in call.output:
            seen.add(call.output["evidence_id"])
            if call.output["evidence_id"] not in relevant:
                outside_indices.append(call.tool_index)
                redundant_indices.add(call.tool_index)
        if sufficient_at is None and required <= seen:
            sufficient_at = executed
    diagnosis = result.final_diagnosis
    return {
        "correct": bool(diagnosis and scenario.accepts_root_cause(diagnosis.predicted_root_cause)),
        "diagnosis_correct": bool(diagnosis and scenario.accepts_root_cause(diagnosis.predicted_root_cause)),
        "evidence_sufficient": required <= retrieved,
        "required_evidence_count": len(required),
        "required_evidence_retrieved_count": len(required & retrieved),
        "required_evidence_retrieved": sorted(required & retrieved),
        "missing_required_evidence": sorted(required - retrieved),
        "evidence_completeness": len(required & retrieved) / len(required),
        "premature_stop": not required <= retrieved,
        "outside_required_supporting_evidence": sorted(retrieved - relevant),
        "outside_required_supporting_calls": len(outside_indices),
        "redundant_calls": len(redundant_indices),
        "excess_calls": executed - sufficient_at if sufficient_at is not None else 0,
        "repeated_calls": len(keys) - len(set(keys)),
        "unobserved_citations": sorted(set(diagnosis.evidence_used) - retrieved) if diagnosis else [],
    }


def total_tokens(run):
    usage = run["usage"]
    if "total_token_count" in usage:
        return usage["total_token_count"]
    if "input_token_count" in usage and "output_token_count" in usage:
        return usage["input_token_count"] + usage["output_token_count"]
    return None


