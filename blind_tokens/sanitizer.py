"""
High-Speed Ingress Context Sanitizer for Blind-Tokens.
Scans prompts, tool outputs, and context traces, replacing sensitive tokens with typed blind surrogates.
"""

import re
import time
from typing import Dict, List, Any, Tuple
from .models import TokenType, SanitizationResult
from .vault import BlindTokenVault


class ContextSanitizer:
    """Detects and replaces secrets with cryptographically blinded tokens."""

    PATTERNS: List[Tuple[TokenType, re.Pattern]] = [
        # API Keys & Secrets
        (TokenType.API_KEY, re.compile(r"\b(?:sk-[a-zA-Z0-9_\-]{20,}|ghp_[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16})\b")),
        (TokenType.BEARER_TOKEN, re.compile(r"\b(?:Bearer\s+)([a-zA-Z0-9\-_]{24,}\.[a-zA-Z0-9\-_]{24,}\.[a-zA-Z0-9\-_]{16,})\b")),
        # SSN
        (TokenType.SSN, re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
        # Credit Cards (15-16 digits with dashes or spaces)
        (TokenType.CREDIT_CARD, re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),
        # Email Addresses
        (TokenType.EMAIL, re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")),
        # IPv4 Addresses
        (TokenType.IP_ADDRESS, re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b")),
    ]

    def __init__(self, vault: BlindTokenVault):
        self.vault = vault

    def sanitize_text(self, text: str) -> SanitizationResult:
        """Sanitize plain text, replacing all recognized sensitive entities."""
        start_time = time.time()
        orig_len = len(text)
        sanitized = text
        blinded_types: Dict[str, int] = {}
        total_blinded = 0

        for token_type, pattern in self.PATTERNS:
            matches = list(pattern.finditer(sanitized))
            if not matches:
                continue

            # Process matches in reverse order to preserve string offsets
            for match in reversed(matches):
                # If bearer token capture group exists
                if token_type == TokenType.BEARER_TOKEN and len(match.groups()) > 0:
                    raw_val = match.group(1)
                    surrogate = self.vault.get_or_create_surrogate(raw_val, token_type)
                    start, end = match.span(1)
                    sanitized = sanitized[:start] + surrogate + sanitized[end:]
                else:
                    raw_val = match.group(0)
                    surrogate = self.vault.get_or_create_surrogate(raw_val, token_type)
                    start, end = match.span(0)
                    sanitized = sanitized[:start] + surrogate + sanitized[end:]

                blinded_types[token_type.value] = blinded_types.get(token_type.value, 0) + 1
                total_blinded += 1

        duration_ms = (time.time() - start_time) * 1000.0

        return SanitizationResult(
            original_length=orig_len,
            sanitized_length=len(sanitized),
            sanitized_text=sanitized,
            tokens_blinded=total_blinded,
            blinded_types=blinded_types,
            duration_ms=duration_ms
        )

    def sanitize_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitize OpenAI/Anthropic format message dictionaries."""
        sanitized_messages = []
        for msg in messages:
            msg_copy = msg.copy()
            content = msg.get("content")
            if isinstance(content, str):
                msg_copy["content"] = self.sanitize_text(content).sanitized_text
            elif isinstance(content, list):
                new_blocks = []
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text":
                        b_copy = b.copy()
                        b_copy["text"] = self.sanitize_text(b["text"]).sanitized_text
                        new_blocks.append(b_copy)
                    else:
                        new_blocks.append(b)
                msg_copy["content"] = new_blocks
            sanitized_messages.append(msg_copy)
        return sanitized_messages
