"""
Cryptographic Surrogate Vault for Blind-Tokens.
Maintains bidirectional mappings between raw secrets and typed blind surrogates.
"""

import hmac
import hashlib
import re
import secrets
from typing import Dict, Optional, Any, List
from .models import TokenType, BlindedToken


class BlindTokenVault:
    """Secure in-memory vault for token surrogate blinding and unblinding."""

    SURROGATE_PATTERN = re.compile(r"\[BLIND_([A-Z_]+):([a-f0-9]{8})\]")

    def __init__(self, hmac_key: Optional[bytes] = None):
        self._key = hmac_key or secrets.token_bytes(32)
        # raw_value -> BlindedToken
        self._raw_to_token: Dict[str, BlindedToken] = {}
        # surrogate -> BlindedToken
        self._surrogate_to_token: Dict[str, BlindedToken] = {}

    def get_or_create_surrogate(self, raw_value: str, token_type: TokenType) -> str:
        """Derive or fetch deterministic surrogate for a given secret."""
        if raw_value in self._raw_to_token:
            token = self._raw_to_token[raw_value]
            token.usage_count += 1
            return token.blind_surrogate

        # Generate HMAC-based surrogate token
        digest = hmac.new(self._key, raw_value.encode("utf-8"), hashlib.sha256).hexdigest()[:8]
        surrogate = f"[BLIND_{token_type.value}:{digest}]"

        token = BlindedToken(
            raw_value=raw_value,
            blind_surrogate=surrogate,
            token_type=token_type,
            usage_count=1
        )

        self._raw_to_token[raw_value] = token
        self._surrogate_to_token[surrogate] = token
        return surrogate

    def unblind(self, surrogate: str) -> Optional[str]:
        """Lookup raw secret by surrogate."""
        token = self._surrogate_to_token.get(surrogate)
        return token.raw_value if token else None

    def unblind_text(self, text: str) -> str:
        """Replace all surrogate tokens in a text block with raw secrets."""
        if not text or "[BLIND_" not in text:
            return text

        def _replace(match):
            surrogate = match.group(0)
            token = self._surrogate_to_token.get(surrogate)
            return token.raw_value if token else surrogate

        return self.SURROGATE_PATTERN.sub(_replace, text)

    def unblind_payload(self, payload: Any) -> Any:
        """Recursively unblind strings inside dicts, lists, and primitives."""
        if isinstance(payload, str):
            return self.unblind_text(payload)
        elif isinstance(payload, dict):
            return {k: self.unblind_payload(v) for k, v in payload.items()}
        elif isinstance(payload, list):
            return [self.unblind_payload(elem) for elem in payload]
        return payload

    def count_registered(self) -> int:
        return len(self._raw_to_token)

    def get_all_raw_tokens(self) -> List[str]:
        return list(self._raw_to_token.keys())

    def clear(self) -> None:
        self._raw_to_token.clear()
        self._surrogate_to_token.clear()
