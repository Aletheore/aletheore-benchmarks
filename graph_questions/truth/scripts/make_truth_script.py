#!/usr/bin/env python3
"""Independent ground-truth file-level dependency graph for PHP or Ruby repos.
usage: make_truth_script.py <php|ruby> <repo_dir> <out.json>
Output: {"files": [...source files...], "edges": [[from, to], ...]} (repo-relative, sorted, deduped, no self edges).
Does not read .aletheore/. Helper programs are written to ./truth_work_script/.

PHP rules (PHP's own tokenizer, token_get_all; comments/strings/heredocs never scanned for names):
  * Declaration map: every class/interface/trait/enum declared in any file -> fully qualified name -> file(s).
    (composer.json PSR-4 maps, incl. autoload-dev, are used only as a fallback for undeclared names.)
  * use imports (plain, aliased, comma lists, group use incl. alias); `use function/const` ignored; trait `use`
    inside class bodies and closure `use (...)` are not imports (trait names are caught as references).
  * References: any capitalised/qualified name token (extends, implements, new, static ::, instanceof, type hints,
    catch, attributes, ::class) resolved via the current namespace + use aliases (case-insensitive) to its declaring file.
  * require/include(_once) with string / __DIR__ / dirname(__DIR__[,n]) concatenations that resolve to an in-repo file.
Ruby rules (Ripper):
  * require_relative; require/load resolved against the load path (lib, test, spec, repo root, and the file's own dir for
    __dir__/__FILE__-based expand_path/join forms); autoload :Const, "path" (edge to file, and constant bound to it);
    repo-defined `require_all "dir"` helper -> every dir/*.rb (non-recursive) under lib/.
  * Constant references (nesting-aware lexical lookup, then top level; `::A::B`, `A::B`) resolved to the file defining
    them. If several files define/reopen the constant, the one whose path matches the constant name by Zeitwerk
    convention (Jekyll::Foo -> jekyll/foo.rb) is used, else the constant is skipped (ambiguous). Core constants skipped.
"""
import collections, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _tools import run_tool

W = "./truth_work_script"
SKIP_DIRS = {".git", ".aletheore", "node_modules", "vendor"}

PHP_HELPER = r'''<?php
// usage: php names.php <root> files... ; JSON {file: {decls, refs, imports, includes}}
$root = $argv[1]; $out = [];
$kw = [T_WHITESPACE, T_COMMENT, T_DOC_COMMENT];
function resolve($name, $ns, $al) {
    if ($name[0] === '\\') return strtolower(substr($name, 1));
    if (stripos($name, 'namespace\\') === 0) return strtolower(($ns !== '' ? $ns . '\\' : '') . substr($name, 10));
    $p = strpos($name, '\\'); $first = strtolower($p === false ? $name : substr($name, 0, $p));
    if (isset($al[$first])) return strtolower($al[$first] . ($p === false ? '' : substr($name, $p)));
    return strtolower(($ns !== '' ? $ns . '\\' : '') . $name);
}
for ($i = 2; $i < count($argv); $i++) {
    $f = $argv[$i];
    $src = @file_get_contents("$root/$f"); if ($src === false) continue;
    $toks = [];
    foreach (@token_get_all($src) as $t) { if (is_array($t) && in_array($t[0], $kw)) continue; $toks[] = $t; }
    $ns = ''; $al = []; $decls = []; $refs = []; $imports = []; $includes = [];
    $n = count($toks); $depth = 0; $classDepths = []; $pending = false;
    for ($k = 0; $k < $n; $k++) {
        $t = $toks[$k]; $id = is_array($t) ? $t[0] : null; $txt = is_array($t) ? $t[1] : $t;
        if ($txt === '{' || $id === T_CURLY_OPEN || $id === T_DOLLAR_OPEN_CURLY_BRACES) { $depth++; if ($pending && $txt === '{') { $classDepths[] = $depth; $pending = false; } continue; }
        if ($txt === '}') { if ($classDepths && end($classDepths) === $depth) array_pop($classDepths); $depth--; continue; }
        if ($id === T_NAMESPACE) {
            $nx = $toks[$k + 1] ?? null;
            if (is_array($nx) && in_array($nx[0], [T_STRING, T_NAME_QUALIFIED])) { $ns = $nx[1]; $al = []; $k++; }
            elseif ($nx === '{') { $ns = ''; $al = []; }
            continue;
        }
        if ($id === T_USE && !$classDepths) {
            $pv = $toks[$k - 1] ?? null;
            if ($pv === ')') continue; // closure use
            $k++; $buf = [];
            $kind = 'class';
            if (is_array($toks[$k]) && in_array($toks[$k][0], [T_FUNCTION, T_CONST])) $kind = 'x';
            for (; $k < $n && $toks[$k] !== ';'; $k++) { $tk = $toks[$k]; $buf[] = is_array($tk) ? $tk[1] : $tk; }
            if ($kind !== 'class') continue;
            $s = preg_replace('/\s+/', ' ', implode(' ', $buf));
            $s = str_replace([' \\', '\\ '], '\\', $s);
            $items = [];
            if (strpos($s, '{') !== false) {
                [$pre, $grp] = explode('{', $s, 2); $pre = trim($pre);
                foreach (explode(',', rtrim(trim($grp), '}')) as $it) {
                    $it = trim($it); if ($it === '') continue;
                    if (preg_match('/^(function|const)\s/i', $it)) continue;
                    $items[] = $pre . $it;
                }
            } else {
                foreach (explode(',', $s) as $it) { $it = trim($it); if ($it !== '') $items[] = $it; }
            }
            foreach ($items as $it) {
                $a = preg_split('/\s+as\s+/i', trim($it)); $fq = ltrim(trim($a[0]), '\\');
                $pos = strrpos($fq, '\\');
                $alias = trim($a[1] ?? ($pos !== false ? substr($fq, $pos + 1) : $fq));
                $al[strtolower($alias)] = $fq; $imports[] = strtolower($fq);
            }
            continue;
        }
        if (in_array($id, [T_CLASS, T_INTERFACE, T_TRAIT, T_ENUM], true)) {
            $prev = $toks[$k - 1] ?? null;
            if (is_array($prev) && $prev[0] == T_DOUBLE_COLON) continue;
            $nx = $toks[$k + 1] ?? null;
            $pending = true;
            if (is_array($nx) && $nx[0] == T_STRING) { $decls[] = strtolower(($ns !== '' ? $ns . '\\' : '') . $nx[1]); $k++; }
            continue;
        }
        if (in_array($id, [T_REQUIRE, T_REQUIRE_ONCE, T_INCLUDE, T_INCLUDE_ONCE], true)) {
            $cur = ''; $j = $k + 1;
            for (; $j < $n && $toks[$j] !== ';'; $j++) {
                $x = $toks[$j];
                if (is_array($x) && $x[0] === T_DIR) { $cur .= '<DIR>'; }
                elseif (is_array($x) && $x[0] === T_CONSTANT_ENCAPSED_STRING) { $cur .= substr($x[1], 1, -1); }
                elseif (is_array($x) && $x[0] === T_STRING && strtolower($x[1]) === 'dirname') {
                    $lv = 1;
                    $j++; while ($j < $n && $toks[$j] !== ')') { $y = $toks[$j]; if (is_array($y) && $y[0] === T_LNUMBER) $lv = (int)$y[1]; $j++; }
                    $cur .= '<DIR>' . str_repeat('/..', $lv);
                }
            }
            if ($cur !== '') $includes[] = $cur;
            continue;
        }
        if ($id === T_STRING || $id === T_NAME_QUALIFIED || $id === T_NAME_FULLY_QUALIFIED || $id === T_NAME_RELATIVE) {
            $prev = $toks[$k - 1] ?? null; $pid = is_array($prev) ? $prev[0] : $prev;
            if (in_array($pid, [T_OBJECT_OPERATOR, T_NULLSAFE_OBJECT_OPERATOR, T_DOUBLE_COLON, T_FUNCTION, T_CONST, T_GOTO, T_NAMESPACE], true)) continue;
            $nx = $toks[$k + 1] ?? null;
            if ($nx === '(' && $pid !== T_NEW) continue;
            if ($pid === T_CASE && !(is_array($nx) && $nx[0] === T_DOUBLE_COLON)) continue;
            if ($nx === ':' && $id === T_STRING && ($pid === '(' || $pid === ',')) continue; // named argument
            if ($id === T_STRING && !ctype_upper($txt[0])) continue;
            if (in_array(strtolower($txt), ['self', 'static', 'parent', 'true', 'false', 'null'])) continue;
            $refs[] = resolve($txt, $ns, $al);
        }
    }
    $out[$f] = ['decls' => array_values(array_unique($decls)), 'refs' => array_values(array_unique($refs)),
                'imports' => array_values(array_unique($imports)), 'includes' => $includes];
}
echo json_encode($out);
'''

RB_HELPER = r'''# usage: ruby consts.rb <root> files... ; JSON {file => {defs, refs:[[name, abs, nest]], reqs:[[kind, spec, rel, dyn]], autoloads:[[fq, path]]}}
require "ripper"
require "json"
root = ARGV.shift
out = {}
REQ = %w[require require_relative load require_all autoload]

def path_of(node)
  case node[0]
  when :var_ref, :var_field
    return nil unless node[1].is_a?(Array) && node[1][0] == :@const
    [[node[1][1]], false]
  when :const_ref then [[node[1][1]], false]
  when :top_const_ref, :top_const_field then [[node[1][1]], true]
  when :const_path_ref, :const_path_field
    left = path_of(node[1]); return nil unless left
    right = node[2]; return nil unless right.is_a?(Array) && right[0] == :@const
    [left[0] + [right[1]], left[1]]
  end
end

def strings_of(args)
  strs = []; rel = false; dyn = false
  stack = [args]
  until stack.empty?
    x = stack.shift
    next unless x.is_a?(Array)
    case x[0]
    when :@tstring_content then strs << x[1]
    when :string_embexpr then dyn = true
    when :@kw then rel = true if x[1] == "__FILE__"
    when :@ident then rel = true if x[1] == "__dir__"
    end
    x.each { |y| stack << y if y.is_a?(Array) }
  end
  [strs, rel, dyn]
end

def walk(node, nest, res)
  return unless node.is_a?(Array)
  case node[0]
  when :module, :class
    p = path_of(node[1])
    if p
      fq = (p[1] || nest.empty?) ? p[0].join("::") : nest.last + "::" + p[0].join("::")
      res[:defs] << fq
      walk(node[2], nest, res) if node[0] == :class && node[2]
      body = node[0] == :module ? node[2] : node[3]
      walk(body, nest + [fq], res)
      return
    end
  when :assign
    tgt = node[1]
    if tgt.is_a?(Array) && [:var_field, :const_path_field, :top_const_field].include?(tgt[0])
      p = path_of(tgt)
      if p
        fq = (p[1] || nest.empty?) ? p[0].join("::") : nest.last + "::" + p[0].join("::")
        res[:defs] << fq
        walk(node[2], nest, res)
        return
      end
    end
  when :command, :method_add_arg
    name = nil; args = nil
    if node[0] == :command && node[1].is_a?(Array) && node[1][0] == :@ident
      name = node[1][1]; args = node[2]
    elsif node[0] == :method_add_arg && node[1].is_a?(Array) && node[1][0] == :fcall && node[1][1].is_a?(Array) && node[1][1][0] == :@ident
      name = node[1][1][1]; args = node[2]
    end
    if name && REQ.include?(name) && args
      if name == "autoload"
        sym = nil; str = nil; stack = [args]
        until stack.empty?
          x = stack.pop; next unless x.is_a?(Array)
          if x[0] == :symbol_literal
            c = x.flatten.each_cons(2).find { |a, b| a == :@const }; sym = c[1] if c
          elsif x[0] == :@tstring_content then str ||= x[1]
          end
          x.each { |y| stack << y if y.is_a?(Array) }
        end
        res[:autoloads] << [(nest.empty? ? sym : nest.last + "::" + sym), str] if sym && str
      else
        strs, rel, dyn = strings_of(args)
        unless strs.empty?
          res[:reqs] << [name, (rel ? strs.join("/") : strs.join("")), rel, dyn]
        end
      end
    end
  when :var_ref, :const_path_ref, :top_const_ref
    p = path_of(node)
    if p
      res[:refs] << [p[0].join("::"), p[1], nest.dup]
      return
    end
  end
  node.each { |c| walk(c, nest, res) if c.is_a?(Array) }
end

ARGV.each do |f|
  src = File.read(File.join(root, f)) rescue next
  sexp = Ripper.sexp(src)
  next unless sexp
  res = { defs: [], refs: [], reqs: [], autoloads: [] }
  walk(sexp, [], res)
  out[f] = res
end
puts JSON.generate(out)
'''


def list_files(root, ext):
    out = []
    try:
        r = run_tool(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True)
        out = [l for l in r.stdout.splitlines() if l.endswith(ext) and os.path.isfile(os.path.join(root, l))]
    except Exception:
        for d, ds, fs in os.walk(root):
            ds[:] = [x for x in ds if x not in SKIP_DIRS]
            out += [os.path.relpath(os.path.join(d, f), root) for f in fs if f.endswith(ext)]
    return sorted(set(out))


def psr4_maps(root):
    maps = []
    try:
        c = json.load(open(os.path.join(root, "composer.json")))
    except Exception:
        return maps
    for key in ("autoload", "autoload-dev"):
        for pfx, dirs in c.get(key, {}).get("psr-4", {}).items():
            for d in ([dirs] if isinstance(dirs, str) else dirs):
                maps.append((pfx.rstrip("\\"), os.path.normpath(d)))
    return maps


def run_helper(cmd, name, code, root, files):
    os.makedirs(W, exist_ok=True)
    hp = os.path.join(W, name)
    open(hp, "w").write(code)
    data = {}
    for i in range(0, len(files), 200):
        r = run_tool([cmd, hp, root] + files[i:i + 200], capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout:
            sys.exit(cmd + " helper failed: " + r.stderr[:500])
        data.update(json.loads(r.stdout))
    return data


def php_graph(root, files):
    data = run_helper("php", "names.php", PHP_HELPER, root, files)
    fs = set(files)
    decl = collections.defaultdict(set)
    for f, d in data.items():
        for c in d["decls"]:
            decl[c].add(f)
    maps = psr4_maps(root)
    lower = {x.lower(): x for x in fs}

    def lookup(fq):
        if fq in decl:
            return decl[fq]
        for pfx, d in maps:  # fallback: PSR-4 path for a name nobody declared
            p = pfx.lower()
            if fq.startswith(p + "\\"):
                rel = os.path.normpath(os.path.join(d, fq[len(p) + 1:].replace("\\", "/"))) + ".php"
                if rel.lower() in lower:
                    return {lower[rel.lower()]}
        return ()

    E = set()
    for f, d in data.items():
        for fq in d["imports"] + d["refs"]:
            for t in lookup(fq):
                E.add((f, t))
        fd = os.path.dirname(f)
        for inc in d["includes"]:
            if "<DIR>" in inc:
                cands = [os.path.normpath(inc.replace("<DIR>", fd))]
            else:
                cands = [os.path.normpath(os.path.join(fd, inc)), os.path.normpath(inc.lstrip("/"))]
            for p in cands:
                if p in fs:
                    E.add((f, p))
    return E


def ruby_graph(root, files):
    data = run_helper("ruby", "consts.rb", RB_HELPER, root, files)
    fs = set(files)
    lps = [p for p in ("lib", "test", "spec") if os.path.isdir(os.path.join(root, p))] + ["."]
    E = set()

    def res(base, spec):
        spec = spec if spec.endswith(".rb") else spec + ".rb"
        p = os.path.normpath(os.path.join(base, spec))
        return p if p in fs else None

    for f, d in data.items():
        fd = os.path.dirname(f)
        for kind, spec, rel, dyn in d["reqs"]:
            tgts = []
            if kind == "require_all":
                for lp in lps:
                    base = os.path.normpath(os.path.join(lp, spec))
                    hits = [p for p in files if os.path.dirname(p) == base]
                    if hits:
                        tgts = hits
                        break
            elif kind == "require_relative":
                tgts = [res(fd, spec)]
            elif rel:  # expand_path/join with __dir__ or __FILE__
                tgts = [res(fd, spec), res(os.path.dirname(fd), spec)]
            elif not dyn:
                tgts = [t for t in (res(lp, spec) for lp in lps) if t][:1]
            for t in tgts:
                if t:
                    E.add((f, t))
    core = set(run_tool(["ruby", "-e", "puts Object.constants"], capture_output=True, text=True).stdout.split())
    definers = collections.defaultdict(set)
    for f, d in data.items():
        for fq in d["defs"]:
            definers[fq].add(f)
    for f, d in data.items():
        for fq, path in d["autoloads"]:
            for lp in lps:
                t = res(lp, path)
                if t:
                    E.add((f, t))
                    definers[fq] = {t}  # explicit autoload binds the constant to that file
                    break

    def conv(fq):
        return "/".join(re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", x)).lower() for x in fq.split("::")) + ".rb"

    def pick(fq):
        ds = definers[fq]
        if len(ds) == 1:
            return next(iter(ds))
        c = conv(fq)
        m = [x for x in ds if x == c or x.endswith("/" + c)]
        return m[0] if len(m) == 1 else None

    for f, d in data.items():
        own = set(d["defs"])
        for ref, absolute, nest in d["refs"]:
            if ref in core and "::" not in ref:
                continue
            if absolute:
                cands = [ref]
            else:
                cands = []
                for entry in reversed(nest):
                    parts = entry.split("::")
                    for i in range(len(parts), 0, -1):
                        c = "::".join(parts[:i]) + "::" + ref
                        if c not in cands:
                            cands.append(c)
                cands.append(ref)
            for c in cands:
                if c in definers:
                    if c in own:
                        break
                    t = pick(c)
                    if t:
                        E.add((f, t))
                    break
    return E


def main():
    lang, repo, out = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3]
    ext = {"php": ".php", "ruby": ".rb"}[lang]
    files = list_files(repo, ext)
    E = php_graph(repo, files) if lang == "php" else ruby_graph(repo, files)
    fs = set(files)
    edges = sorted([f, t] for f, t in E if f != t and f in fs and t in fs)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump({"files": files, "edges": edges}, open(out, "w"), indent=0)
    print(os.path.basename(repo), "files", len(files), "edges", len(edges))


main()
