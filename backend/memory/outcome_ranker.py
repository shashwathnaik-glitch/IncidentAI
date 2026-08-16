"""
Outcome-Aware Memory Ranker for IncidentMind (v1.1)

Ranks candidate solutions using historical evidence stored in CockroachDB:
Score = Semantic Similarity + Historical Success Evidence - Failure Penalty
"""

import logging

logger = logging.getLogger("outcome_ranker")

# Weight factors for score formula
WEIGHT_SIMILARITY = 1.0
WEIGHT_SUCCESS = 0.15
WEIGHT_PARTIAL = 0.05
WEIGHT_FAILURE_PENALTY = 0.20
WEIGHT_REJECTED_PENALTY = 0.10

def evaluate_and_rank_candidates(similar_incidents, query_context=""):
    """
    Takes a list of similar incidents returned by CockroachDB vector search
    (including their associated solution_attempts) and ranks candidate solutions
    based on historical evidence outcomes.

    :param similar_incidents: list of dicts with 'similarity', 'solution_attempts', etc.
    :param query_context: string representation of current incident
    :returns: dict with 'best_candidate', 'ranked_solutions', and 'composite_confidence'
    """
    solution_candidates = {}

    for inc in similar_incidents:
        similarity = float(inc.get("similarity", 0.0))
        attempts = inc.get("solution_attempts", [])

        for att in attempts:
            solution_text = att.get("solution_text")
            outcome = att.get("outcome", "unknown").lower()
            
            if not solution_text:
                continue

            if solution_text not in solution_candidates:
                solution_candidates[solution_text] = {
                    "solution_text": solution_text,
                    "base_similarity": similarity,
                    "success_count": 0,
                    "failure_count": 0,
                    "partial_count": 0,
                    "rejected_count": 0,
                    "unknown_count": 0,
                    "total_attempts": 0,
                    "reasons": []
                }

            cand = solution_candidates[solution_text]
            cand["total_attempts"] += 1

            if att.get("failure_reason"):
                cand["reasons"].append(att["failure_reason"])

            if outcome == "success":
                cand["success_count"] += 1
            elif outcome == "failure":
                cand["failure_count"] += 1
            elif outcome == "partial":
                cand["partial_count"] += 1
            elif outcome == "rejected":
                cand["rejected_count"] += 1
            else:
                cand["unknown_count"] += 1

    # Calculate composite score for each candidate solution
    ranked_list = []
    for solution_text, cand in solution_candidates.items():
        base_sim = cand["base_similarity"]
        
        # Evidence adjustments
        success_bonus = cand["success_count"] * WEIGHT_SUCCESS
        partial_bonus = cand["partial_count"] * WEIGHT_PARTIAL
        failure_penalty = cand["failure_count"] * WEIGHT_FAILURE_PENALTY
        rejected_penalty = cand["rejected_count"] * WEIGHT_REJECTED_PENALTY

        final_score = (base_sim * WEIGHT_SIMILARITY) + success_bonus + partial_bonus - failure_penalty - rejected_penalty
        final_score = max(0.0, min(1.0, final_score)) # Clamp between 0.0 and 1.0

        # Confidence percentage calculation
        confidence_percent = int(round(final_score * 100))

        ranked_list.append({
            "solution_text": solution_text,
            "composite_score": round(final_score, 4),
            "confidence_percent": confidence_percent,
            "base_similarity": round(base_sim, 4),
            "evidence_breakdown": {
                "success_count": cand["success_count"],
                "failure_count": cand["failure_count"],
                "partial_count": cand["partial_count"],
                "rejected_count": cand["rejected_count"],
                "unknown_count": cand["unknown_count"],
                "total_attempts": cand["total_attempts"]
            },
            "failure_reasons": list(set(cand["reasons"]))
        })

    # Sort descending by composite score
    ranked_list.sort(key=lambda x: x["composite_score"], reverse=True)

    best_candidate = ranked_list[0] if ranked_list else None

    return {
        "best_candidate": best_candidate,
        "ranked_solutions": ranked_list,
        "composite_confidence": best_candidate["confidence_percent"] if best_candidate else 75
    }
