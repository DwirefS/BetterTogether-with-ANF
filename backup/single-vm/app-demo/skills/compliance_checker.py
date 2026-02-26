"""
AlphaAgent — Skill: Compliance Checker
Cross-references financial analysis results against internal risk policies.
"""

from __future__ import annotations

from typing import Dict, List

from .financial_math import check_policy_threshold


# Internal policy thresholds (from Trade_Surveillance_Policy_2026.pdf)
POLICY_THRESHOLDS = {
    "capex_yoy_pct": {
        "threshold": 40.0,
        "direction": "above",
        "policy_ref": "Trade Surveillance Policy §4 — AI Agent Usage Policy",
        "description": "YoY CapEx changes exceeding 40% require management review and board notification.",
    },
    "leverage_ratio": {
        "threshold": 2.5,
        "direction": "above",
        "policy_ref": "Risk & Compliance Brief — Internal Policy Limit",
        "description": "Net Debt-to-EBITDA exceeding 2.5x triggers enhanced risk monitoring.",
    },
    "var_99_usd_m": {
        "threshold": 50.0,
        "direction": "above",
        "policy_ref": "Trade Surveillance Policy §3 — Alert Severity",
        "description": "99% 1-day VaR exceeding $50M requires escalation to CRO.",
    },
    "position_size_usd_m": {
        "threshold": 10.0,
        "direction": "above",
        "policy_ref": "Trade Surveillance Policy §4 — AI Agent Usage Policy",
        "description": "AI-recommended positions above $10M notional require human approval.",
    },
}


def run_compliance_check(
    metrics: Dict[str, float],
    ticker: str = "",
) -> Dict[str, any]:
    """
    Run compliance checks against all internal policy thresholds.

    Args:
        metrics: Dict of metric_name → value (e.g., {"capex_yoy_pct": 35.2, "leverage_ratio": 1.8})
        ticker: Company ticker for context

    Returns:
        Dict with overall status, individual findings, and recommendations
    """
    findings: List[Dict] = []
    flags = 0

    for metric_name, value in metrics.items():
        if metric_name in POLICY_THRESHOLDS:
            policy = POLICY_THRESHOLDS[metric_name]
            result = check_policy_threshold(
                metric_name=metric_name,
                value=value,
                threshold=policy["threshold"],
                direction=policy["direction"],
            )
            result["policy_ref"] = policy["policy_ref"]
            result["policy_description"] = policy["description"]
            findings.append(result)
            if result["status"] == "FLAG":
                flags += 1

    overall = "FLAG" if flags > 0 else "PASS"

    return {
        "ticker": ticker,
        "overall_status": overall,
        "total_checks": len(findings),
        "flags": flags,
        "passes": len(findings) - flags,
        "findings": findings,
        "recommendation": (
            f"⚠️ {flags} policy threshold(s) violated for {ticker or 'entity'}. "
            "Escalate to Chief Compliance Officer per Trade Surveillance Policy §6."
            if flags > 0
            else f"✅ All {len(findings)} compliance checks passed for {ticker or 'entity'}. "
            "No escalation required."
        ),
    }


def format_compliance_report(result: Dict) -> str:
    """Format compliance check results into a readable report."""
    lines = [
        f"## Compliance Assessment: {result.get('ticker', 'Entity')}",
        f"**Overall Status:** {result['overall_status']}",
        f"**Checks Run:** {result['total_checks']} | "
        f"**Passed:** {result['passes']} | **Flagged:** {result['flags']}",
        "",
    ]

    for f in result.get("findings", []):
        icon = "🚩" if f["status"] == "FLAG" else "✅"
        lines.append(f"{icon} **{f['metric']}**: {f['value']} (threshold: {f['threshold']})")
        lines.append(f"   Policy: {f.get('policy_ref', 'N/A')}")
        lines.append(f"   {f['detail']}")
        lines.append("")

    lines.append(f"**Recommendation:** {result['recommendation']}")
    return "\n".join(lines)
