import db
import app
from schemas import AssessmentResult, RubricCriterion


def _make_assessment(user_id: str) -> AssessmentResult:
    return AssessmentResult(
        user_id=user_id,
        domain="math",
        item_id="diagnostic-1",
        bloom_level="K2",
        response="Answer",
        score=0.7,
        rubric_criteria=[RubricCriterion(id="logic", score=0.7)],
        model_version="test",
        prompt_version="p.v1",
        confidence=0.9,
        source="direct",
    )


def test_privacy_export_and_delete(temp_db):
    user_id = "alice"
    db.create_user(user_id, "alice@example.com", "hash")
    db.record_privacy_consent(user_id, True, "unit test")
    db.upsert_mastery(user_id, "math.algebra", 0.42)
    db.upsert_bloom_progress(user_id, "math", "K2")
    db.record_llm_metric(user_id, "model-x", "chat.v1", app.CHAT_PROMPT_VARIANT, 1200, 210, 180)
    db.log_learning_event(user_id, "math", "quiz", score=0.8, details={"skill": "math.algebra"})
    db.log_journey_update(user_id, "suggest_next_item", {"skill": "math.algebra", "reason": "Practice quadratic functions"})
    db.record_chat_ops(user_id, "math", "Question?", "Answer!", {}, [], [])
    db.upsert_learning_path_state(user_id, "math", {"levels": {"K1": 0.6}, "current_level": "K1", "history": []})
    db.log_learning_path_event(
        user_id,
        "math",
        "K1",
        "promote",
        reason="Test",
        reason_code="unit_test",
        confidence=0.9,
        evidence={"source": "unit"},
    )
    db.store_feedback(user_id, "answer-1", "up", "Great explanation", confidence=0.95)
    db._exec(
        "INSERT INTO xapi_statements(user_id, verb, object_id) VALUES (?,?,?)",
        (user_id, "verb", "obj"),
    )
    db.record_quiz_attempt(user_id, "math", "activity-1", 4, 5)
    db.save_assessment_result(_make_assessment(user_id))

    export_bundle = app.privacy_export(user_id)
    assert export_bundle["users"]
    assert export_bundle["mastery"]
    assert export_bundle["learning_events"]
    assert export_bundle["journey_log"]
    assert export_bundle["xapi_statements"]
    assert export_bundle["assessment_results"]
    assert export_bundle["bloom_progress"]
    assert export_bundle["bloom_progress_history"]
    assert export_bundle["llm_metrics"]
    assert export_bundle["learning_path_state"]
    assert export_bundle["learning_path_events"]
    assert export_bundle["answer_feedback"]
    assert export_bundle["user_consent"]

    deletion_result = app.privacy_delete(user_id)
    assert deletion_result["deleted"]["users"] == 1

    remaining = db.export_user_data(user_id)
    assert not any(
        remaining.get(key)
        for key in (
            "mastery",
            "learning_events",
            "journey_log",
            "xapi_statements",
            "assessment_results",
            "bloom_progress",
            "bloom_progress_history",
            "llm_metrics",
            "learning_path_state",
            "learning_path_events",
            "answer_feedback",
            "user_consent",
        )
    )
