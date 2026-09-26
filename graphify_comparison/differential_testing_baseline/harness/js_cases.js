// Differential-testing harness for JS real_bug_fix cases 005-008.

const results = [];

// --- 005: axios-progress-negative-clamp ---
function computeLoaded_old(rawLoaded, total) {
  return Math.max(0, total != null ? Math.min(rawLoaded, total) : rawLoaded);
}
function computeLoaded_new(rawLoaded, total) {
  return total != null ? Math.min(rawLoaded, total) : rawLoaded;
}
function run005() {
  for (const [raw, total] of [[-500, undefined], [-1, 1000], [100, 1000]]) {
    const o = computeLoaded_old(raw, total), n = computeLoaded_new(raw, total);
    if (o !== n) return ["DIVERGED", `rawLoaded=${raw} total=${total} old=${o} new=${n}`];
  }
  return ["IDENTICAL", ""];
}
results.push(["005-axios-progress-negative-clamp", ...run005()]);

// --- 006: express-content-length-transfer-encoding ---
// `this.get(header)` stub: returns a header value or undefined.
function computeLen_old(chunk, hasTransferEncoding) {
  let len;
  if (chunk !== undefined && !hasTransferEncoding) {
    len = Buffer.isBuffer(chunk) ? chunk.length : Buffer.byteLength(String(chunk));
  }
  return len;
}
function computeLen_new(chunk, hasTransferEncoding) {
  let len;
  if (chunk !== undefined) {
    len = Buffer.isBuffer(chunk) ? chunk.length : Buffer.byteLength(String(chunk));
  }
  return len;
}
function run006() {
  for (const [chunk, hasTE] of [["hello", true], ["hello", false], [undefined, true]]) {
    const o = computeLen_old(chunk, hasTE), n = computeLen_new(chunk, hasTE);
    if (o !== n) return ["DIVERGED", `chunk=${JSON.stringify(chunk)} Transfer-Encoding-present=${hasTE} old=${o} new=${n}`];
  }
  return ["IDENTICAL", ""];
}
results.push(["006-express-content-length-transfer-encoding", ...run006()]);

// --- 007: lodash-omit-array-clone ---
function isPlainObject(v) {
  return typeof v === "object" && v !== null && !Array.isArray(v) && Object.getPrototypeOf(v) === Object.prototype;
}
function customOmitClone_old(value) {
  return isPlainObject(value) || Array.isArray(value) ? undefined : value;
}
function customOmitClone_new(value) {
  return isPlainObject(value) ? undefined : value;
}
function run007() {
  for (const value of [[1, 2, 3], { a: 1 }, "str", 42, null]) {
    const o = customOmitClone_old(value), n = customOmitClone_new(value);
    if (o !== n) return ["DIVERGED", `value=${JSON.stringify(value)} old=${o} new=${JSON.stringify(n)}`];
  }
  return ["IDENTICAL", ""];
}
results.push(["007-lodash-omit-array-clone", ...run007()]);

// --- 008: axios-headers-set-cookie ---
function isArray(v) { return Array.isArray(v); }
function getSetCookie_old(value) {
  return isArray(value) ? value : (value == null || value === false) ? [] : [value];
}
function getSetCookie_new(value) {
  return value || [];
}
function run008() {
  for (const value of ["sid=abc123; Path=/", 0, "", false, null, ["a=1", "b=2"]]) {
    const o = getSetCookie_old(value), n = getSetCookie_new(value);
    if (JSON.stringify(o) !== JSON.stringify(n)) {
      return ["DIVERGED", `value=${JSON.stringify(value)} old=${JSON.stringify(o)} new=${JSON.stringify(n)}`];
    }
  }
  return ["IDENTICAL", ""];
}
results.push(["008-axios-headers-set-cookie", ...run008()]);

console.log(`${"case".padEnd(40)} ${"result".padEnd(10)} detail`);
console.log("-".repeat(100));
for (const [c, status, detail] of results) {
  console.log(`${c.padEnd(40)} ${status.padEnd(10)} ${detail}`);
}
