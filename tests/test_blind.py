"""
Unit tests for Blind-Tokens zero-knowledge context sanitization and egress unblinding.
"""

import unittest
from blind_tokens.models import TokenType
from blind_tokens.vault import BlindTokenVault
from blind_tokens.sanitizer import ContextSanitizer
from blind_tokens.egress import ToolEgressAdapter
from blind_tokens.verifier import ReasoningTraceVerifier


class TestBlindTokens(unittest.TestCase):

    def setUp(self):
        self.vault = BlindTokenVault()
        self.sanitizer = ContextSanitizer(self.vault)
        self.egress = ToolEgressAdapter(self.vault, self.sanitizer)
        self.verifier = ReasoningTraceVerifier(self.vault)

    def test_vault_surrogate_bidirectional(self):
        secret = "sk-ant-api03-abcdef123456789012345678"
        surrogate = self.vault.get_or_create_surrogate(secret, TokenType.API_KEY)
        self.assertTrue(surrogate.startswith("[BLIND_API_KEY:"))
        self.assertEqual(self.vault.unblind(surrogate), secret)

    def test_sanitizer_replaces_secrets(self):
        prompt = (
            "Contact john.doe@example.com using key sk-abcdef1234567890abcdef123456 "
            "with SSN 123-45-6789."
        )
        res = self.sanitizer.sanitize_text(prompt)
        self.assertEqual(res.tokens_blinded, 3)
        self.assertNotIn("john.doe@example.com", res.sanitized_text)
        self.assertNotIn("sk-abcdef1234567890abcdef123456", res.sanitized_text)
        self.assertNotIn("123-45-6789", res.sanitized_text)
        self.assertIn("[BLIND_EMAIL:", res.sanitized_text)
        self.assertIn("[BLIND_API_KEY:", res.sanitized_text)
        self.assertIn("[BLIND_SSN:", res.sanitized_text)

    def test_message_structure_sanitization(self):
        messages = [
            {"role": "user", "content": "My IP is 192.168.1.100 and email is dev@corp.io"}
        ]
        sanitized = self.sanitizer.sanitize_messages(messages)
        content = sanitized[0]["content"]
        self.assertNotIn("192.168.1.100", content)
        self.assertNotIn("dev@corp.io", content)
        self.assertIn("[BLIND_IP_ADDRESS:", content)
        self.assertIn("[BLIND_EMAIL:", content)

    def test_egress_unblinding_and_reblinding(self):
        raw_card = "4000 1234 5678 9010"
        surrogate_card = self.vault.get_or_create_surrogate(raw_card, TokenType.CREDIT_CARD)

        executed_with_raw = False

        def local_mock_gateway(args):
            nonlocal executed_with_raw
            if args["card"] == raw_card:
                executed_with_raw = True
            return {"status": "ok", "echo_card": args["card"]}

        res = self.egress.execute_tool_call(
            "charge",
            {"card": surrogate_card, "amount": 100},
            local_mock_gateway
        )

        self.assertTrue(executed_with_raw)
        self.assertEqual(res["tool"], "charge")
        # Ensure echoed card was re-blinded in the output
        self.assertEqual(res["blinded_result"]["echo_card"], surrogate_card)

    def test_reasoning_trace_audit(self):
        raw_key = "sk-supersecret12345678901234"
        surrogate = self.vault.get_or_create_surrogate(raw_key, TokenType.API_KEY)

        clean_trace = f"<thinking>Using key surrogate {surrogate} to invoke query.</thinking>"
        audit_clean = self.verifier.audit_trace(clean_trace)
        self.assertTrue(audit_clean.is_clean)
        self.assertEqual(audit_clean.risk_score, 0.0)

        dirty_trace = f"<thinking>Raw secret was {raw_key}!</thinking>"
        audit_dirty = self.verifier.audit_trace(dirty_trace)
        self.assertFalse(audit_dirty.is_clean)
        self.assertEqual(audit_dirty.leaked_tokens_count, 1)
        self.assertGreater(audit_dirty.risk_score, 0.0)


if __name__ == "__main__":
    unittest.main()
