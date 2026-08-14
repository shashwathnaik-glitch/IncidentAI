"""
Unit tests for Outcome-Aware Memory Ranker (backend/memory/outcome_ranker.py)
Verifies scoring logic, evidence weighting, and ranking calculations.
"""

import pytest
from backend.memory.outcome_ranker import evaluate_and_rank_candidates

def test_evaluate_and_rank_candidates_success_prioritization():
    """Verifies that solutions with historical successes are ranked above failed solutions."""
    similar_incidents = [
        {
            "id": "inc_001",
            "similarity": 0.90,
            "solution_attempts": [
                {
                    "solution_text": "Restart service worker pool",
                    "outcome": "failure",
                    "failure_reason": "Process hung on IO lock"
                }
            ]
        },
        {
            "id": "inc_002",
            "similarity": 0.85,
            "solution_attempts": [
                {
                    "solution_text": "Scale CockroachDB max_connections to 500",
                    "outcome": "success"
                },
                {
                    "solution_text": "Scale CockroachDB max_connections to 500",
                    "outcome": "success"
                }
            ]
        }
    ]

    result = evaluate_and_rank_candidates(similar_incidents)
    
    best = result["best_candidate"]
    assert best is not None
    assert best["solution_text"] == "Scale CockroachDB max_connections to 500"
    assert best["evidence_breakdown"]["success_count"] == 2
    
    ranked = result["ranked_solutions"]
    assert len(ranked) == 2
    # Verify candidate with success bonus ranks higher despite lower base similarity
    assert ranked[0]["solution_text"] == "Scale CockroachDB max_connections to 500"
    assert ranked[1]["solution_text"] == "Restart service worker pool"
    assert ranked[1]["evidence_breakdown"]["failure_count"] == 1

def test_evaluate_and_rank_empty_candidates():
    """Verifies ranker behavior when no similar incidents or attempts are returned."""
    result = evaluate_and_rank_candidates([])
    assert result["best_candidate"] is None
    assert result["ranked_solutions"] == []
    assert result["composite_confidence"] == 75
