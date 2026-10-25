<?php
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
