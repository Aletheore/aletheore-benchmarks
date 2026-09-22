"""Scores aletheore_3x_results.json (or any file matching its shape) against
ground_truth.json's 44 golden bugs, using (file substring, line window,
keyword) signatures - a real hand-validated matching key, not a fresh LLM
judge, built by reading each finding's actual text against the real diff and
real repo source across multiple scoring passes (2026-09-21). Encodes
already-established matches so re-scoring a new run is fast and consistent,
not a re-derivation from scratch each time.

Deliberately not an LLM judge: this session's own earlier free-tier
benchmark found judge agreement with manual scoring unreliable enough to
need auditing (see aletheore-benchmarks history), so recall/precision here
are computed from an explicit, readable, reviewable matching table instead.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
CORPUS_DIR = HERE.parent
RESULTS_DIR = CORPUS_DIR / "results"

# (file_substring, line_center_or_None, line_tolerance, [keyword_any_of],
# optional extra_file_substring_required) - a finding matches a golden if
# file_substring is in its file path AND (line is None OR within tolerance
# of center) AND at least one keyword (if any given) appears in its issue
# text (case-insensitive). None means this golden was never matched by any
# configuration tested this session (kept explicit, not silently omitted).
SIGNATURES = {
    "keycloak-37429": [
        ("messages_lt.properties", None, 0, ["italian", "totpstep1"], "account"),
        ("messages_zh_CN.properties", None, 0, ["traditional chinese", "simplified"], "account"),
        None,
        ("VerifyMessageProperties.java", 122, 30, ["santizeanchors", "anchor"]),
        None,
    ],
    "sentry-95633": [None, None],
    "calcom-22532": [
        ("CalendarService.ts", 1022, 5, ["updatemanybycredentialid"]),
        ("test-gcal-webhooks.sh", None, 0, ["sed -i"]),
        None,
        ("CredentialActionsDropdown.tsx", 100, 10, ["en-us", "hardcoded locale"]),
    ],
    "grafana-80329": [
        ("xorm_store.go", 538, 15, ["error", "log level"]),
        ("cleanup.go", 77, 2, ["10 min", "1 min", "ticker"]),
    ],
    "sentry-80168": [
        None,
        None,
        ("test_detector.py", 195, 10, ["group_2", "group2"]),
    ],
    "sentry-80528": [
        ("incident_occurrence.py", 160, 10, ["unused", "config"]),
        ("incidents.py", 70, 70, ["previous_checkins", "ordering", "ok/active", "muted"]),
    ],
    "grafana-76186": [
        None,
        ("logger_middleware.go", 44, 10, ["traceid"]),
        ("fake.go", 46, 5, ["testlogger", "fromcontext", "newtestlogger"]),
    ],
    "grafana-103633": [
        ("service.go", 116, 10, ["stale denial cache", "permdenialcache"]),
        None,
        ("cache.go", 30, 5, ["cache key collision", "underscore"]),
    ],
    "grafana-79265": [
        ("database.go", 105, 15, ["race condition", "countdevices", "count-then"]),
        ("client.go", 44, 2, ["tagdevice", "synchronous", "goroutine"]),
        ("database.go", 78, 15, ["rowsaffected", "errdevicelimitreached"]),
        ("database.go", 78, 15, ["30 days", "time window", "stale device"]),
        None,
    ],
    "calcom-22345": [None, None],
    "calcom-10967": [
        ("EventManager.ts", 118, 5, ["mainhostdestinationcalendar"]),
        None,
        ("CalendarService.ts", 254, 5, ["externalid", "find"]),
        ("create.handler.ts", 150, 5, ["slug", "invert"]),
        (None, None, 0, ["createevent", "credentialid", "interface", "second parameter", "second argument"]),
        ("EventManager.ts", 509, 5, ["undefined credential", "updateallcalendarevents", "updateeventoncalendar"]),
    ],
    "calcom-10600": [
        ("BackupCode.tsx", 7, 3, ["twofactor", "naming"]),
        None,
        None,
        ("next-auth-options.ts", 146, 10, ["race condition", "code reuse", "non-atomic"]),
        ("EnableTwoFactorModal.tsx", 82, 30, ["url", "revoke", "createobjecturl", "resource leak"]),
    ],
    "calcom-8087": [
        (None, None, 0, ["dynamic import", "promise<module>", "unhandled import failure"]),
        (None, None, 0, ["foreach(async", "unawaited"]),
    ],
}


def matches(finding: dict, sig) -> bool:
    if sig is None:
        return False
    file_sub, line_center, tol, keywords = sig[0], sig[1], sig[2], sig[3]
    extra_req = sig[4] if len(sig) > 4 else None
    if file_sub is not None and file_sub not in finding["file"]:
        return False
    if extra_req is not None and extra_req not in finding["file"]:
        return False
    if line_center is not None and abs(finding["line"] - line_center) > tol:
        return False
    text = finding["issue"].lower()
    if keywords and not any(kw in text for kw in keywords):
        return False
    return True


def score_file(results_path: Path, output_path: Path) -> None:
    data = json.load(open(results_path))
    summary = {}
    for config in ["flash", "air"]:
        if config not in data or not data[config]:
            continue
        trial_recalls = []
        trial_precisions = []
        for trial_idx, trial in enumerate(data[config]):
            total_goldens = 0
            total_matched_goldens = 0
            total_findings = 0
            total_matched_findings = 0
            for case_id, sigs in SIGNATURES.items():
                findings = trial["findings"].get(case_id, [])
                total_findings += len(findings)
                total_goldens += len(sigs)
                matched_flags = [False] * len(findings)
                for sig in sigs:
                    hit = False
                    for fi, f in enumerate(findings):
                        if matches(f, sig):
                            hit = True
                            matched_flags[fi] = True
                    if hit:
                        total_matched_goldens += 1
                total_matched_findings += sum(matched_flags)
            recall = total_matched_goldens / total_goldens
            precision = total_matched_findings / total_findings if total_findings else 0.0
            trial_recalls.append((total_matched_goldens, total_goldens, recall))
            trial_precisions.append((total_matched_findings, total_findings, precision))
            print(f"{config} trial {trial_idx + 1}: recall {total_matched_goldens}/{total_goldens} "
                  f"({recall:.1%}), precision {total_matched_findings}/{total_findings} ({precision:.1%})")
        avg_recall = sum(r[2] for r in trial_recalls) / len(trial_recalls)
        avg_precision = sum(p[2] for p in trial_precisions) / len(trial_precisions)
        print(f"{config} AVERAGE over {len(trial_recalls)} trial(s): "
              f"recall {avg_recall:.1%}, precision {avg_precision:.1%}\n")
        summary[config] = {
            "recalls": trial_recalls, "precisions": trial_precisions,
            "avg_recall": avg_recall, "avg_precision": avg_precision,
        }
    json.dump(summary, open(output_path, "w"), indent=2)


if __name__ == "__main__":
    import sys
    results_path = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS_DIR / "aletheore_3x_results.json"
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else RESULTS_DIR / "aletheore_3x_summary.json"
    score_file(results_path, output_path)
