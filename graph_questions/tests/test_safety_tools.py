import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gq_purge_limit import is_rate_limited
from purge_bad import is_network_failure
from reproduce import extract_run_archives
from safe_cleanup import quarantine_json_files


class SafeCleanupTests(unittest.TestCase):
    def test_dry_run_preserves_candidate_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            results = root / "out"
            results.mkdir()
            result = results / "candidate.json"
            result.write_text(json.dumps({"result": "session limit reached"}), encoding="utf-8")

            matches = quarantine_json_files(results, is_rate_limited)

            self.assertEqual(matches, [result.resolve()])
            self.assertTrue(result.exists())
            self.assertFalse((root / "quarantine").exists())

    def test_apply_moves_candidate_to_quarantine_without_deleting_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            results = root / "out"
            results.mkdir()
            result = results / "candidate.json"
            contents = json.dumps({"rc": 1, "raw": "API error: unable to connect"})
            result.write_text(contents, encoding="utf-8")

            matches = quarantine_json_files(results, is_network_failure, apply=True)

            self.assertEqual(matches, [result.resolve()])
            self.assertFalse(result.exists())
            quarantined = list((root / "quarantine").rglob("candidate.json"))
            self.assertEqual(len(quarantined), 1)
            self.assertEqual(quarantined[0].read_text(encoding="utf-8"), contents)

    def test_session_limit_match_is_specific(self):
        self.assertTrue(is_rate_limited({"result": "You hit your session limit"}))
        self.assertFalse(is_rate_limited({"result": "You hit your breakpoint"}))


class ReproductionExtractionTests(unittest.TestCase):
    def make_archive(self, base, member_name, contents):
        runs = base / "runs"
        runs.mkdir(exist_ok=True)
        archive_path = runs / "out_demo.tar.gz"
        payload = base / "payload"
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_text(contents, encoding="utf-8")
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(payload, arcname=member_name)
        return archive_path

    def test_extracts_under_output_dir_and_preserves_repo_root_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo_file = base / "tracked.json"
            repo_file.write_text("tracked", encoding="utf-8")
            self.make_archive(base, "out_demo/result.json", "result")

            extract_run_archives(base)

            self.assertEqual(repo_file.read_text(encoding="utf-8"), "tracked")
            self.assertEqual((base / "out_demo/result.json").read_text(encoding="utf-8"), "result")

    def test_existing_output_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            existing = base / "out_demo"
            existing.mkdir()
            original = existing / "result.json"
            original.write_text("original", encoding="utf-8")
            self.make_archive(base, "out_demo/result.json", "replacement")

            extract_run_archives(base)

            self.assertEqual(original.read_text(encoding="utf-8"), "original")

    def test_rejects_archive_path_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            self.make_archive(base, "out_demo/../../tracked.json", "overwrite")

            with self.assertRaises(ValueError):
                extract_run_archives(base)

            self.assertFalse((base / "tracked.json").exists())


if __name__ == "__main__":
    unittest.main()
