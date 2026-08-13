# IncidentMind — AI Safety Audit
# Owner: AI / Intelligence layer
#
# Provides a structured audit of the AI layer for:
#   - Prompt injection vulnerabilities
#   - Secrets / PII leakage into prompts or outputs
#   - Hallucination (fabricated historical evidence)
#   - Outcome misclassification (unknown/rejected treated as success)
#   - Confidence dishonesty (high confidence without evidence)
#   - Unsafe recommendations (approval bypass)
#
# Audit findings are classified as: CRITICAL / HIGH / MEDIUM / LOW
# CRITICAL and HIGH findings must be fixed before final testing.
# MEDIUM and LOW are reported for awareness.
#
# Usage:
#   audit = SafetyAuditor()
#   findings = audit.run_full_audit(analysis_result, retrieval_result)
#   audit.print_report(findings)

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set

from backend.agents.recommendation import Recommendation
from backend.agents.safety_guard import (
    InjectionDetected,
    assert_outcome_not_misclassified,
    check_output_for_leakage,
    sanitise_input,
    validate_no_fabrication,
)
from backend.memory.retrieval import MemoryRetrievalResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Audit finding types
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class AuditFinding:
    """A single safety audit finding."""
    severity: Severity
    category: str
    description: str
    owner: str = "AI"  # Which team owns the fix: AI / Backend / Database / Frontend
    remediation: str = ""


@dataclass
class AuditReport:
    """Full audit report from a safety audit run."""
    findings: List[AuditFinding] = field(default_factory=list)
    passed: bool = True  # False if any CRITICAL or HIGH finding exists
    summary: str = ""

    def add(self, finding: AuditFinding) -> None:
        self.findings.append(finding)
        if finding.severity in (Severity.CRITICAL, Severity.HIGH):
            self.passed = False

    def critical_and_high(self) -> List[AuditFinding]:
        return [f for f in self.findings if f.severity in (Severity.CRITICAL, Severity.HIGH)]

    def by_severity(self, sev: Severity) -> List[AuditFinding]:
        return [f for f in self.findings if f.severity == sev]


# ---------------------------------------------------------------------------
# Safety Auditor
# ---------------------------------------------------------------------------

class SafetyAuditor:
    """
    Runs safety and hallucination audits on AI pipeline inputs and outputs.
    """

    # ------------------------------------------------------------------
    # Input audit: run BEFORE sending to Bedrock
    # ------------------------------------------------------------------

    def audit_input(
        self,
        title: str,
        description: str,
        logs: Optional[str] = None,
    ) -> AuditReport:
        """
        Audit incident input for prompt injection and sensitive data.

        Returns an AuditReport. If any CRITICAL/HIGH finding exists,
        the caller should reject the input or redact it before processing.
        """
        report = AuditReport()
        fields = {"title": title, "description": description}
        if logs:
            fields["logs"] = logs

        for field_name, text in fields.items():
            # Check for injection
            try:
                sanitise_input(text, raise_on_injection=True)
            except InjectionDetected as exc:
                report.add(AuditFinding(
                    severity=Severity.HIGH,
                    category="prompt-injection",
                    description=(
                        f"Potential prompt injection detected in incident {field_name}. "
                        f"Details: {exc}"
                    ),
                    owner="AI",
                    remediation=(
                        "Input has been sanitised (injection pattern redacted). "
                        "Log the raw input for security review."
                    ),
                ))

            # Check for secrets/PII in input
            leakage = check_output_for_leakage(text)
            for warning in leakage:
                report.add(AuditFinding(
                    severity=Severity.HIGH,
                    category="pii-secrets-in-input",
                    description=(
                        f"Potential sensitive data in incident {field_name}: {warning}"
                    ),
                    owner="AI",
                    remediation=(
                        "Mask sensitive patterns before forwarding to Bedrock. "
                        "Do not log the raw field value."
                    ),
                ))

        report.summary = (
            f"Input audit complete: {len(report.findings)} finding(s) "
            f"({'FAILED' if not report.passed else 'PASSED'})."
        )
        return report

    # ------------------------------------------------------------------
    # Output audit: run AFTER Bedrock response, BEFORE returning to Backend
    # ------------------------------------------------------------------

    def audit_output(
        self,
        recommendation: Recommendation,
        retrieval_result: MemoryRetrievalResult,
    ) -> AuditReport:
        """
        Audit AI recommendation output for:
          - PII/secrets leakage
          - Hallucination (fabricated incident IDs)
          - Outcome misclassification
          - Dishonest confidence
          - Approval bypass
        """
        report = AuditReport()

        # Collect known retrieved IDs
        retrieved_ids: Set[str] = {
            ev.incident_id for ev in retrieval_result.historical_evidence
        } if retrieval_result.historical_evidence else set()

        # 1. PII/secrets leakage in recommendation output
        full_output = (
            recommendation.recommended_solution + " "
            + recommendation.reasoning_summary
        )
        leakage_warnings = check_output_for_leakage(full_output)
        for warning in leakage_warnings:
            report.add(AuditFinding(
                severity=Severity.CRITICAL,
                category="output-leakage",
                description=f"Sensitive data pattern in AI recommendation output: {warning}",
                owner="AI",
                remediation="Strip sensitive patterns from all AI outputs before returning to client.",
            ))

        # 2. Hallucination check — detect invented incident IDs in output
        fabrication_issues = validate_no_fabrication(
            recommendation_text=recommendation.recommended_solution + " " + recommendation.reasoning_summary,
            retrieved_incident_ids=retrieved_ids,
            retrieved_solution_texts=set(),
        )
        for issue in fabrication_issues:
            report.add(AuditFinding(
                severity=Severity.CRITICAL,
                category="hallucination",
                description=issue,
                owner="AI",
                remediation=(
                    "Verify the recommendation only references incidents retrieved from memory. "
                    "The LLM must not invent incident IDs or fabricate historical data."
                ),
            ))

        # 3. Outcome misclassification in evidence items
        for ev in recommendation.evidence:
            issues = assert_outcome_not_misclassified(ev.outcome, ev.note)
            for issue in issues:
                report.add(AuditFinding(
                    severity=Severity.CRITICAL,
                    category="outcome-misclassification",
                    description=issue,
                    owner="AI",
                    remediation=(
                        "Review _outcome_note() in recommendation.py. "
                        "Ensure UNKNOWN and REJECTED outcomes are never described as success."
                    ),
                ))

        # 4. Confidence honesty check
        if recommendation.confidence_score > 0.8 and not retrieval_result.historical_evidence:
            report.add(AuditFinding(
                severity=Severity.HIGH,
                category="confidence-dishonesty",
                description=(
                    f"High confidence ({recommendation.confidence_score:.0%}) reported "
                    "despite zero historical evidence. Confidence must be grounded in evidence."
                ),
                owner="AI",
                remediation=(
                    "Verify _compute_confidence() applies the cold_start_cap correctly. "
                    "Cold start must cap confidence at confidence_cold_start_cap."
                ),
            ))

        if (
            recommendation.confidence_score > 0.7
            and retrieval_result.historical_evidence
            and any(
                ev.success_count == 0
                for ev in retrieval_result.historical_evidence
            )
        ):
            report.add(AuditFinding(
                severity=Severity.MEDIUM,
                category="confidence-calibration",
                description=(
                    f"Confidence ({recommendation.confidence_score:.0%}) may be too high "
                    "given no matching incidents have any success history."
                ),
                owner="AI",
                remediation="Review confidence computation — check success_ratio calculation.",
            ))

        # 5. Approval bypass check
        if (
            not recommendation.approval_required
            and recommendation.confidence_score < 0.55
        ):
            report.add(AuditFinding(
                severity=Severity.CRITICAL,
                category="approval-bypass",
                description=(
                    f"approval_required=False despite confidence={recommendation.confidence_score:.0%} "
                    "(below threshold). Low-confidence recommendations MUST require approval."
                ),
                owner="AI",
                remediation=(
                    "Verify RecommendationEngine.generate() approval logic. "
                    "approval_required must be True when confidence < confidence_approval_threshold."
                ),
            ))

        if (
            not recommendation.approval_required
            and retrieval_result.cold_start
        ):
            report.add(AuditFinding(
                severity=Severity.CRITICAL,
                category="approval-bypass",
                description=(
                    "approval_required=False on cold start. "
                    "Cold start recommendations MUST always require approval."
                ),
                owner="AI",
                remediation="Force approval_required=True whenever cold_start=True.",
            ))

        report.summary = (
            f"Output audit complete: {len(report.findings)} finding(s) "
            f"({'FAILED' if not report.passed else 'PASSED'})."
        )
        return report

    # ------------------------------------------------------------------
    # Combined report printer
    # ------------------------------------------------------------------

    @staticmethod
    def print_report(report: AuditReport) -> None:
        """Print a formatted safety audit report to the logger."""
        logger.info("=" * 60)
        logger.info("SAFETY AUDIT REPORT — %s", "PASSED" if report.passed else "FAILED")
        logger.info("=" * 60)
        logger.info(report.summary)

        if not report.findings:
            logger.info("No findings. Audit passed.")
            return

        for sev in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            sevfindings = report.by_severity(sev)
            if sevfindings:
                logger.info("\n[%s] %d finding(s):", sev.value, len(sevfindings))
                for finding in sevfindings:
                    logger.info(
                        "  Category: %s | Owner: %s\n  %s\n  Remediation: %s",
                        finding.category, finding.owner,
                        finding.description, finding.remediation,
                    )

        if not report.passed:
            logger.error(
                "%d CRITICAL/HIGH finding(s) must be resolved before production use.",
                len(report.critical_and_high()),
            )
        logger.info("=" * 60)
