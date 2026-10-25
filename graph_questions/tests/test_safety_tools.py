import json
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gq_purge_limit import is_rate_limited
from purge_bad import is_network_failure
from reproduce import extract_run_archives
from safe_cleanup import quarantine_json_files
from scoring import load_tasks, score


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

    def test_session_limit_variants_are_kept_as_candidates(self):
        for text in (
            "maximum session limit",
            "session limit is 5h",
            "your session limit resets at midnight",
        ):
            with self.subTest(text=text):
                self.assertTrue(is_rate_limited({"result": text}))

    def test_partial_quarantine_failure_reports_what_moved(self):
        with tempfile.TemporaryDirectory() as temporary:
            results = Path(temporary) / "out"
            results.mkdir()
            first = results / "a.json"
            second = results / "b.json"
            first.write_text('{"result":"session limit"}', encoding="utf-8")
            second.write_text('{"result":"session limit"}', encoding="utf-8")
            real_move = __import__("shutil").move

            def fail_second(source, destination):
                if Path(source).name == "b.json":
                    raise PermissionError("blocked")
                return real_move(source, destination)

            with patch("safe_cleanup.shutil.move", side_effect=fail_second):
                with self.assertRaisesRegex(OSError, "moved 1 of 2.*a.json"):
                    quarantine_json_files(results, is_rate_limited, apply=True)
            self.assertFalse(first.exists())
            self.assertTrue(second.exists())

    def test_non_object_json_is_skipped(self):
        with tempfile.TemporaryDirectory() as temporary:
            results = Path(temporary) / "out"
            results.mkdir()
            (results / "array.json").write_text("[]", encoding="utf-8")
            self.assertEqual(quarantine_json_files(results, is_rate_limited), [])


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

    def test_existing_empty_output_directory_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            existing = base / "out_demo"
            existing.mkdir()
            self.make_archive(base, "out_demo/result.json", "replacement")

            extract_run_archives(base)

            self.assertEqual(list(existing.iterdir()), [])

    def test_output_directory_created_during_extraction_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            destination = base / "out_demo"
            self.make_archive(base, "out_demo/result.json", "replacement")
            real_mkdir = os.mkdir
            raced = False

            def create_racing_destination(path, *args, **kwargs):
                nonlocal raced
                if os.fspath(path) == str(destination) and not raced:
                    raced = True
                    real_mkdir(path, *args, **kwargs)
                    raise FileExistsError(path)
                return real_mkdir(path, *args, **kwargs)

            with patch("reproduce.os.mkdir", side_effect=create_racing_destination):
                extract_run_archives(base)

            self.assertEqual(list(destination.iterdir()), [])

    def test_missing_runs_directory_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as temporary:
            extract_run_archives(temporary)

    def test_running_purge_on_its_base_directory_is_allowed(self):
        with patch.object(sys, "argv", ["gq_purge_limit.py", "."]):
            output = io.StringIO()
            with redirect_stdout(output):
                from gq_purge_limit import main

                main()
            self.assertIn("0 candidate(s)", output.getvalue())

    def test_rejects_archive_path_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            self.make_archive(base, "out_demo/../../tracked.json", "overwrite")

            with self.assertRaises(ValueError):
                extract_run_archives(base)

            self.assertFalse((base / "tracked.json").exists())


class SharedScoringTests(unittest.TestCase):
    def test_score_is_shared_and_keeps_direct_answer_behavior(self):
        task = {"kind": "direct", "truth": ["src/a.py"]}
        self.assertEqual(score(task, '["src/a.py"]'), (1.0, True))
        self.assertEqual(score(task, "not json"), (0.0, False))

    def test_task_loader_reads_requested_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            task_file = Path(temporary) / "tasks.json"
            task_file.write_text('[{"id":"one"}]', encoding="utf-8")
            self.assertEqual(load_tasks(["tasks.json"], temporary), {"one": {"id": "one"}})


if __name__ == "__main__":
    unittest.main()
