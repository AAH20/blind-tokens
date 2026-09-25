"""
Tool Egress Adapter & Boundary Gateway for Blind-Tokens.
Unblinds parameters right before execution at the local tool boundary,
and re-blinds downstream responses before returning into agent context.
"""

from typing import Dict, Any, Callable
from .vault import BlindTokenVault
from .sanitizer import ContextSanitizer


class ToolEgressAdapter:
    """Safely bridges blinded agent calls to unblinded local MCP servers/tools."""

    def __init__(self, vault: BlindTokenVault, sanitizer: ContextSanitizer):
        self.vault = vault
        self.sanitizer = sanitizer

    def execute_tool_call(
        self,
        tool_name: str,
        blinded_arguments: Dict[str, Any],
        tool_executor: Callable[[Dict[str, Any]], Any]
    ) -> Dict[str, Any]:
        """
        1. Unblind inbound parameters at the wire boundary
        2. Execute tool locally with raw credentials
        3. Re-blind output payload before returning to the LLM context
        """
        # Step 1: Unblind arguments
        unblinded_args = self.vault.unblind_payload(blinded_arguments)

        # Step 2: Execute tool locally
        raw_result = tool_executor(unblinded_args)

        # Step 3: Re-blind result to prevent secrets echoing back into LLM memory
        if isinstance(raw_result, str):
            sanitized_res = self.sanitizer.sanitize_text(raw_result).sanitized_text
        elif isinstance(raw_result, dict):
            # Convert string values in dict
            def _blind_walk(obj):
                if isinstance(obj, str):
                    return self.sanitizer.sanitize_text(obj).sanitized_text
                elif isinstance(obj, dict):
                    return {k: _blind_walk(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [_blind_walk(x) for x in obj]
                return obj
            sanitized_res = _blind_walk(raw_result)
        else:
            sanitized_res = raw_result

        return {
            "tool": tool_name,
            "blinded_result": sanitized_res,
            "executed_cleanly": True
        }
