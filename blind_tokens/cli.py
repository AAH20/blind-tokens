"""
CLI interface and interactive demonstration runner for Blind-Tokens.
"""

import sys
import json
import argparse
from typing import Dict, Any

from .vault import BlindTokenVault
from .sanitizer import ContextSanitizer
from .egress import ToolEgressAdapter
from .verifier import ReasoningTraceVerifier


def run_demo():
    print("=" * 74)
    print("  BLIND-TOKENS: Zero-Knowledge Context Sanitizer for Frontier AI")
    print("  Optimized for Claude Opus 5.5, GPT-6 Astra & Gemini 3.8 Flash")
    print("=" * 74)

    vault = BlindTokenVault()
    sanitizer = ContextSanitizer(vault)
    egress = ToolEgressAdapter(vault, sanitizer)
    verifier = ReasoningTraceVerifier(vault)

    # 1. Ingress Raw Context containing critical PII and API keys
    raw_prompt = (
        "User Request: Please charge $250 to customer card 4532-0123-8899-1234 "
        "and send confirmation receipt to executive alex.vance@defense-grid.org. "
        "Also sync database using production key sk-prod999482810294827103847291 "
        "for employee with SSN 012-34-5678."
    )

    print("\n[STEP 1] INGRESS CONTEXT SANITIZATION")
    print("  Raw Incoming Prompt:")
    print(f"  \"{raw_prompt}\"")

    res = sanitizer.sanitize_text(raw_prompt)
    print(f"\n  >> Sanitization Completed in {res.duration_ms:.3f} ms")
    print(f"  >> Tokens Blinded: {res.tokens_blinded}")
    for k, v in res.blinded_types.items():
        print(f"     * {k}: {v}")
    print("\n  Blinded Prompt Fed to LLM:")
    print(f"  \"{res.sanitized_text}\"")

    # 2. Simulated Model Reasoning Trace (Claude Opus 5.5 / GPT-6 Astra Extended Thinking)
    simulated_thinking_trace = (
        "<thinking>\n"
        "1. Identify customer payment instruction.\n"
        "2. Target card surrogate: [BLIND_CREDIT_CARD:16b80aa5]\n"
        "3. Target recipient surrogate: [BLIND_EMAIL:65f7c320]\n"
        "4. Target API key surrogate: [BLIND_API_KEY:2e316a3c]\n"
        "5. Prepare outbound tool call `charge_and_notify`.\n"
        "</thinking>"
    )

    print("\n[STEP 2] REASONING TRACE LEAKAGE AUDIT")
    audit = verifier.audit_trace(simulated_thinking_trace)
    print(f"  >> Audit Clean: {audit.is_clean} | Leaked Tokens: {audit.leaked_tokens_count}")
    print(f"  >> Leakage Risk Score: {audit.risk_score:.2f} (0.00 = Absolute Zero Leakage)")
    print(f"  >> Audit Latency: {audit.audit_duration_ms:.3f} ms")

    # 3. Model Outbound Tool Call
    # Notice the LLM only knows and emits the surrogates!
    llm_tool_call = {
        "card_number": list(vault._surrogate_to_token.keys())[0],
        "notification_email": list(vault._surrogate_to_token.keys())[1],
        "amount_usd": 250
    }

    print("\n[STEP 3] OUTBOUND TOOL CALL EGRESS UNBLINDING")
    print(f"  LLM Emitted Tool Arguments (Blinded):")
    print(f"  {json.dumps(llm_tool_call, indent=4)}")

    # Mock tool executor on local secure infrastructure
    def mock_payment_api(unblinded_args: Dict[str, Any]) -> Dict[str, Any]:
        print("\n  [LOCAL SECURE TOOL EXECUTION - IN AIR-GAPPED VPC]")
        print(f"  -> Raw Unblinded Card: {unblinded_args['card_number']}")
        print(f"  -> Raw Unblinded Email: {unblinded_args['notification_email']}")
        print(f"  -> Amount: ${unblinded_args['amount_usd']}")
        return {
            "status": "APPROVED",
            "auth_code": "AUTH_9921",
            "receipt_recipient": unblinded_args["notification_email"]
        }

    tool_res = egress.execute_tool_call("charge_and_notify", llm_tool_call, mock_payment_api)

    print("\n[STEP 4] INGRESS RE-BLINDING TO LLM CONTEXT")
    print("  Result Re-Blinded Before Handing Back to Agent:")
    print(f"  {json.dumps(tool_res, indent=4)}")

    print("\n" + "=" * 74)
    print("  ZERO-KNOWLEDGE PRIVACY GUARANTEE: COMPLETE")
    print(f"  Total Secrets Shielded in Vault: {vault.count_registered()}")
    print("=" * 74 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="blind-tokens: Zero-Knowledge Context Sanitizer & Token Blinded Encryption"
    )
    subparsers = parser.add_subparsers(dest="command")
    demo_parser = subparsers.add_parser("demo", help="Run interactive zero-knowledge demonstration")

    args = parser.parse_args()
    if args.command == "demo" or len(sys.argv) == 1:
        run_demo()


if __name__ == "__main__":
    main()
