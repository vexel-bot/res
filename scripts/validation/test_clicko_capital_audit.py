"""A completed response must not hide an earlier turn with uncertain billing."""
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("capital_audit", Path(__file__).with_name("clicko-capital-audit.py"))
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class CapitalAuditTest(unittest.TestCase):
    def test_completed_jobs_keep_uncertain_turns_separate_from_measured_usage_and_reservations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.sqlite"
            db = sqlite3.connect(path)
            db.execute("CREATE TABLE studio_llm_connections (id TEXT, config TEXT, provider TEXT)")
            db.execute("CREATE TABLE studio_generation_jobs (id TEXT, status TEXT, request TEXT, result TEXT, document_id TEXT, created_at TEXT, provider TEXT, error_code TEXT)")
            db.execute("INSERT INTO studio_llm_connections VALUES ('connection','{}','anthropic')")
            for identifier, cost, changes in [
                ("closed", .5, {}),
                ("succeeded-with-lost-turn", .5, {"uncertainCostUpperBoundUsd": .2}),
                ("pending-turn", .25, {"pendingTurnBudget": {"maxOutputTokens": 100}}),
            ]:
                result = {"submissionStarted": True, "submissionOutcome": "response_received",
                          "measuredCostUsd": cost, "financialReservationUsd": 1.5, **changes}
                db.execute("INSERT INTO studio_generation_jobs VALUES (?,?,?,?,?,?,?,?)", (
                    identifier, "succeeded", json.dumps({"llmConnectionId": "connection", "model": "claude-opus-5-5"}),
                    json.dumps(result), "doc", "2026-11-12", "llm.anthropic", None,
                ))
            db.commit(); db.close()
            report = audit_module.audit(path)
            self.assertEqual(report["knownAnthropicCostUsd"], 1.25)
            self.assertEqual(report["directReservationUsd"], 4.5)
            self.assertEqual(report["recordedUncertainCostUpperBoundUsd"], .2)
            self.assertEqual(set(report["unknownSubmissionIds"]), {"succeeded-with-lost-turn", "pending-turn"})
            self.assertTrue(report["remainingEstimateExcludesUncertainCharges"])
            self.assertFalse(report["providerBalanceReconciled"])


if __name__ == "__main__":
    unittest.main()
