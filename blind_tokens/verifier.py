"""
Reasoning Trace Verifier & Leakage Auditor for Blind-Tokens.
Verifies zero raw token leakage in extended thinking and reasoning traces.
"""

import time
from typing import List
from .models import TraceAuditResult
from .vault import BlindTokenVault


class ReasoningTraceVerifier:
    """Audits agent thinking traces and context logs for leakage of registered raw secrets."""

    def __init__(self, vault: BlindTokenVault):
        self.vault = vault

    def audit_trace(self, reasoning_trace: str) -> TraceAuditResult:
        """Scan a reasoning / extended thinking trace to ensure zero raw secrets appear."""
        start_time = time.time()
        registered_secrets = self.vault.get_all_raw_tokens()
        leaked_tokens: List[str] = []

        for secret in registered_secrets:
            if secret in reasoning_trace:
                leaked_tokens.append(secret)

        duration_ms = (time.time() - start_time) * 1000.0
        is_clean = (len(leaked_tokens) == 0)
        risk_score = 0.0 if is_clean else min(1.0, len(leaked_tokens) * 0.5)

        return TraceAuditResult(
            is_clean=is_clean,
            leaked_tokens_count=len(leaked_tokens),
            leaked_tokens=leaked_tokens,
            risk_score=risk_score,
            audit_duration_ms=duration_ms
        )
