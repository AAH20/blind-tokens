"""
Data models and token definitions for Blind-Tokens.
Zero-Knowledge Context Sanitizer & Token Blinded Encryption for Reasoning Traces.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import time


class TokenType(str, Enum):
    API_KEY = "API_KEY"
    EMAIL = "EMAIL"
    CREDIT_CARD = "CREDIT_CARD"
    SSN = "SSN"
    IP_ADDRESS = "IP_ADDRESS"
    BEARER_TOKEN = "BEARER_TOKEN"
    PRIVATE_KEY = "PRIVATE_KEY"
    CUSTOM_SECRET = "CUSTOM_SECRET"


@dataclass
class BlindedToken:
    raw_value: str
    blind_surrogate: str
    token_type: TokenType
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0


@dataclass
class SanitizationResult:
    original_length: int
    sanitized_length: int
    sanitized_text: str
    tokens_blinded: int
    blinded_types: Dict[str, int] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class TraceAuditResult:
    is_clean: bool
    leaked_tokens_count: int
    leaked_tokens: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    audit_duration_ms: float = 0.0
