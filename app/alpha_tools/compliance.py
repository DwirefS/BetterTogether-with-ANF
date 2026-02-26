def compliance_check(draft_text: str) -> str:
    """
    Cross-references SEC and FINRA regulatory frameworks against generated text.

    Args:
        draft_text: The analytical text drafted by the summarizing agent.

    Returns:
        Feedback on whether the text violates guidelines (e.g. guaranteeing returns).
    """
    import logging
    from .nim_client import NIMClient

    logger = logging.getLogger(__name__)

    prompt = f"""
    You are a FINRA and SEC Regulatory Compliance Officer.
    Review the following draft for any unauthorized speculation, guarantees of future performance, or implicit promises.
    Return 'COMPLIANCE REVIEW: PASSED.' if it is safe, otherwise return 'COMPLIANCE REVIEW: FAILED.' followed by specific FINRA/SEC rule violations and how to fix them.

    Draft:
    {draft_text}
    """

    try:
        nim = NIMClient()
        response = nim.chat_completion(
            [{"role": "user", "content": prompt}], temperature=0.1
        )
        return response
    except Exception as e:
        logger.error(f"Compliance check LLM call failed: {e}")
        return f"COMPLIANCE REVIEW ERROR: Failed to reach compliance verification NIM logic. {e}"
