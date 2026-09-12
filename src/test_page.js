/* Run the built page's script against a stub DOM, and assert the figures its
 * prose commits to. There is no browser in the build environment, so this is the
 * check that the page actually executes.
 *
 *     node test_page.js
 */
const fs = require("fs"), path = require("path"), assert = require("assert");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const m = html.match(/<script>\n([\s\S]*?)\n<\/script>/);
assert(m, "no inline script found in index.html");
const code = m[1];

const nanGuard = new Set(["fillRect", "moveTo", "lineTo", "arc", "fillText", "strokeRect"]);
function ctx2d() {
  const noop = () => {};
  return new Proxy({}, {
    get(t, k) {
      if (k === "measureText") return () => ({width: 10});
      if (k === "setTransform") return noop;
      if (nanGuard.has(k)) return (...a) => {
        for (const v of a) if (typeof v === "number" && !Number.isFinite(v))
          throw new Error("non-finite coordinate in " + k + ": " + JSON.stringify(a));
      };
      if (typeof k === "string" &&
          /^(begin|close|stroke|fill|save|restore|clear|clip|rect|translate|rotate|scale|setLineDash|createLinearGradient)/.test(k))
        return k === "createLinearGradient" ? () => ({addColorStop: noop}) : noop;
      return t[k];
    },
    set(t, k, v) { t[k] = v; return true; }
  });
}
let elements = {};
function mkEl(id) {
  const L = {};
  const el = {
    id, innerHTML: "", value: "", hidden: false, clientWidth: 880, dataset: {}, style: {},
    getAttribute: k => el["_" + k] != null ? el["_" + k] : (k === "height" ? "300" : null),
    setAttribute: (k, v) => { el["_" + k] = v; },
    addEventListener: (k, fn) => { (L[k] = L[k] || []).push(fn); },
    getContext: () => ctx2d(),
    getBoundingClientRect: () => ({left: 0, top: 0, width: 880, height: 300}),
    querySelectorAll: () => [0, 1, 2].map(i => {
      const c = mkEl(id + "-" + i);
      c.dataset = {f: ["", "dead", "live"][i]};
      return c;
    }),
    fire: (k, ev) => (L[k] || []).forEach(fn => fn(ev))
  };
  return el;
}
function get(id) { return elements[id] || (elements[id] = mkEl(id)); }
global.document = {
  getElementById: get,
  documentElement: {
    _a: {}, getAttribute(k) { return this._a[k] || null; }, setAttribute(k, v) { this._a[k] = v; }
  }
};
global.getComputedStyle = () => ({getPropertyValue: () => "#888888"});
global.matchMedia = () => ({matches: false, addEventListener: () => {}});
global.devicePixelRatio = 2;
global.addEventListener = () => {};
global.setTimeout = fn => fn && fn();
global.clearTimeout = () => {};

new Function(code)();
console.log("page script executed with no exception");

const D = JSON.parse(html.match(/const D = (\{[\s\S]*?\});\n/)[1]);
const B = D.buckets, A = D.archive, C = D.corpus;
const det = B.live + B.soft + B.dead;

function ok(cond, what) { assert(cond, "FAILED: " + what); console.log("  ok  " + what); }

console.log("\ncorpus:");
ok(C.citations > 1300 && C.citations < 1500, "citations in range (" + C.citations + ")");
ok(C.urls > 1250, "distinct urls (" + C.urls + ")");
ok(C.y0 === 1996, "first citation year is 1996");
ok(C.cases > 400, "cases (" + C.cases + ")");

console.log("\nbuckets partition the corpus:");
ok(B.live + B.soft + B.dead + B.indet === C.urls, "buckets sum to url count");
ok(D.byYear.reduce((s, r) => s + r.n, 0) === C.urls, "byYear sums to url count");

console.log("\nheadline claims:");
const liveShare = 100 * B.live / det;
ok(liveShare > 25 && liveShare < 60, "live share plausible (" + liveShare.toFixed(1) + "%)");
ok(B.dead > B.live, "more dead than live — the finding the page leads with");
ok(A.deadArchived + A.deadNever === A.deadTotal, "dead urls split cleanly by archive status");
ok(A.archived <= A.urls && A.near <= A.archived, "archive counts are nested correctly");

console.log("\nrot increases with age:");
const early = D.byYear.filter(r => r.y >= 2003 && r.y <= 2012 && r.n > 5);
const late  = D.byYear.filter(r => r.y >= 2018 && r.y <= 2024 && r.n > 5);
const share = rs => {
  const n = rs.reduce((s, r) => s + r.live + r.soft + r.dead, 0);
  const l = rs.reduce((s, r) => s + r.live, 0);
  return 100 * l / n;
};
const se = share(early), sl = share(late);
ok(sl > se + 15, "recent citations survive far better (" + se.toFixed(0) + "% vs " + sl.toFixed(0) + "%)");

console.log("\nperma.cc is a current-term phenomenon:");
const py = D.perma.byYear, recent = (py[2025] || 0) + (py[2026] || 0);
const older = Object.keys(py).filter(y => +y < 2025).reduce((s, y) => s + py[y], 0);
ok(D.perma.cites > 50, "perma citations (" + D.perma.cites + ")");
ok(recent > older * 10, "concentrated in 2025-26 (" + recent + " vs " + older + " before)");
ok(D.perma.live > D.perma.answered * 0.8,
   "and they resolve: " + D.perma.live + "/" + D.perma.answered +
   " of those giving a definite answer (" + D.perma.indet + " refused a bot)");

console.log("\ntable + interaction paths:");
get("decay").fire("pointermove", {clientX: 400});
get("practice").fire("pointermove", {clientX: 400});
const q = get("q");
q.value = "census";
q.fire("input", {target: {value: "census"}});
ok(/census/i.test(get("tbl").innerHTML), "search filters the citation table");
ok(D.rows.length === C.citations, "one table row per citation");

console.log("\nALL CHECKS PASSED");
