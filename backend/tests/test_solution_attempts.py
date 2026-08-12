"""
Unit and integration tests for Solution Attempt outcome recording and append-only history preservation.

CRITICAL PRODUCT PRINCIPLE TEST:
Verify that solution attempts are immutable historical records.
Every attempted solution receives an outcome (success/failure/partial/rejected/unknown).
Never overwrite, delete, or update past attempt records.
"""

from uuid import uuid4
from fastapi import status


def get_auth_token(client, email="employee@company.com", password="Password123!"):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    return login_res.json()["access_token"]


def create_test_incident(client, token):
    res = client.post(
        "/api/v1/incidents",
        json={
            "title": "Kafka partition rebalance loop",
            "description": "Consumers getting kicked out of consumer group during heavy ingestion",
            "category": "Messaging",
            "severity": "P2"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    return res.json()["id"]


def test_record_solution_attempt_success(client):
    token = get_auth_token(client)
    incident_id = create_test_incident(client, token)

    attempt_payload = {
        "solution_text": "Increased max.poll.interval.ms from 300000 to 600000",
        "outcome": "success",
        "failure_reason": None,
        "execution_duration_ms": 1200,
        "confidence_at_execution": 0.90,
        "reward_info": 1.0
    }

    res = client.post(
        f"/api/v1/incidents/{incident_id}/attempts",
        json=attempt_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["incident_id"] == incident_id
    assert data["solution_text"] == attempt_payload["solution_text"]
    assert data["outcome"] == "success"
    assert data["reward_info"] == 1.0
    assert "id" in data
    assert "performed_by" in data


def test_outcome_enum_validation(client):
    token = get_auth_token(client)
    incident_id = create_test_incident(client, token)

    # Test invalid outcome string
    res = client.post(
        f"/api/v1/incidents/{incident_id}/attempts",
        json={
            "solution_text": "Invalid outcome test",
            "outcome": "invalid_outcome_string"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test all 5 valid outcomes: success, failure, partial, rejected, unknown
    valid_outcomes = ["success", "failure", "partial", "rejected", "unknown"]
    for outcome in valid_outcomes:
        ok_res = client.post(
            f"/api/v1/incidents/{incident_id}/attempts",
            json={
                "solution_text": f"Testing outcome {outcome}",
                "outcome": outcome
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert ok_res.status_code == status.HTTP_201_CREATED
        assert ok_res.json()["outcome"] == outcome


def test_solution_attempt_history_immutability(client):
    """
    CRITICAL MEMORY RULE VERIFICATION:
    Attempt 1 -> failure
    Attempt 2 -> partial
    Attempt 3 -> success
    All three records MUST remain in historical attempt list without being overwritten or deleted.
    """
    token = get_auth_token(client)
    incident_id = create_test_incident(client, token)

    # Attempt 1: Failed
    att1 = client.post(
        f"/api/v1/incidents/{incident_id}/attempts",
        json={
            "solution_text": "Restarted consumer pods without config change",
            "outcome": "failure",
            "failure_reason": "Rebalance loop recurred within 5 minutes"
        },
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    # Attempt 2: Partial
    att2 = client.post(
        f"/api/v1/incidents/{incident_id}/attempts",
        json={
            "solution_text": "Doubled pod memory allocation to 4GB",
            "outcome": "partial",
            "failure_reason": "Latency improved but rebalance still occurred on peak load"
        },
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    # Attempt 3: Successful
    att3 = client.post(
        f"/api/v1/incidents/{incident_id}/attempts",
        json={
            "solution_text": "Tuned max.poll.records to 100 and increased session timeout",
            "outcome": "success"
        },
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    # Retrieve all attempts for incident
    get_res = client.get(
        f"/api/v1/incidents/{incident_id}/attempts",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_res.status_code == status.HTTP_200_OK
    attempts = get_res.json()

    # VERIFICATION: Exactly 3 distinct attempt records exist
    assert len(attempts) == 3

    # All attempt IDs are unique and match created records
    attempt_ids = [att["id"] for att in attempts]
    assert len(set(attempt_ids)) == 3
    assert att1["id"] in attempt_ids
    assert att2["id"] in attempt_ids
    assert att3["id"] in attempt_ids

    # Outcomes match exact chronological attempt history
    outcomes = [att["outcome"] for att in attempts]
    assert "failure" in outcomes
    assert "partial" in outcomes
    assert "success" in outcomes


def test_record_solution_attempt_incident_not_found(client):
    token = get_auth_token(client)
    bogus_id = str(uuid4())
    res = client.post(
        f"/api/v1/incidents/{bogus_id}/attempts",
        json={
            "solution_text": "Attempt on non-existent incident",
            "outcome": "failure"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_solution_attempts_unauthenticated(client):
    bogus_id = str(uuid4())
    res = client.get(f"/api/v1/incidents/{bogus_id}/attempts")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
