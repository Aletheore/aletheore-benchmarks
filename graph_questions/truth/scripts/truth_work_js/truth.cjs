// usage: node truth.cjs <repoCopy> <out.json>
const ts = require('typescript');
const fs = require('fs'), path = require('path'), cp = require('child_process');
const root = path.resolve(process.argv[2]);
const files = cp.execFileSync('git', ['-C', root, 'ls-files'], { encoding: 'utf8', maxBuffer: 1e8 }).split('\n').filter(Boolean);
const SRC = /\.(js|jsx|mjs|cjs|ts|tsx|mts|cts)$/;
const src = files.filter(f => SRC.test(f));
const srcSet = new Set(src);
const fileSet = new Set(files);
// tsconfig
let opts = { allowJs: true, checkJs: false, module: ts.ModuleKind.NodeNext, moduleResolution: ts.ModuleResolutionKind.NodeNext, resolveJsonModule: true };
const cfgPath = path.join(root, 'tsconfig.json');
if (fs.existsSync(cfgPath)) {
  const c = ts.readConfigFile(cfgPath, ts.sys.readFile);
  const p = ts.parseJsonConfigFileContent(c.config, ts.sys, root);
  opts = Object.assign({}, p.options, { allowJs: true, noEmit: true });
}
// workspace packages
const pkgs = {};
for (const f of files) if (/(^|\/)package\.json$/.test(f)) {
  try { const j = JSON.parse(fs.readFileSync(path.join(root, f), 'utf8')); if (j.name) pkgs[j.name] = { dir: path.dirname(f) === '.' ? '' : path.dirname(f), json: j }; } catch (e) {}
}
const CONDS = ['@zod/source', 'import', 'node', 'default', 'require', 'types'];
function pickCond(t) {
  if (typeof t === 'string') return t;
  if (Array.isArray(t)) { for (const x of t) { const r = pickCond(x); if (r) return r; } return null; }
  if (t && typeof t === 'object') { for (const c of CONDS) if (c in t) { const r = pickCond(t[c]); if (r) return r; } }
  return null;
}
function resolveWorkspace(spec) {
  let best = null;
  for (const n of Object.keys(pkgs)) if (spec === n || spec.startsWith(n + '/')) if (!best || n.length > best.length) best = n;
  if (!best) return null;
  const pk = pkgs[best]; const sub = '.' + spec.slice(best.length);
  let target = null;
  const ex = pk.json.exports;
  if (ex) {
    const map = (typeof ex === 'string' || Array.isArray(ex) || Object.keys(ex).every(k => !k.startsWith('.'))) ? { '.': ex } : ex;
    if (map[sub] !== undefined) target = pickCond(map[sub]);
    else for (const k of Object.keys(map)) if (k.endsWith('*') && sub.startsWith(k.slice(0, -1))) { const t = pickCond(map[k]); if (t) target = t.replace('*', sub.slice(k.length - 1)); break; }
  } else if (sub === '.') target = pk.json.main || 'index.js';
  else target = sub;
  if (!target) return null;
  let rel = path.posix.normalize(path.posix.join(pk.dir, target));
  const cands = [rel, rel + '.ts', rel + '.js', rel + '/index.ts', rel + '/index.js', rel.replace(/\.js$/, '.ts'), rel.replace(/\.cjs$/, '.cts'), rel.replace(/\.mjs$/, '.mts')];
  for (const c of cands) if (srcSet.has(c)) return c;
  return null;
}
const host = ts.sys;
const optCache = {};
function optsFor(from) {
  let d = path.dirname(from);
  while (true) {
    const cfg = path.join(root, d, 'tsconfig.json');
    if (fs.existsSync(cfg)) {
      if (!optCache[cfg]) {
        const c = ts.readConfigFile(cfg, ts.sys.readFile);
        const p = ts.parseJsonConfigFileContent(c.config, ts.sys, path.dirname(cfg));
        optCache[cfg] = Object.assign({}, p.options, { allowJs: true, noEmit: true });
      }
      return optCache[cfg];
    }
    if (d === '.' || d === '') return opts;
    d = path.dirname(d);
  }
}
const cache = ts.createModuleResolutionCache(root, x => x, opts);
function resolve(spec, from) {
  const rel = spec.startsWith('.') || spec.startsWith('/');
  if (rel) { const ex = path.posix.normalize(path.posix.join(path.posix.dirname(from), spec)); if (srcSet.has(ex) && !/\.d\.[cm]?ts$/.test(ex)) return ex; }
  if (!rel) { const w0 = resolveWorkspace(spec); if (w0) return w0; }
  const r = ts.resolveModuleName(spec, path.join(root, from), optsFor(from), host, cache).resolvedModule;
  if (r && !r.isExternalLibraryImport) {
    const rp = path.relative(root, r.resolvedFileName);
    if (!rp.startsWith('..') && !rp.includes('node_modules')) {
      if (srcSet.has(rp)) return rp;
      // d.ts that corresponds to a source? keep as-is if tracked
      return undefined; // asset (css/json/png...): not an import-graph target
    }
  }
  if (rel) {
    // fallback: manual (extension swap, index, stripped ext)
    const base = path.posix.normalize(path.posix.join(path.posix.dirname(from), spec));
    const alt = [base, base.replace(/\.(m|c)?js$/, '.$1ts'.replace('$1', '$1')), base.replace(/\.js$/, '.ts'), base.replace(/\.js$/, '.tsx'), base + '.js', base + '.ts', base + '.mjs', base + '.cjs', base + '/index.js', base + '/index.ts'];
    for (const c of alt) if (srcSet.has(c)) return c;
    return undefined;
  }
  const w = resolveWorkspace(spec);
  return w || null; // null = external
}
const edges = []; const unresolved = [];
function kindOf(k) { return k; }
for (const f of src) {
  let text; try { text = fs.readFileSync(path.join(root, f), 'utf8'); } catch (e) { continue; }
  const sf = ts.createSourceFile(f, text, ts.ScriptTarget.Latest, true, /\.(tsx|jsx)$/.test(f) ? ts.ScriptKind.TSX : undefined);
  const add = (spec, kind, typeOnly) => {
    const r = resolve(spec, f);
    if (r === undefined) unresolved.push({ from: f, spec, kind });
    else if (r === null) { /* external */ }
    else edges.push({ from: f, to: r, kind, typeOnly: !!typeOnly, spec });
  };
  const visit = n => {
    if (ts.isImportDeclaration(n) && ts.isStringLiteral(n.moduleSpecifier)) {
      const ic = n.importClause; const typeOnly = !!(ic && ic.isTypeOnly);
      add(n.moduleSpecifier.text, ic ? (typeOnly ? 'import-type' : 'import') : 'side-effect', typeOnly);
    } else if (ts.isExportDeclaration(n) && n.moduleSpecifier && ts.isStringLiteral(n.moduleSpecifier)) {
      add(n.moduleSpecifier.text, n.exportClause ? 'export-from' : 'export-star', n.isTypeOnly);
    } else if (ts.isImportEqualsDeclaration(n) && ts.isExternalModuleReference(n.moduleReference) && ts.isStringLiteral(n.moduleReference.expression)) {
      add(n.moduleReference.expression.text, 'require', n.isTypeOnly);
    } else if (ts.isCallExpression(n)) {
      const e = n.expression;
      if (ts.isIdentifier(e) && e.text === 'require' && n.arguments.length === 1 && ts.isStringLiteralLike(n.arguments[0])) add(n.arguments[0].text, 'require');
      else if (e.kind === ts.SyntaxKind.ImportKeyword && n.arguments.length >= 1 && ts.isStringLiteralLike(n.arguments[0])) add(n.arguments[0].text, 'dynamic');
    } else if (ts.isImportTypeNode(n) && ts.isLiteralTypeNode(n.argument) && ts.isStringLiteral(n.argument.literal)) {
      add(n.argument.literal.text, 'import-type-node', true);
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
}
fs.writeFileSync(process.argv[3], JSON.stringify({ src, edges, unresolved }));
console.log('src', src.length, 'edges', edges.length, 'unresolved', unresolved.length);
