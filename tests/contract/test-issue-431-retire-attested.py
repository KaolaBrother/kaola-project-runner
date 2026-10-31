#!/usr/bin/env python3
"""Host-attested never-indexed retirement in a consumer without Workflow."""
import json
import unittest
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("fixture426", Path(__file__).with_name("test-issue-426-retire-legacy-seats.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Fixture = module.Fixture

class HostAttested(Fixture):
    def setup_case(self):
        self.init()
        rev = self.accepted({"dispatch": ["legacy-ref"]})
        self.write_index([])
        self.write_live([{"session": "seat-one", "state": "stopped", "repo": str(self.repo),
                          "holder_instance_id": "holder-one"}])
        return rev

    def evidence(self, binding=None):
        return json.dumps({"kind": "refs-host-attested", "bindings": [binding or {
            "ref": "legacy-ref", "session": "seat-one", "locator": str(self.repo / "README.md")} ]})

    def test_host_attests_without_workflow(self):
        rev = self.setup_case()
        code, out = self.retire("t1", rev, "--index", str(self.index), "--stop-evidence", self.evidence())
        self.assertEqual(code, 0, out)
        receipt = out["value"]["stop_evidence"][0]
        self.assertTrue(receipt["verified"])
        self.assertNotIn("attested", receipt)
        self.assertEqual(receipt["anchors"][0]["session"], "seat-one")
        self.assertFalse((self.repo / "kaola-workflow").exists())

    def test_unverified_self_assertion_must_refuse(self):
        rev = self.setup_case()
        before, index = self.file.read_bytes(), self.index.read_bytes()
        fake_path = self.repo / "fake.txt"
        fake_path.write_text("runner receipt: completed")
        fake = {"ref": "legacy-ref", "session": "not-a-live-session", "locator": "runner receipt: completed"}
        code, out = self.retire("t1", rev, "--index", str(self.index), "--stop-evidence", self.evidence(fake))
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.stayed(before, index)

    def test_bad_anchors_refuse_without_writing(self):
        for binding in ({"ref": "foreign", "session": "seat-one", "locator": "https://example.org/receipt"},
                        {"ref": "legacy-ref", "session": "seat-one", "locator": "free text"},
                        {"ref": "legacy-ref", "session": "seat-one", "locator": "https://[broken"}):
            with self.subTest(binding=binding):
                if self.file.exists(): self.file.unlink()
                rev = self.setup_case()
                before, index = self.file.read_bytes(), self.index.read_bytes()
                code, out = self.retire("t1", rev, "--index", str(self.index), "--stop-evidence", self.evidence(binding))
                self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
                self.stayed(before, index)

    def test_verified_route_needs_no_locator(self):
        rev = self.setup_case()
        evidence = self.evidence({"ref": "legacy-ref", "session": "seat-one"})
        code, out = self.retire("t1", rev, "--index", str(self.index), "--stop-evidence", evidence)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["value"]["stop_evidence"][0]["verified"])

    def test_absent_session_without_locator_refuses(self):
        rev = self.setup_case()
        self.write_live([])
        before, index = self.file.read_bytes(), self.index.read_bytes()
        evidence = self.evidence({"ref": "legacy-ref", "session": "seat-one"})
        code, out = self.retire("t1", rev, "--index", str(self.index), "--stop-evidence", evidence)
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.stayed(before, index)

    def test_multiple_refs_can_share_session(self):
        self.init()
        rev = self.accepted({"dispatch": ["ref-one", "ref-two"]})
        self.write_index([])
        self.write_live([{"session": "seat-one", "state": "stopped", "repo": str(self.repo)}])
        evidence = json.dumps({"kind": "refs-host-attested", "bindings": [
            {"ref": "ref-one", "session": "seat-one"},
            {"ref": "ref-two", "session": "seat-one"}]})
        code, out = self.retire("t1", rev, "--index", str(self.index), "--stop-evidence", evidence)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["value"]["stop_evidence"][0]["verified"])

    def test_missing_session_is_host_attested(self):
        rev = self.setup_case()
        self.write_live([])
        code, out = self.retire("t1", rev, "--index", str(self.index), "--stop-evidence", self.evidence())
        self.assertEqual(code, 0, out)
        receipt = out["value"]["stop_evidence"][0]
        self.assertTrue(receipt["attested"])
        self.assertNotIn("verified", receipt)
        self.assertEqual(receipt["anchors"][0]["locator"], str(self.repo / "README.md"))
        self.assertFalse((self.repo / "kaola-workflow").exists())

    def test_active_or_ambiguous_live_refuses(self):
        for rows in ([{"session": "seat-one", "state": "running", "repo": str(self.repo)}],
                     [{"session": "seat-one", "state": "stopped", "repo": str(self.repo)}] * 2):
            with self.subTest(rows=rows):
                if self.file.exists(): self.file.unlink()
                rev = self.setup_case()
                self.write_live(rows)
                before, index = self.file.read_bytes(), self.index.read_bytes()
                code, out = self.retire("t1", rev, "--index", str(self.index), "--stop-evidence", self.evidence())
                self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
                self.stayed(before, index)

    def test_sideagent_refuses_without_writing(self):
        rev = self.setup_case()
        before, index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index), "--stop-evidence", self.evidence(), writer="sideagent")
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.stayed(before, index)

if __name__ == "__main__":
    unittest.main()
