"""Runs Graphify's `extract --code-only` against the exact same 14 fixture
variants (13 languages, JS split ESM/CJS) as Aletheore's own
`scripts/lang_coverage_matrix.py` in the parent repo, so the two tools are
graded on identical, controlled input.

Ground truth per fixture: 2 functions, 2 classes/structs (0 for C - it has
none), 2 module-level constants, and one real cross-file reference (a call
or explicit import) that a correct graph must resolve. C and C++ define
`helper()` only as a header prototype with no body anywhere - the real
function count there is 1, not 2 (matches the parent script's own comment:
"Header declarations are not definitions").

graph.json schema (graphifyy 0.9.68, verified empirically 2026-09-26 by
hand-inspecting all 14 raw outputs - see lang_coverage/raw/*.json):
- Functions/classes are NOT reliably distinguishable by the `_callable`/
  `_callable_class` flags alone - Go, Rust, and C#'s inner class member
  nodes often carry neither flag despite being real functions/classes.
  This script therefore classifies by matching each node's `norm_label`
  against the known identifiers the fixture actually defines (safe here
  because we authored the fixtures), not by flag alone.
- Cross-file linkage is checked directly: does any edge connect the two
  files' nodes at all (an "imports"/"imports_from" edge, or a "calls" edge
  from the caller symbol to the callee symbol)? A fixture with zero such
  edges failed to resolve the reference even though both symbols were
  individually extracted correctly.
"""
import json, os, shutil, subprocess

ROOT = "/tmp/graphify_langmatrix"
GRAPHIFY_BIN = os.environ.get("GRAPHIFY_BIN", "graphify")
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "lang_coverage", "raw")

# (dir, files, function identifiers, class identifiers, constant identifiers,
#  expected function count, expected class count)
FIXTURES = {
    "python": ("py", {
        "mod.py": "CONST_VALUE = 42\n\n\nclass Widget:\n    pass\n\n\ndef helper():\n    return CONST_VALUE\n",
        "main.py": "from mod import helper\n\nMAIN_CONST = 1\n\n\nclass App:\n    pass\n\n\ndef run():\n    return helper()\n"},
        {"helper()", "run()"}, {"widget", "app"}, {"const_value", "main_const"}, 2, 2),
    "javascript_esm": ("jsesm", {
        "mod.js": "export const CONST_VALUE = 42;\nexport class Widget {}\nexport function helper() { return CONST_VALUE; }\n",
        "main.js": "import { helper } from './mod.js';\nexport const MAIN_CONST = 1;\nexport class App {}\nexport function run() { return helper(); }\n"},
        {"helper()", "run()"}, {"widget", "app"}, {"const_value", "main_const"}, 2, 2),
    "javascript_cjs": ("jscjs", {
        "mod.js": "const CONST_VALUE = 42;\nclass Widget {}\nfunction helper() { return CONST_VALUE; }\nmodule.exports = { helper, Widget, CONST_VALUE };\n",
        "main.js": "const { helper } = require('./mod');\nconst MAIN_CONST = 1;\nclass App {}\nfunction run() { return helper(); }\nmodule.exports = { run, App, MAIN_CONST };\n"},
        {"helper()", "run()"}, {"widget", "app"}, {"const_value", "main_const"}, 2, 2),
    "typescript": ("ts", {
        "mod.ts": "export const CONST_VALUE: number = 42;\nexport class Widget {}\nexport function helper(): number { return CONST_VALUE; }\n",
        "main.ts": "import { helper } from './mod';\nexport const MAIN_CONST: number = 1;\nexport class App {}\nexport function run(): number { return helper(); }\n"},
        {"helper()", "run()"}, {"widget", "app"}, {"const_value", "main_const"}, 2, 2),
    "go": ("go", {
        "go.mod": "module example.com/demo\n\ngo 1.21\n",
        "mod/mod.go": "package mod\n\nconst ConstValue = 42\n\ntype Widget struct{}\n\nfunc Helper() int { return ConstValue }\n",
        "main.go": "package main\n\nimport \"example.com/demo/mod\"\n\nconst MainConst = 1\n\ntype App struct{}\n\nfunc Run() int { return mod.Helper() }\n"},
        {"helper()", "run()"}, {"widget", "app"}, {"constvalue", "mainconst"}, 2, 2),
    "rust": ("rs", {
        "Cargo.toml": "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n",
        "src/lib.rs": "pub mod helper;\n\npub const MAIN_CONST: i32 = 1;\n\npub struct App;\n\npub fn run() -> i32 { helper::help() }\n",
        "src/helper.rs": "pub const CONST_VALUE: i32 = 42;\n\npub struct Widget;\n\npub fn help() -> i32 { CONST_VALUE }\n"},
        {"help()", "run()"}, {"widget", "app"}, {"const_value", "main_const"}, 2, 2),
    "java": ("java", {
        "src/com/example/Mod.java": "package com.example;\n\npublic class Mod {\n    public static final int CONST_VALUE = 42;\n    public static int helper() { return CONST_VALUE; }\n}\n",
        "src/com/example/Main.java": "package com.example;\n\nimport com.example.Mod;\n\npublic class Main {\n    public static final int MAIN_CONST = 1;\n    public static int run() { return Mod.helper(); }\n}\n"},
        {".helper()", ".run()"}, {"mod", "main"}, {"const_value", "main_const"}, 2, 2),
    "ruby": ("rb", {
        "mod.rb": "CONST_VALUE = 42\n\nclass Widget\nend\n\ndef helper\n  CONST_VALUE\nend\n",
        "main.rb": "require_relative 'mod'\n\nMAIN_CONST = 1\n\nclass App\nend\n\ndef run\n  helper\nend\n"},
        {"helper()", "run()"}, {"widget", "app"}, {"const_value", "main_const"}, 2, 2),
    "php": ("php", {
        "composer.json": '{"autoload":{"psr-4":{"App\\\\":"src/"}}}',
        "src/Widget.php": "<?php\nnamespace App;\n\nconst CONST_VALUE = 42;\n\nclass Widget {}\n\nfunction helper() { return CONST_VALUE; }\n",
        "src/Runner.php": "<?php\nnamespace App;\n\nuse App\\Widget;\n\nconst MAIN_CONST = 1;\n\nclass Runner {}\n\nfunction run() { return helper(); }\n"},
        {"helper()", "run()"}, {"widget", "runner"}, {"const_value", "main_const"}, 2, 2),
    "c": ("c", {
        "mod.h": "#ifndef MOD_H\n#define MOD_H\n#define CONST_VALUE 42\nint helper(void);\n#endif\n",
        "main.c": "#include \"mod.h\"\n\nstatic const int MAIN_CONST = 1;\n\nint run(void) { return helper(); }\n"},
        {"run()"}, set(), {"main_const"}, 1, 0),
    "cpp": ("cpp", {
        "mod.hpp": "#pragma once\nconst int CONST_VALUE = 42;\nclass Widget {};\nint helper();\n",
        "main.cpp": "#include \"mod.hpp\"\n\nconst int MAIN_CONST = 1;\n\nclass App {};\n\nint run() { return helper(); }\n"},
        {"run()"}, {"widget", "app"}, {"const_value", "main_const"}, 1, 2),
    "csharp": ("cs", {
        "Mod.cs": "namespace App.Lib;\n\npublic class Mod {\n    public const int ConstValue = 42;\n    public static int Helper() { return ConstValue; }\n}\n",
        "Main.cs": "using App.Lib;\n\nnamespace App.Run;\n\npublic class Main {\n    public const int MainConst = 1;\n    public static int Run() { return Mod.Helper(); }\n}\n"},
        {".helper()", ".run()"}, {"mod", "main"}, {"constvalue", "mainconst"}, 2, 2),
    "kotlin": ("kt", {
        "src/com/example/mod/Mod.kt": "package com.example.mod\n\nconst val CONST_VALUE = 42\n\nclass Widget\n\nfun helper(): Int = CONST_VALUE\n",
        "src/com/example/main/Main.kt": "package com.example.main\n\nimport com.example.mod.helper\nimport com.example.mod.Widget\n\nconst val MAIN_CONST = 1\n\nclass App\n\nfun run(): Int = helper()\n"},
        {"helper()", "run()"}, {"widget", "app"}, {"const_value", "main_const"}, 2, 2),
    "swift": ("sw", {
        "Package.swift": "// swift-tools-version:5.9\nimport PackageDescription\n\nlet package = Package(\n    name: \"Demo\",\n    targets: [\n        .target(name: \"Mod\"),\n        .target(name: \"Main\", dependencies: [\"Mod\"]),\n    ]\n)\n",
        "Sources/Mod/Mod.swift": "public let CONST_VALUE = 42\n\npublic class Widget {}\n\npublic func helper() -> Int { return CONST_VALUE }\n",
        "Sources/Main/Main.swift": "import Mod\n\npublic let MAIN_CONST = 1\n\npublic class App {}\n\npublic func run() -> Int { return helper() }\n"},
        {"helper()", "run()"}, {"widget", "app"}, {"const_value", "main_const"}, 2, 2),
}

shutil.rmtree(ROOT, ignore_errors=True)
os.makedirs(RAW_DIR, exist_ok=True)
rows = []
for lang, (dirname, files, fn_ids, cls_ids, const_ids, exp_fn, exp_cls) in FIXTURES.items():
    d = os.path.join(ROOT, dirname)
    for rel, body in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(body)
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    subprocess.run(["git", "add", "-A"], cwd=d, check=True)
    subprocess.run(["git", "-c", "user.email=a@b.c", "-c", "user.name=t",
                    "commit", "-qm", "x"], cwd=d, check=True)
    proc = subprocess.run([GRAPHIFY_BIN, "extract", ".", "--code-only"],
                          cwd=d, capture_output=True, text=True)
    graph_path = os.path.join(d, "graphify-out", "graph.json")
    if not os.path.exists(graph_path):
        rows.append((lang, "EXTRACT FAILED", 0, exp_fn, 0, exp_cls, 0, len(const_ids), False)); continue
    g = json.load(open(graph_path))
    shutil.copy(graph_path, os.path.join(RAW_DIR, f"{lang}.json"))
    nodes = {n["id"]: n for n in g["nodes"]}
    edges = g["links"]
    norm_labels = {n["id"]: n.get("norm_label", "") for n in nodes.values()}

    found_fn = sum(1 for want in fn_ids if any(nl == want for nl in norm_labels.values()))
    found_cls = sum(1 for want in cls_ids if any(nl == want for nl in norm_labels.values()))
    found_const = sum(1 for want in const_ids if any(nl == want for nl in norm_labels.values()))

    # Cross-file link: any edge whose source and target sit in different
    # source files, of a semantic (not just container "contains") relation.
    file_of = {n["id"]: n.get("source_file") for n in nodes.values()}
    cross_file_linked = any(
        e.get("relation") in ("imports", "imports_from", "calls", "references", "indirect_call")
        and file_of.get(e.get("source")) != file_of.get(e.get("target"))
        for e in edges
    )
    if len(files) < 2:
        cross_file_linked = True  # nothing to link (n/a)

    rows.append((lang, f"{len(nodes)} nodes", found_fn, exp_fn, found_cls, exp_cls,
                 found_const, len(const_ids), cross_file_linked))

print(f"{'language':18s} {'funcs':>7s} {'classes':>9s} {'consts':>9s} {'cross-file link':>16s}")
print("-" * 66)
for lang, parsed, ffn, efn, fcls, ecls, fco, eco, linked in rows:
    fn_ok = "✅" if ffn == efn else f"❌({ffn}/{efn})"
    cls_ok = "✅" if fcls == ecls else (f"❌({fcls}/{ecls})" if ecls else "n/a")
    co_ok = "✅" if fco == eco else f"❌({fco}/{eco})"
    link_ok = "✅" if linked else "❌"
    print(f"{lang:18s} {fn_ok:>7s} {cls_ok:>9s} {co_ok:>9s} {link_ok:>16s}")
