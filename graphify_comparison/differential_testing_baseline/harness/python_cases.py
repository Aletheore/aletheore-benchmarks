"""Differential-testing harness for the Python real_bug_fix cases
(001, 002, 003, 004) in benchmarks/pr-review-benchmark/cases/.

Each OLD/NEW pair is reconstructed directly from that case's pr.diff (plus,
for 003, the real full function fetched from GitHub at repo.txt's
base_commit, since the diff hunk alone didn't include the whole loop).
Reports DIVERGED (a real counterexample input found - a real verifier
would flag this) or IDENTICAL (no divergence found across all generated
inputs) per case.
"""
import importlib.metadata
import pickle
import json
import re

results = []

# --- 001: flask-cli-key-quote --------------------------------------------
def v001_old(is_context):
    if is_context:
        raise ValueError('When "--cert" is an SSLContext object, "--key" is not used.')

def v001_new(is_context):
    if is_context:
        raise ValueError('When "--cert" is an SSLContext object, "--key is not used.')

def run_001():
    try:
        v001_old(True)
    except ValueError as e:
        old_msg = str(e)
    try:
        v001_new(True)
    except ValueError as e:
        new_msg = str(e)
    return ("DIVERGED", f"old={old_msg!r} new={new_msg!r}") if old_msg != new_msg else ("IDENTICAL", "")

results.append(("001-flask-cli-key-quote", *run_001()))

# --- 002: requests-json-decode-pickle -------------------------------------
CompatJSONDecodeError = json.JSONDecodeError

class InvalidJSONError(IOError):
    def __init__(self, *args, **kwargs):
        self.response = kwargs.pop("response", None)
        self.request = kwargs.pop("request", None)
        if self.response is not None and not self.request and hasattr(self.response, "request"):
            self.request = self.response.request
        super().__init__(*args, **kwargs)

class JSONDecodeError_OLD(InvalidJSONError, CompatJSONDecodeError):
    def __init__(self, *args, **kwargs):
        CompatJSONDecodeError.__init__(self, *args)
        InvalidJSONError.__init__(self, *self.args, **kwargs)
    def __reduce__(self):
        return CompatJSONDecodeError.__reduce__(self)

class JSONDecodeError_NEW(InvalidJSONError, CompatJSONDecodeError):
    def __init__(self, *args, **kwargs):
        CompatJSONDecodeError.__init__(self, *args)
        InvalidJSONError.__init__(self, *self.args, **kwargs)

def try_pickle(cls):
    e = cls("Expecting value", "{}", 0)
    try:
        restored = pickle.loads(pickle.dumps(e))
        return f"ok: {restored!r}"
    except Exception as exc:
        return f"raised {type(exc).__name__}: {exc}"

def run_002():
    old_r = try_pickle(JSONDecodeError_OLD)
    new_r = try_pickle(JSONDecodeError_NEW)
    return ("DIVERGED", f"old={old_r!r} new={new_r!r}") if old_r != new_r else ("IDENTICAL", "")

results.append(("002-requests-json-decode-pickle", *run_002()))

# --- 003: requests-proxy-bypass-registry ----------------------------------
# Full function fetched from psf/requests at the case's pinned base_commit
# (raw.githubusercontent.com) - isolating just the check-value loop as a
# pure function of (proxy_override_raw_string, host).
def bypass_old(proxy_override_raw, host):
    proxyOverride = proxy_override_raw.split(";")
    proxyOverride = filter(None, proxyOverride)
    for test in proxyOverride:
        if test == "<local>":
            if "." not in host:
                return True
        test = test.replace(".", r"\.").replace("*", r".*").replace("?", r".")
        if re.match(test, host, re.I):
            return True
    return False

def bypass_new(proxy_override_raw, host):
    proxyOverride = proxy_override_raw.split(";")
    for test in proxyOverride:
        if test == "<local>":
            if "." not in host:
                return True
        test = test.replace(".", r"\.").replace("*", r".*").replace("?", r".")
        if re.match(test, host, re.I):
            return True
    return False

def run_003():
    for raw, host in [
        ("example.com;;192.168.*", "some-other-host.example"),  # empty entry between two ';'
        (";internal.local", "totally-unrelated-host"),           # leading empty entry
        ("<local>;", "plainhost"),
    ]:
        o, n = bypass_old(raw, host), bypass_new(raw, host)
        if o != n:
            return "DIVERGED", f"proxyOverride={raw!r} host={host!r} old={o} new={n}"
    return "IDENTICAL", ""

results.append(("003-requests-proxy-bypass-registry", *run_003()))

# --- 004: click-version-package-name --------------------------------------
class PackageNotFoundError(Exception):
    pass

FAKE_VERSIONS = {"Pillow": "10.4.0"}
FAKE_PACKAGES_DISTRIBUTIONS = {"PIL": ["Pillow"]}

def fake_version(name):
    if name in FAKE_VERSIONS:
        return FAKE_VERSIONS[name]
    raise PackageNotFoundError(name)

def resolve_old(package_name):
    try:
        return fake_version(package_name)
    except PackageNotFoundError:
        distributions = FAKE_PACKAGES_DISTRIBUTIONS.get(package_name, [])
        if len(distributions) == 1:
            return fake_version(distributions[0])
        elif len(distributions) > 1:
            raise RuntimeError(
                f"{package_name!r} maps to multiple installed distributions "
                f"({', '.join(distributions)}). Pass 'package_name' to disambiguate."
            ) from None
        else:
            raise RuntimeError(
                f"{package_name!r} is not installed. Try passing 'package_name' instead."
            ) from None

def resolve_new(package_name):
    try:
        return fake_version(package_name)
    except PackageNotFoundError:
        raise RuntimeError(
            f"{package_name!r} is not installed. Try passing 'package_name' instead."
        ) from None

def run_004():
    for name in ["PIL", "Pillow", "totally-unknown-package"]:
        old_r = new_r = None
        old_err = new_err = None
        try:
            old_r = resolve_old(name)
        except RuntimeError as e:
            old_err = str(e)
        try:
            new_r = resolve_new(name)
        except RuntimeError as e:
            new_err = str(e)
        if (old_r, old_err) != (new_r, new_err):
            return "DIVERGED", f"package_name={name!r} old=({old_r!r},{old_err!r}) new=({new_r!r},{new_err!r})"
    return "IDENTICAL", ""

results.append(("004-click-version-package-name", *run_004()))

print(f"{'case':40s} {'result':10s} detail")
print("-" * 100)
for case, status, detail in results:
    print(f"{case:40s} {status:10s} {detail}")
