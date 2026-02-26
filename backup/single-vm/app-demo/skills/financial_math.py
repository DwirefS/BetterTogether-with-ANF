"""
AlphaAgent — Skill: Financial Math Calculator
Deterministic financial calculations to prevent LLM hallucination on math.
"""

from __future__ import annotations

from typing import Dict, Optional


def calculate_yoy_variance(current: float, prior: float) -> Dict[str, str]:
    """
    Calculate Year-over-Year (YoY) percentage variance.

    Args:
        current: Current period value
        prior: Prior period value

    Returns:
        Dict with formula, result, and interpretation
    """
    if prior == 0:
        return {
            "formula": "((current - prior) / prior) × 100",
            "inputs": f"current={current}, prior={prior}",
            "result": "Error: Division by zero (prior period value is 0)",
            "interpretation": "Cannot calculate YoY variance with zero baseline.",
        }

    variance = ((current - prior) / prior) * 100
    direction = "increase" if variance > 0 else "decrease" if variance < 0 else "no change"

    return {
        "formula": "((current - prior) / prior) × 100",
        "inputs": f"current={current}, prior={prior}",
        "result": f"{variance:+.2f}%",
        "absolute_change": f"{current - prior:+.2f}",
        "direction": direction,
        "interpretation": f"A {abs(variance):.2f}% {direction} from {prior} to {current}.",
    }


def calculate_margin(numerator: float, denominator: float, margin_type: str = "EBITDA") -> Dict[str, str]:
    """
    Calculate a financial margin (EBITDA, operating, net, etc.).

    Args:
        numerator: The margin numerator (e.g., EBITDA)
        denominator: The margin denominator (e.g., Revenue)
        margin_type: Label for the margin type

    Returns:
        Dict with formula, result, and interpretation
    """
    if denominator == 0:
        return {
            "formula": f"{margin_type} / Revenue × 100",
            "result": "Error: Division by zero.",
        }

    margin = (numerator / denominator) * 100
    health = "healthy" if margin > 20 else "moderate" if margin > 10 else "concerning"

    return {
        "formula": f"{margin_type} / Revenue × 100",
        "inputs": f"{margin_type}={numerator}, Revenue={denominator}",
        "result": f"{margin:.1f}%",
        "assessment": f"{margin_type} margin of {margin:.1f}% is considered {health} for capital markets.",
    }


def calculate_leverage(net_debt: float, ebitda: float) -> Dict[str, str]:
    """
    Calculate Net Debt-to-EBITDA leverage ratio.

    Args:
        net_debt: Net debt value
        ebitda: EBITDA value

    Returns:
        Dict with formula, result, and risk assessment
    """
    if ebitda == 0:
        return {
            "formula": "Net Debt / EBITDA",
            "result": "Error: Division by zero (EBITDA is 0).",
        }

    ratio = net_debt / ebitda
    risk = "low" if ratio < 1.5 else "moderate" if ratio < 2.5 else "elevated" if ratio < 3.5 else "high"

    return {
        "formula": "Net Debt / EBITDA",
        "inputs": f"Net Debt={net_debt}, EBITDA={ebitda}",
        "result": f"{ratio:.2f}x",
        "risk_level": risk,
        "interpretation": f"Leverage of {ratio:.2f}x is {risk}. Industry threshold is typically 2.5x.",
    }


def check_policy_threshold(
    metric_name: str,
    value: float,
    threshold: float,
    direction: str = "above",
) -> Dict[str, str]:
    """
    Check if a financial metric exceeds a policy threshold.

    Args:
        metric_name: Name of the metric being checked
        value: Actual value
        threshold: Policy threshold
        direction: "above" means violation if value > threshold

    Returns:
        Dict with status (PASS/FLAG) and details
    """
    if direction == "above":
        violated = value > threshold
    else:
        violated = value < threshold

    return {
        "metric": metric_name,
        "value": f"{value:.2f}",
        "threshold": f"{threshold:.2f}",
        "direction": f"must not be {direction} threshold",
        "status": "FLAG" if violated else "PASS",
        "detail": (
            f"⚠️ POLICY VIOLATION: {metric_name} ({value:.2f}) exceeds threshold ({threshold:.2f}). "
            f"Requires management review per Trade Surveillance Policy §4."
            if violated
            else f"✅ PASS: {metric_name} ({value:.2f}) is within policy limits ({threshold:.2f})."
        ),
    }
