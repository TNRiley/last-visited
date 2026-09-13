/* Last Visited — all rendering. D is spliced in by 10_inject.py. */
(function () {
"use strict";

const C = D.corpus, B = D.buckets, A = D.archive, P = D.perma;
const det = B.live + B.soft + B.dead;
const nf = n => n == null ? "—" : n.toLocaleString("en-US");
const pc = (a, b, d) => b ? (100 * a / b).toFixed(d == null ? 1 : d) + "%" : "—";

/* ---------- text ---------- */
document.getElementById("dek").innerHTML =
  "Every web address the Supreme Court of the United States has cited in an opinion since " +
  "the first one in 1996 — <b>" + nf(C.citations) + " citations</b> across " + nf(C.cases) +
  " cases — fetched again and checked against the Internet Archive. <b>" + pc(B.live, det) +
  "</b> of the addresses that give a straight answer still resolve to what was cited. " +
  "The Court noticed before anyone made it a study: its own citation practice has changed " +
  "three times, and this term it started archiving every link it uses.";

const stripe = [
  [nf(C.citations), "URLs cited in " + nf(C.opinions) + " opinions since 1996"],
  [pc(B.live, det), "still resolve to the document that was cited"],
  [pc(B.dead + B.soft, det), "are gone, or answer from the site root instead"],
  [pc(A.deadArchived, A.deadTotal, 0), "of the dead ones survive in the Wayback Machine"]
];
document.getElementById("stripe").innerHTML = stripe.map(s =>
  '<div><div class="v">' + s[0] + '</div><div class="k">' + s[1] + "</div></div>").join("");
document.getElementById("stripe-note").innerHTML =
  nf(B.indet) + " further URLs are excluded from those shares: the host answered, but with a " +
  "bot wall, a paywall or a rate limit, which is not evidence either way.";

document.getElementById("lede1").innerHTML =
  "Each URL is placed in the year it was first cited, then checked today. The gradient is the " +
  "whole finding: citations from the late 2000s are almost entirely gone, and survival improves " +
  "steadily towards the present. That is what rot looks like — not a cliff, but an exposure " +
  "curve, where the longer an address has been in print the less likely it is to still answer.";

document.getElementById("note-ocr").innerHTML =
  "<b>Why the second view matters.</b> Everything before 2021 is OCR of the printed reporters, " +
  "and a scanning error produces an address that was never real — this corpus contains " +
  "<code>geodties.com</code> and <code>seareh_quotes</code>. Such a URL is dead for reasons that " +
  "have nothing to do with the web. Restricting to URLs the Internet Archive holds a capture of " +
  "proves the address as printed once existed, which removes most of that noise. The curve keeps " +
  "its shape either way, which is the point of showing both.";

document.getElementById("lede2").innerHTML =
  "Not every failure is the same failure, and the differences carry most of the meaning. " +
  "A 404 is an honest death. A host that no longer resolves at all means the publisher is gone, " +
  "not just the page. A redirect that lands on the site's front door is the quiet one — the " +
  "server answers 200, a naive checker scores it alive, and the cited document is nowhere.";

document.getElementById("note-ua").innerHTML =
  "<b>A correction this study had to make to itself.</b> " + nf(D.recheck.retried) + " URLs gave an " +
  "ambiguous answer on the first pass — including every one of the Court's own perma.cc links, which " +
  "returned 403. Changing the user-agent did nothing. The block is on the HTTP client itself: the " +
  "same links return 403 to Python and 200 to <code>curl</code> with byte-identical headers. " +
  "Re-fetching the ambiguous set through curl changed <b>" + nf(D.recheck.changed) + "</b> verdicts, " +
  "<b>" + nf(D.recheck.rescued) + "</b> of them from dead or blocked to alive. Left uncorrected, the " +
  "most interesting finding on this page would have been an artefact of the measuring instrument — " +
  "which is the failure mode a link-rot study is most exposed to, and the reason the indeterminate " +
  "category exists at all rather than being folded into the dead.";

document.getElementById("lede3").innerHTML =
  "The Internet Archive holds a capture of <b>" + pc(A.archived, A.urls) + "</b> of these addresses, " +
  "and captured <b>" + pc(A.near, A.urls) + "</b> of them within a year of the opinion that cited them. " +
  "That is the difference between a citation that has rotted and one that is unrecoverable.";

document.getElementById("lede4").innerHTML =
  "The Court has changed how it cites the web three times, and each change is visible in the text " +
  "of the opinions themselves.";

document.getElementById("note-perma").innerHTML =
  "<b>The newest convention is one term old.</b> perma.cc — built at Harvard's Library Innovation Lab " +
  "in direct response to research on this exact problem — appears <b>" + nf(P.cites) + " times</b> in " +
  "the current term's opinions, in the form <code>(archived at https://perma.cc/XXXX-XXXX)</code>, " +
  "and essentially never before it. It is now the single most-cited host in the corpus. Of its " +
  nf(P.urls) + " distinct links, <b>" + nf(P.live) + " of the " + nf(P.answered) +
  "</b> that gave a definite answer resolve" + (P.indet ? "; the other " + nf(P.indet) +
  " refused an automated client outright, which is counted as no answer rather than as dead" : "") + ".";

document.getElementById("lede5").innerHTML =
  "All " + nf(C.citations) + " citations, sorted by date. Filter by outcome, search by case, " +
  "justice, host or URL. Every row links to the address exactly as the Court printed it.";

/* ---------- canvas plumbing ---------- */
function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
function setup(cv) {
  const dpr = Math.min(devicePixelRatio || 1, 2);
  // The markup height is the CSS height. Read it once and pin it: assigning cv.height
  // below rewrites that same attribute, so reading it again on the next redraw would
  // double the canvas on every hover event until the browser gives up and paints white.
  const h = +(cv.dataset.h || (cv.dataset.h = cv.getAttribute("height")));
  cv.style.height = h + "px";
  const w = cv.clientWidth;
  cv.width = w * dpr; cv.height = h * dpr;
  const g = cv.getContext("2d");
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  return {g, w, h};
}
const MONO = '"IBM Plex Mono",monospace', SANS = '"Archivo",system-ui,sans-serif';
function gridlines(g, x0, x1, ticks, fmt) {
  g.strokeStyle = css("--line"); g.lineWidth = 1;
  g.fillStyle = css("--faint"); g.font = "11px " + MONO; g.textAlign = "right";
  ticks.forEach(t => {
    g.beginPath(); g.moveTo(x0, Math.round(t.y) + .5); g.lineTo(x1, Math.round(t.y) + .5); g.stroke();
    g.fillText(fmt(t.v), x0 - 8, t.y + 4);
  });
}

/* ---------- 01 decay ---------- */
const KEYS = [["live", "--good", "Still resolves"], ["soft", "--soft404", "Redirects to site root"],
              ["dead", "--dead", "Gone (404, or host vanished)"], ["indet", "--indet", "Host would not say"]];
document.getElementById("decay-legend").innerHTML = KEYS.map(k =>
  '<span><i class="sw" style="background:var(' + k[1] + ')"></i> ' + k[2] + "</span>").join("");
let decayMode = "all", decayHit = null;
const decayCv = document.getElementById("decay"), decayRead = document.getElementById("decay-read");

function decayRows() {
  if (decayMode === "all") return D.byYear.filter(r => r.n > 0);
  const m = {}; D.confYear.forEach(r => m[r.y] = r);
  return D.byYear.filter(r => m[r.y]).map(r => {
    const c = m[r.y];
    return {y: r.y, n: c.n, live: c.n - c.dead, soft: 0, dead: c.dead, indet: 0, cites: r.cites};
  });
}
function drawDecay() {
  const {g, w, h} = setup(decayCv);
  const rows = decayRows();
  const L = 40, R = 12, T = 16, B = 34;
  const bw = (w - L - R) / rows.length;
  gridlines(g, L, w - R, [0, 25, 50, 75, 100].map(v => ({v, y: h - B - (h - B - T) * v / 100})),
            v => v + "%");
  rows.forEach((r, i) => {
    const x = L + i * bw, pad = Math.min(2.5, bw * 0.14);
    let acc = 0;
    KEYS.forEach(k => {
      const v = r[k[0]]; if (!v) return;
      const y0 = h - B - (h - B - T) * (acc + v) / r.n;
      const y1 = h - B - (h - B - T) * acc / r.n;
      g.fillStyle = css(k[1]);
      g.globalAlpha = (decayHit == null || decayHit === i) ? 1 : .38;
      g.fillRect(x + pad, y0, bw - pad * 2, y1 - y0);
      g.globalAlpha = 1;
      acc += v;
    });
    if (r.y % 5 === 0 || rows.length < 14) {
      g.fillStyle = css("--faint"); g.font = "10px " + MONO; g.textAlign = "center";
      g.fillText("'" + String(r.y).slice(2), x + bw / 2, h - B + 15);
    }
  });
  g.fillStyle = css("--faint"); g.font = "10px " + MONO; g.textAlign = "center";
  g.fillText("year first cited", L + (w - L - R) / 2, h - 4);
  const r = decayHit != null ? rows[decayHit] : null;
  decayRead.innerHTML = r
    ? "<b>" + r.y + "</b> &nbsp; " + r.n + " urls &nbsp; still resolving <b>" +
      pc(r.live, r.n) + "</b> &nbsp; gone <b>" + pc(r.dead + r.soft, r.n) + "</b>"
    : (decayMode === "all"
        ? nf(C.urls) + " urls by year first cited; bars are shares within each year"
        : nf(D.confirmed.n) + " urls with a Wayback capture — dead here is dead for real");
}
decayCv.addEventListener("pointermove", e => {
  const rect = decayCv.getBoundingClientRect(), rows = decayRows();
  const L = 40, R = 12, bw = (rect.width - L - R) / rows.length;
  const i = Math.floor((e.clientX - rect.left - L) / bw);
  decayHit = (i >= 0 && i < rows.length) ? i : null;
  drawDecay();
});
decayCv.addEventListener("pointerleave", () => { decayHit = null; drawDecay(); });
function pills(on, off) {
  document.getElementById(on).setAttribute("aria-pressed", "true");
  document.getElementById(off).setAttribute("aria-pressed", "false");
}
document.getElementById("c-all").onclick = () => { decayMode = "all"; pills("c-all", "c-conf"); drawDecay(); };
document.getElementById("c-conf").onclick = () => { decayMode = "conf"; pills("c-conf", "c-all"); drawDecay(); };

/* ---------- 02 failure modes ---------- */
const FAILS = [
  ["ok", "Resolves at the cited path", "--good"],
  ["soft", "200, but redirected to the site root", "--soft404"],
  ["notfound", "404 or 410 — page gone", "--dead"],
  ["dns", "Host does not resolve — publisher gone", "--dead"],
  ["conn", "Connection refused or reset", "--dead"],
  ["timeout", "No response before timeout", "--dead"],
  ["server", "5xx server error", "--dead"],
  ["blocked", "401 / 403 / 429 — would not say", "--indet"],
  ["ssl", "Certificate invalid", "--indet"],
  ["other", "Other response", "--indet"]
];
function drawFail() {
  const cv = document.getElementById("fail"), {g, w, h} = setup(cv);
  const rows = FAILS.map(f => ({k: f[0], label: f[1], c: f[2], n: D.states[f[0]] || 0}))
                    .filter(r => r.n > 0);
  const L = 8, R = 58, T = 10, B = 8;
  const bh = (h - T - B) / rows.length;
  const max = Math.max.apply(null, rows.map(r => r.n));
  rows.forEach((r, i) => {
    const y = T + i * bh;
    g.fillStyle = css(r.c); g.globalAlpha = .9;
    g.fillRect(L, y + bh * 0.34, (w - L - R) * r.n / max, bh * 0.40);
    g.globalAlpha = 1;
    g.fillStyle = css("--ink"); g.font = "11.5px " + SANS; g.textAlign = "left";
    g.fillText(r.label, L + 2, y + bh * 0.26);
    g.fillStyle = css("--muted"); g.font = "11px " + MONO; g.textAlign = "left";
    g.fillText(nf(r.n) + "  " + pc(r.n, C.urls, 0), L + (w - L - R) * r.n / max + 8, y + bh * 0.62);
  });
  document.getElementById("fail-read").innerHTML =
    "Of " + nf(C.urls) + " distinct URLs. Host-gone (<b>" + nf(D.states.dns || 0) +
    "</b>) is the hardest failure: nothing at that domain answers at all.";
}

/* ---------- 03 archive ---------- */
function drawArch() {
  const cv = document.getElementById("arch"), {g, w, h} = setup(cv);
  const bars = [
    {label: "All cited URLs", parts: [
      {n: A.archived, c: "--accent", t: "in the Wayback Machine"},
      {n: A.urls - A.archived, c: "--line-2", t: "never archived"}], tot: A.urls},
    {label: "Only the dead ones", parts: [
      {n: A.deadArchived, c: "--accent", t: "recoverable from the archive"},
      {n: A.deadNever, c: "--dead", t: "gone with no copy anywhere"}], tot: A.deadTotal}
  ];
  const L = 8, R = 8, T = 16, B = 10, gap = 30;
  const bh = (h - T - B - gap) / bars.length;
  bars.forEach((b, i) => {
    const y = T + i * (bh + gap);
    g.fillStyle = css("--ink"); g.font = "600 12.5px " + SANS; g.textAlign = "left";
    g.fillText(b.label, L, y + 2);
    let x = L;
    b.parts.forEach(p => {
      const pw = (w - L - R) * p.n / b.tot;
      g.fillStyle = css(p.c); g.globalAlpha = .92;
      g.fillRect(x, y + 12, pw, bh * 0.42); g.globalAlpha = 1;
      if (pw > 74) {
        g.fillStyle = css("--paper"); g.font = "600 11px " + MONO; g.textAlign = "left";
        g.fillText(pc(p.n, b.tot, 0), x + 8, y + 12 + bh * 0.27);
      }
      x += pw;
    });
    g.fillStyle = css("--muted"); g.font = "11px " + SANS; g.textAlign = "left";
    g.fillText(b.parts.map(p => nf(p.n) + " " + p.t).join("   ·   "), L, y + 12 + bh * 0.42 + 15);
  });
  document.getElementById("arch-read").innerHTML =
    "A capture also proves the address was real, which is how OCR damage is separated from rot.";
}

/* ---------- 04 citation practice ---------- */
const PKEYS = [["visited", "--accent", "States a visitation date"],
               ["clerk", "--soft404", "Copy filed with the Clerk of Court"],
               ["perma", "--good", "Archived at perma.cc"]];
document.getElementById("practice-legend").innerHTML = PKEYS.map(k =>
  '<span><i class="sw" style="background:var(' + k[1] + ')"></i> ' + k[2] + "</span>").join("");
let pracHit = null;
const pracCv = document.getElementById("practice");

function drawPractice() {
  const {g, w, h} = setup(pracCv);
  const rows = D.practice.filter(r => r.n > 0);
  const L = 40, R = 12, T = 16, B = 34;
  const bw = (w - L - R) / rows.length;
  gridlines(g, L, w - R, [0, 25, 50, 75, 100].map(v => ({v, y: h - B - (h - B - T) * v / 100})),
            v => v + "%");
  rows.forEach((r, i) => {
    const x = L + i * bw, sub = (bw - 4) / PKEYS.length;
    PKEYS.forEach((k, j) => {
      const share = r.n ? r[k[0]] / r.n : 0;
      if (!share) return;
      const bh = (h - B - T) * share;
      g.fillStyle = css(k[1]);
      g.globalAlpha = (pracHit == null || pracHit === i) ? .92 : .34;
      g.fillRect(x + 2 + j * sub, h - B - bh, Math.max(1, sub - 1), bh);
      g.globalAlpha = 1;
    });
    if (r.y % 5 === 0) {
      g.fillStyle = css("--faint"); g.font = "10px " + MONO; g.textAlign = "center";
      g.fillText("'" + String(r.y).slice(2), x + bw / 2, h - B + 15);
    }
  });
  g.fillStyle = css("--faint"); g.font = "10px " + MONO; g.textAlign = "center";
  g.fillText("share of that year's citations", L + (w - L - R) / 2, h - 4);
  const r = pracHit != null ? rows[pracHit] : null;
  document.getElementById("practice-read").innerHTML = r
    ? "<b>" + r.y + "</b> &nbsp; " + r.n + " citations &nbsp; visitation date <b>" + pc(r.visited, r.n, 0) +
      "</b> &nbsp; clerk's file <b>" + pc(r.clerk, r.n, 0) + "</b> &nbsp; perma.cc <b>" + pc(r.perma, r.n, 0) + "</b>"
    : "Hover a year. The three conventions barely overlap — each replaced the last.";
}
pracCv.addEventListener("pointermove", e => {
  const rect = pracCv.getBoundingClientRect(), rows = D.practice.filter(r => r.n > 0);
  const L = 40, R = 12, bw = (rect.width - L - R) / rows.length;
  const i = Math.floor((e.clientX - rect.left - L) / bw);
  pracHit = (i >= 0 && i < rows.length) ? i : null;
  drawPractice();
});
pracCv.addEventListener("pointerleave", () => { pracHit = null; drawPractice(); });

/* ---------- 05 table ---------- */
const SI = D.stateIndex;
const GROUP = {ok: "live", soft: "soft", notfound: "dead", dns: "dead", conn: "dead",
               timeout: "dead", server: "dead", blocked: "indet", ssl: "indet", other: "indet"};
const LABEL = {live: "resolves", soft: "root only", dead: "gone", indet: "no answer"};
const FILTERS = [["", "All"], ["dead", "Gone"], ["live", "Still up"], ["soft", "Root only"],
                 ["indet", "No answer"], ["perma", "perma.cc"]];
let filter = "", query = "";
document.getElementById("filters").innerHTML = FILTERS.map(f =>
  '<button class="pill" data-f="' + f[0] + '" aria-pressed="' + (f[0] === "" ? "true" : "false") +
  '">' + f[1] + "</button>").join("");
document.getElementById("filters").querySelectorAll("button").forEach(b => b.onclick = () => {
  filter = b.dataset.f;
  document.getElementById("filters").querySelectorAll("button").forEach(o =>
    o.setAttribute("aria-pressed", o.dataset.f === filter ? "true" : "false"));
  renderTable();
});
const hay = D.rows.map(r => (r[0] + " " + r[2] + " " + r[5] + " " + r[3]).toLowerCase());
document.getElementById("q").addEventListener("input", e => {
  query = e.target.value.trim().toLowerCase(); renderTable();
});

const CAP = 400;                                  // the DOM, not the filter, is the limit
function renderTable() {
  const out = [];
  let shown = 0;
  for (let i = 0; i < D.rows.length; i++) {
    const r = D.rows[i], st = r[6] >= 0 ? SI[r[6]] : null, gp = st ? GROUP[st] : "indet";
    if (filter === "perma") { if (r[0].indexOf("perma.cc") < 0) continue; }
    else if (filter && gp !== filter) continue;
    if (query && hay[i].indexOf(query) < 0) continue;
    shown++;
    if (out.length < CAP) out.push([r, st, gp]);
  }
  document.getElementById("tblcount").innerHTML =
    nf(shown) + " citations" + (shown > out.length ? " — showing the first " + nf(out.length) : "");
  document.getElementById("tbl").innerHTML =
    "<thead><tr><th>Case</th><th>Cited</th><th>Status</th><th>Archive</th></tr></thead><tbody>" +
    out.map(([r, st, gp]) =>
      "<tr><td>" + esc(r[2]) + '<span class="u">' + esc(r[0]) + "</span></td>" +
      '<td class="mono">' + r[1] + "<br><span style='color:var(--faint)'>" + esc(r[4]) +
      (r[5] ? " · " + esc(r[5]) : "") + "</span></td>" +
      '<td><span class="tag t-' + gp + '">' + LABEL[gp] + "</span>" +
      (st && st !== "ok" ? "<br><span style='color:var(--faint);font-size:10.5px'>" + st + "</span>" : "") +
      "</td>" +
      '<td class="arch">' + (r[7] === 2 ? "captured near citation" : r[7] === 1 ? "captured later" : "—") +
      "</td></tr>").join("") + "</tbody>";
}
function esc(s) {
  return String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
}

/* ---------- methods + footer ---------- */
document.getElementById("methods").innerHTML =
  "<h4>Corpus</h4><p>Two sources, because no single one spans the period. " + nf(C.capCases) +
  " cases from the Caselaw Access Project's bulk volumes (U.S. Reports 500–572, 1991–2014; " +
  "Supreme Court Reporter 134–140, 2014–2020), which is OCR of the printed reporters; and " +
  nf(C.slipPdfs) + " born-digital slip opinion PDFs from supremecourt.gov for OT2020–OT2025, " +
  "which the site serves only for recent terms. Opinions printed in both reporters are " +
  "de-duplicated on case, date, opinion type and URL.</p>" +

  "<h4>Extraction</h4><p>Print breaks long URLs across lines. In the scanned volumes the break " +
  "survives as a plain space (<code>http://www.txdmv. gov/motorists</code>) and a " +
  "whitespace-terminated pattern truncates the address; in the PDFs it is a real newline, and " +
  "<code>pdftotext</code>'s default mode deletes a hyphen at a line end as if it were hyphenation, " +
  "which corrupts any URL that legitimately ends a line with one — so <code>-layout</code> is used. " +
  "Fragments are rejoined only where a typesetter would actually break, and the continuation has to " +
  "look like a host, a path, or an opaque archive code. One perma.cc link could not be recovered: " +
  "its code is split across a page boundary with the running header in between.</p>" +

  "<h4>What a verdict means</h4><p><b>Resolves</b> is 2xx at the path that was cited. " +
  "<b>Root only</b> is 2xx after a redirect that threw the path away — the site lives, the document " +
  "does not, and counting these as alive is the standard way link-rot studies overstate survival. " +
  "<b>Gone</b> is 404/410, a host that no longer resolves, or a connection that fails. " +
  "<b>No answer</b> is 401/403/429 and certificate failures: the server refused to say, and these " +
  "are excluded from every percentage rather than guessed at.</p>" +

  "<h4>The instrument had to be corrected</h4><p>" + nf(D.recheck.retried) + " URLs answered " +
  "ambiguously on the first pass, including all of the Court's perma.cc links. The cause was not " +
  "the user-agent but the HTTP client: those links return 403 to python-requests and 200 to " +
  "<code>curl</code> with identical headers. Re-fetching through curl changed " + nf(D.recheck.changed) +
  " verdicts. Only ambiguous states were retried — a 404 is a 404 whoever asks. perma.cc also " +
  "rate-limits, and refuses intermittently under load, so its links get a separate serial pass with " +
  "three attempts each; a 403 surviving all three is still recorded as no answer, never as dead.</p>" +

  "<h4>OCR is the confound, and it is bounded</h4><p>A mis-scanned address is dead for reasons that " +
  "have nothing to do with link rot. Every URL is therefore also looked up in the Internet Archive: " +
  "a capture proves the address as printed once existed. The second view in section 01 restricts to " +
  "those " + nf(D.confirmed.n) + " URLs. It is a conservative floor, not a correction — a real URL " +
  "too obscure ever to be crawled is excluded from it too.</p>" +

  "<h4>What this cannot tell you</h4><p>It cannot see content drift: a URL that still resolves may " +
  "serve something entirely different from what the Justice read, and that is invisible to a status " +
  "code. Counts are of addresses, not of how load-bearing each was — a citation in a footnote and " +
  "one carrying a holding weigh the same here. The slip-opinion corpus covers only the terms " +
  "supremecourt.gov currently serves, so OT2015–OT2019 rests on the Supreme Court Reporter alone. " +
  "And a liveness check is a snapshot: these figures describe " + D.generated + ", not a stable fact.</p>";

document.getElementById("foot").innerHTML =
  "Sources: <a href='https://case.law/'>Caselaw Access Project</a> bulk data (CC0) · " +
  "<a href='https://www.supremecourt.gov/opinions/slipopinion/25'>supremecourt.gov slip opinions</a> " +
  "(US Government work, public domain) · liveness checked against the live web and the " +
  "<a href='https://archive.org/help/wayback_api.php'>Internet Archive Wayback API</a>. " +
  "Checked " + D.generated + " · " + nf(C.citations) + " citations · " + nf(C.urls) + " distinct URLs. " +
  "<a href='https://github.com/TNRiley/last-visited'>Source and rebuild instructions</a>.";

/* ---------- boot ---------- */
function redraw() { drawDecay(); drawFail(); drawArch(); drawPractice(); }
document.getElementById("theme").onclick = () => {
  const cur = document.documentElement.getAttribute("data-theme");
  const dark = cur ? cur === "dark" : matchMedia("(prefers-color-scheme:dark)").matches;
  document.documentElement.setAttribute("data-theme", dark ? "light" : "dark");
  redraw();
};
matchMedia("(prefers-color-scheme:dark)").addEventListener("change", redraw);
let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(redraw, 120); });
renderTable();
redraw();
})();
