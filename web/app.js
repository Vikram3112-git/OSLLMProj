/* OSLLM web interface. No build step and no frameworks: plain JS talking to server.py. */
"use strict";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const S = { status: null, student: localStorage.getItem("osllm.student") || "", 
            history: [], busy: false, topic: null, level: "medium", chatId: null, unit: 0 };

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) n.append(kid.nodeType ? kid : String(kid));
  return n;
}
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (x) => `${Math.round((x || 0) * 100)}%`;
const fmt = (x) => (Number.isInteger(x) ? String(x) : Number(x).toFixed(2));
const vec = (v) => (v || []).join(" ");
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch { return false; } },
};

async function api(path, body, method) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 25000);
  const opt = body
    ? { method: method || "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: controller.signal }
    : { method: method || "GET", signal: controller.signal };
  try {
    const r = await fetch(path, opt);
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || `Request failed (${r.status})`);
    return data;
  } catch (e) {
    if (e.name === "AbortError") throw new Error("This request took too long. Check that OSLLM is still running, then try again.");
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

async function streamApi(path, body, on, signal) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal });
  if (!r.ok || !r.body) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || `Request failed (${r.status})`); }
  const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const lineText = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
      if (lineText) { try { on(JSON.parse(lineText)); } catch (e) { console.warn(e); } }
    }
  }
}

/* ------------------------------------------------------------------ smooth streaming */
// Re-rendering Markdown on every token makes long answers lag; render at most once per frame instead.
function renderer(target, title) {
  let text = "", queued = false;
  const paint = () => {
    queued = false;
    let t = text;
    if (title) t = t.replace(new RegExp("^\\s*#{1,4}\\s*" + title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s*\\n", "i"), "");
    target.innerHTML = md(t);
  };
  return {
    add(piece) { text += piece; if (!queued) { queued = true; requestAnimationFrame(paint); } },
    flush() { paint(); },
    get text() { return text; },
  };
}

/* ------------------------------------------------------------------ markdown (small, offline) */
function inline(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\s][^*]*?)\*(?!\*)/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}
function md(src) {
  const lines = String(src || "").replace(/\r/g, "").split("\n");
  let out = "", i = 0;
  while (i < lines.length) {
    const ln = lines[i];
    if (/^```/.test(ln)) {
      const code = []; i++;
      while (i < lines.length && !/^```/.test(lines[i])) code.push(lines[i++]);
      i++; out += `<pre><code>${esc(code.join("\n"))}</code></pre>`; continue;
    }
    const h = ln.match(/^(#{1,4})\s+(.*)$/);
    if (h) { const lv = Math.min(4, Math.max(2, h[1].length)); out += `<h${lv}>${inline(h[2])}</h${lv}>`; i++; continue; }
    if (/^\s*\|.*\|\s*$/.test(ln) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
      const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const head = cells(ln); i += 2; const rows = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) rows.push(cells(lines[i++]));
      out += `<div class="table-wrap"><table><thead><tr>${head.map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead><tbody>${
        rows.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
      continue;
    }
    if (/^\s*([-*+]|\d+[.)])\s+/.test(ln)) {
      const ordered = /^\s*\d/.test(ln); const items = [];
      while (i < lines.length && /^\s*([-*+]|\d+[.)])\s+/.test(lines[i])) {
        let item = lines[i++].replace(/^\s*([-*+]|\d+[.)])\s+/, "");
        while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*([-*+]|\d+[.)])\s+/.test(lines[i])) item += " " + lines[i++].trim();
        items.push(`<li>${inline(item)}</li>`);
      }
      out += ordered ? `<ol>${items.join("")}</ol>` : `<ul>${items.join("")}</ul>`; continue;
    }
    if (/^>\s?/.test(ln)) { const q = []; while (i < lines.length && /^>\s?/.test(lines[i])) q.push(lines[i++].replace(/^>\s?/, "")); out += `<blockquote>${inline(q.join(" "))}</blockquote>`; continue; }
    if (/^\s*(-{3,}|\*{3,})\s*$/.test(ln)) { i++; continue; }
    if (!ln.trim()) { i++; continue; }
    // keep monospace-looking text (Gantt charts, frame tables) intact
    if (/^\s*\|/.test(ln) || /^\s{4,}\S/.test(ln)) {
      const pre = []; while (i < lines.length && lines[i].trim() && (/^\s*\|/.test(lines[i]) || /^\s*[\d\s]+$/.test(lines[i]) || /^\s{4,}/.test(lines[i]))) pre.push(lines[i++]);
      out += `<pre><code>${esc(pre.join("\n"))}</code></pre>`; continue;
    }
    const para = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|>|\s*([-*+]|\d+[.)])\s+|\s*\|)/.test(lines[i])) para.push(lines[i++]);
    if (!para.length) para.push(lines[i++]);
    out += `<p>${inline(para.join(" "))}</p>`;
  }
  return out;
}

/* ------------------------------------------------------------------ CPU scheduling visuals */
const pidColor = (pid) => (pid === "IDLE" ? "var(--line)" : `var(--p${((parseInt(String(pid).replace(/\D/g, ""), 10) || 0)) % 6 + 1})`);
const pidTag = (pid, cls = "") => el("span", { class: "pid " + cls, style: `--c:${pidColor(pid)}` }, pid);

function ganttSVG(sol) {
  const g = sol.gantt; const t0 = g[0].start, t1 = g[g.length - 1].end, span = Math.max(1, t1 - t0);
  const W = 720, H = 74, pad = 12, top = 8, h = 38, x = (t) => pad + ((t - t0) / span) * (W - 2 * pad);
  const id = "h" + Math.random().toString(36).slice(2, 8);
  let s = `<svg class="gantt" viewBox="0 0 ${W} ${H}" role="img" aria-label="Gantt chart: ${esc(g.map((b) => `${b.pid} ${b.start} to ${b.end}`).join(", "))}">
    <defs><pattern id="${id}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="var(--line-2)"/><line x1="0" y1="0" x2="0" y2="6" stroke="var(--line)" stroke-width="3"/></pattern></defs>`;
  const ticks = new Set();
  for (const b of g) {
    const x0 = x(b.start), w = Math.max(1, x(b.end) - x0);
    const fill = b.pid === "IDLE" ? `url(#${id})` : pidColor(b.pid);
    s += `<rect x="${x0 + 1}" y="${top}" width="${Math.max(1, w - 2)}" height="${h}" rx="4" fill="${fill}"><title>${esc(b.pid)}: ${b.start} to ${b.end}</title></rect>`;
    if (w > 22) s += `<text x="${x0 + w / 2}" y="${top + h / 2 + 5}" text-anchor="middle" font-size="13" font-weight="600" fill="${b.pid === "IDLE" ? "var(--muted)" : "#fff"}">${b.pid === "IDLE" ? "idle" : esc(b.pid)}</text>`;
    ticks.add(b.start); ticks.add(b.end);
  }
  let last = -99;
  for (const t of [...ticks].sort((a, b) => a - b)) {
    const tx = x(t); if (tx - last < 14 && t !== t1) continue; last = tx;
    s += `<line x1="${tx}" x2="${tx}" y1="${top + h + 2}" y2="${top + h + 7}" stroke="var(--muted)"/><text x="${tx}" y="${H - 4}" text-anchor="middle" font-size="12" fill="var(--ink-2)">${t}</text>`;
  }
  return s + "</svg>";
}

function processTable(procs, withPriority) {
  return el("div", { class: "table-wrap" }, el("table", { class: "data" },
    el("thead", {}, el("tr", {}, el("th", {}, "Process"), el("th", { class: "num" }, "Arrival (AT)"), el("th", { class: "num" }, "Burst (BT)"),
      withPriority ? el("th", { class: "num" }, "Priority") : null)),
    el("tbody", {}, procs.map((p) => el("tr", {}, el("td", {}, pidTag(p.pid)), el("td", { class: "num" }, p.arrival), el("td", { class: "num" }, p.burst),
      withPriority ? el("td", { class: "num" }, p.priority) : null)))));
}

function resultTable(sol) {
  const rows = Object.entries(sol.table);
  return el("div", { class: "table-wrap" }, el("table", { class: "data" },
    el("thead", {}, el("tr", {}, ["Process", "AT", "BT", "CT", "TAT = CT − AT", "WT = TAT − BT", "RT"].map((h, i) => el("th", { class: i ? "num" : null }, h)))),
    el("tbody", {}, rows.map(([pid, r]) => el("tr", {}, el("td", {}, pidTag(pid)),
      [r.arrival, r.burst, r.completion, r.turnaround, r.waiting, r.response].map((v) => el("td", { class: "num" }, v)))))));
}

function stepsTable(sol, open) {
  if (!sol.steps?.length) return null;
  return el("details", { class: "steps", open },
    el("summary", {}, `How the chart is built, decision by decision (${sol.steps.length} steps)`),
    el("div", { class: "table-wrap" }, el("table", { class: "data" },
      el("thead", {}, el("tr", {}, el("th", { class: "num" }, "Time"), el("th", {}, "Ready queue"), el("th", {}, "Runs"), el("th", {}, "Why"))),
      el("tbody", {}, sol.steps.map((s) => el("tr", {}, el("td", { class: "num" }, s.time), el("td", {}, s.ready),
        el("td", {}, s.runs === "IDLE" ? "idle" : pidTag(s.runs)), el("td", {}, s.why)))))));
}

function averages(sol) {
  return el("div", { class: "summary-row" },
    el("span", {}, "Average TAT ", el("b", {}, fmt(sol.avg_tat))), el("span", {}, "Average WT ", el("b", {}, fmt(sol.avg_wt))),
    el("span", {}, "Average RT ", el("b", {}, fmt(sol.avg_rt))), el("span", {}, "CPU utilisation ", el("b", {}, pct(sol.cpu_utilization))));
}

function exampleBlock(ex) {
  const q = ex.time_quantum ? `, time quantum ${ex.time_quantum}` : "";
  return el("div", { class: "block" },
    el("h3", { class: "block-title" }, `${ex.name}${q}`),
    ex.scenario ? el("p", {}, ex.scenario) : null,
    processTable(ex.processes, ex.with_priority),
    stepsTable(ex.solution, true),
    el("div", { html: ganttSVG(ex.solution) }),
    resultTable(ex.solution), averages(ex.solution));
}

function tabbed(labels, render) {
  const panes = el("div"), tabs = el("div", { class: "tabs", role: "tablist" });
  const show = (i) => { $$("button", tabs).forEach((b, j) => b.setAttribute("aria-selected", String(i === j))); panes.replaceChildren(...[render(i)].flat().filter(Boolean)); };
  labels.forEach((l, i) => tabs.append(el("button", { type: "button", role: "tab", onclick: () => show(i) }, l)));
  show(0);
  return [tabs, panes];
}

function comparisonBlock(c) {
  const metrics = [["avg_wt", "Avg waiting", "var(--p1)"], ["avg_tat", "Avg turnaround", "var(--p2)"], ["avg_rt", "Avg response", "var(--p3)"]];
  const max = Math.max(1, ...c.results.flatMap((r) => metrics.map(([k]) => r.solution[k])));
  return el("div", { class: "block" },
    el("h3", { class: "block-title" }, "Same processes, different schedulers"),
    processTable(c.processes, c.with_priority),
    el("div", { class: "table-wrap" }, el("table", { class: "data" },
      el("thead", {}, el("tr", {}, el("th", {}, "Run"), el("th", { class: "num" }, "Avg TAT"), el("th", { class: "num" }, "Avg WT"),
        el("th", { class: "num" }, "Avg RT"), el("th", { class: "num" }, "Context switches"))),
      el("tbody", {}, c.results.map((r) => el("tr", {}, el("td", {}, el("b", {}, r.label)), el("td", { class: "num" }, fmt(r.solution.avg_tat)),
        el("td", { class: "num" }, fmt(r.solution.avg_wt)), el("td", { class: "num" }, fmt(r.solution.avg_rt)), el("td", { class: "num" }, r.switches)))))),
    el("div", { class: "bar-legend" }, metrics.map(([, n, col]) => el("span", { style: `--c:${col}` }, n))),
    el("div", { class: "bars" }, c.results.map((r) => el("div", { class: "bar-row" }, el("span", {}, r.label),
      el("div", { class: "bar-track" }, metrics.map(([k, n, col]) => el("div", { class: "bar", style: `width:${(r.solution[k] / max) * 100}%;background:${col}`, title: `${n}: ${fmt(r.solution[k])}` })))))),
    ...tabbed(c.results.map((r) => r.label), (i) => [el("div", { html: ganttSVG(c.results[i].solution) }), stepsTable(c.results[i].solution, false), resultTable(c.results[i].solution)]));
}

/* ------------------------------------------------------------------ the other solvers: Banker's, pages, disk, memory */
function traceList(t, open = false) {
  if (!t.steps?.length) return null;
  return el("details", { class: "steps", open },
    el("summary", {}, `Every decision, step by step (${t.steps.length})`),
    el("ol", { class: "trace" }, t.steps.map((s) => el("li", {}, s.text))));
}
function factsRow(summary, skip = []) {
  const keys = Object.keys(summary || {}).filter((k) => !skip.includes(k));
  if (!keys.length) return null;
  return el("div", { class: "facts" }, keys.map((k) => el("div", {}, el("span", {}, k), el("b", {}, String(summary[k])))));
}
function seqChips(seq, cls = "") {
  return el("div", { class: "seq" }, seq.flatMap((p, i) => [i ? el("span", { class: "arrow", "aria-hidden": "true" }, "→") : null, pidTag(p, cls)]));
}

function bankersView(t) {
  const inp = t.inputs, v = t.view, R = inp.resources, det = t.algorithm === "DETECT";
  const second = det ? inp.request_matrix : inp.max;
  const rowState = (p) => (det ? (v.deadlocked.includes(p) ? "dead" : "ok") : "");
  const head = el("tr", {}, el("th", {}, "Process"), el("th", {}, `Allocation (${R.join(" ")})`), el("th", {}, `${det ? "Request" : "Max"} (${R.join(" ")})`),
    det ? null : el("th", {}, `Need (${R.join(" ")})`));
  const main = el("div", { class: "table-wrap" }, el("table", { class: "data" }, el("thead", {}, head),
    el("tbody", {}, inp.processes.map((p, i) => el("tr", { class: rowState(p) }, el("td", {}, pidTag(p)),
      el("td", { class: "vec" }, vec(inp.allocation[i])), el("td", { class: "vec" }, vec(second[i])),
      det ? null : el("td", { class: "vec" }, vec(v.need[i])))))));
  const avail = el("p", { class: "summary-row" }, el("span", {}, `Available (${R.join(" ")}) `, el("b", { class: "mono" }, vec(inp.available))),
    t.algorithm === "REQUEST" ? el("span", {}, `${inp.request_pid} requests `, el("b", { class: "mono" }, vec(inp.request))) : null,
    t.algorithm === "REQUEST" && v.available_after ? el("span", {}, "Available if granted ", el("b", { class: "mono" }, vec(v.available_after))) : null);

  let verdict;
  if (t.algorithm === "BANKERS") verdict = el("div", {}, el("span", { class: `verdict ${v.safe ? "yes" : "no"}` }, v.safe ? "Safe state" : "Unsafe state"),
    v.sequence?.length ? seqChips(v.sequence) : null);
  else if (t.algorithm === "REQUEST") {
    const d = String(t.summary.Decision || "");
    verdict = el("div", {}, el("span", { class: `verdict ${v.granted ? "yes" : /wait/.test(d) ? "hold" : "no"}` }, `Request ${d}`),
      v.granted && v.sequence?.length ? seqChips(v.sequence) : null);
  } else verdict = el("div", {}, el("span", { class: `verdict ${v.deadlocked.length ? "no" : "yes"}` }, v.deadlocked.length ? "Deadlock found" : "No deadlock"),
    v.deadlocked.length ? seqChips(v.deadlocked, "dead") : null);

  const rows = v.rows || [];
  const passes = rows.length ? el("details", { class: "steps" }, el("summary", {}, `The ${det ? "detection" : "safety"} check, pass by pass (${rows.length} checks)`),
    el("div", { class: "table-wrap" }, el("table", { class: "data" },
      el("thead", {}, el("tr", {}, el("th", { class: "num" }, "Pass"), el("th", {}, "Process"), el("th", {}, det ? "Request" : "Need"), el("th", {}, "Work before"), el("th", {}, "Result"), el("th", {}, "Work after"))),
      el("tbody", {}, rows.map((r) => el("tr", { class: r.ok ? "ok" : "wait" }, el("td", { class: "num" }, r.pass), el("td", {}, pidTag(r.pid)),
        el("td", { class: "vec" }, vec(r.need)), el("td", { class: "vec" }, vec(r.work_before)), el("td", {}, r.ok ? "finishes" : "waits"), el("td", { class: "vec" }, vec(r.work_after)))))))) : null;
  return [main, avail, verdict, passes];
}

function pageView(t) {
  const cols = t.view.columns, n = t.inputs.frames;
  const head = el("tr", {}, el("th", { class: "rowlab" }, "Ref"), cols.map((c) => el("th", { scope: "col" }, c.ref)));
  const rows = [];
  for (let f = 0; f < n; f++) {
    rows.push(el("tr", {}, el("th", { class: "rowlab", scope: "row" }, `Frame ${f + 1}`), cols.map((c) => {
      const val = c.frames[f];
      const isNew = c.fault && val === c.ref;
      return el("td", { class: val == null ? "empty" : isNew ? "new" : "", title: isNew && c.victim != null ? `${c.ref} replaced ${c.victim}` : null }, val == null ? "–" : val);
    })));
  }
  rows.push(el("tr", {}, el("th", { class: "rowlab" }, "Result"), cols.map((c) => el("td", { class: `res ${c.fault ? "f" : "h"}` }, c.fault ? "F" : "H"))));
  const refs = cols.length;
  return [el("div", { class: "table-wrap" }, el("table", { class: "frames", "aria-label": "Frame contents after each reference" }, el("thead", {}, head), el("tbody", {}, rows))),
    el("div", { class: "facts" }, el("div", {}, el("span", {}, "Page faults"), el("b", {}, t.view.faults)), el("div", {}, el("span", {}, "Hits"), el("b", {}, t.view.hits)),
      el("div", {}, el("span", {}, "Hit ratio"), el("b", {}, `${t.view.hits}/${refs} = ${pct(t.view.hits / refs)}`)))];
}

function diskSVG(t) {
  const v = t.view, max = t.inputs.max_cyl || 199, path = v.path;
  const W = 720, pad = 26, top = 30, row = 24, H = top + (path.length - 1) * row + 18;
  const x = (c) => pad + (c / max) * (W - 2 * pad), y = (i) => top + i * row;
  const jumps = new Set(v.jumps || []);
  let s = `<svg class="disk-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Head movement: ${esc(path.join(" to "))}, total ${v.total} cylinders">`;
  s += `<line x1="${x(0)}" x2="${x(max)}" y1="14" y2="14" stroke="var(--line)" stroke-width="2"/>`;
  for (const m of [0, max]) s += `<line x1="${x(m)}" x2="${x(m)}" y1="10" y2="18" stroke="var(--muted)"/><text x="${x(m)}" y="28" text-anchor="middle" font-size="11" fill="var(--muted)">${m}</text>`;
  for (let i = 0; i + 1 < path.length; i++) {
    const dashed = jumps.has(i);
    s += `<line x1="${x(path[i])}" y1="${y(i)}" x2="${x(path[i + 1])}" y2="${y(i + 1)}" stroke="${dashed ? "var(--muted)" : "var(--accent)"}" stroke-width="2" ${dashed ? 'stroke-dasharray="5 5"' : ""}/>`;
  }
  path.forEach((c, i) => {
    const served = i > 0 && v.service[i - 1];
    const fill = i === 0 ? "var(--ink)" : served ? "var(--accent)" : "var(--surface)";
    s += `<circle cx="${x(c)}" cy="${y(i)}" r="5" fill="${fill}" stroke="${i === 0 ? "var(--ink)" : "var(--accent)"}" stroke-width="2"><title>${i === 0 ? "start" : served ? "served" : "edge"} ${c}</title></circle>`;
    const right = x(c) < W - 60;
    s += `<text x="${x(c) + (right ? 10 : -10)}" y="${y(i) + 4}" text-anchor="${right ? "start" : "end"}" font-size="12" fill="var(--ink-2)">${c}</text>`;
  });
  return s + "</svg>";
}
function diskView(t) {
  const v = t.view;
  const moves = el("div", { class: "facts" }, el("div", {}, el("span", {}, "Service order"), el("b", { class: "mono" }, v.order.join(", "))),
    el("div", {}, el("span", {}, "Total head movement"), el("b", {}, `${v.total} cylinders`)),
    el("div", {}, el("span", {}, "Average seek"), el("b", {}, fmt(v.total / v.order.length))));
  return [el("p", { class: "summary-row" }, el("span", {}, "Head starts at ", el("b", {}, t.inputs.head)), t.inputs.direction && /SCAN|LOOK/.test(t.algorithm) ? el("span", {}, "Moving ", el("b", {}, t.inputs.direction === "up" ? `towards ${t.inputs.max_cyl}` : "towards 0")) : null,
    el("span", {}, "Cylinders ", el("b", {}, `0 to ${t.inputs.max_cyl}`))),
    el("div", { html: diskSVG(t) }), moves];
}

function allocView(t) {
  const inp = t.inputs, v = t.view, place = el("div", { class: "table-wrap" }, el("table", { class: "data" },
    el("thead", {}, el("tr", {}, el("th", {}, "Process"), el("th", { class: "num" }, "Size (KB)"), el("th", {}, "Goes to"), el("th", { class: "num" }, "Hole left (KB)"))),
    el("tbody", {}, t.steps.filter((s) => s.pid).map((s) => el("tr", { class: s.block ? "ok" : "dead" }, el("td", {}, pidTag(s.pid)), el("td", { class: "num" }, s.size),
      el("td", {}, s.block ? `${s.block} (${s.before} KB)` : "waits, no hole is big enough"), el("td", { class: "num" }, s.block ? s.after : "–"))))));
  const holes = el("div", { class: "table-wrap" }, el("table", { class: "data" },
    el("thead", {}, el("tr", {}, el("th", {}, "Hole"), el("th", { class: "num" }, "Before (KB)"), el("th", { class: "num" }, "After (KB)"))),
    el("tbody", {}, v.labels.map((b, i) => el("tr", {}, el("td", {}, el("b", {}, b)), el("td", { class: "num" }, inp.blocks[i]), el("td", { class: "num" }, v.holes_after[i]))))));
  return [place, holes, factsRow(t.summary, ["Placement", "Free holes left"])];
}

function taskBody(t) {
  if (t.kind === "bankers") return bankersView(t);
  if (t.kind === "page") return pageView(t);
  if (t.kind === "disk") return diskView(t);
  if (t.kind === "alloc") return allocView(t);
  return [factsRow(t.summary)];
}
function problemText(t) {
  const i = t.inputs;
  if (t.kind === "page") return `Reference string: ${i.refs.join(" ")}\nFrames: ${i.frames}`;
  if (t.kind === "disk") return `Request queue: ${i.requests.join(", ")}`;
  if (t.kind === "alloc") return `Holes: ${i.blocks.map((b, k) => `B${k + 1} = ${b}`).join(", ")} KB\nProcesses: ${i.names.map((p, k) => `${p} = ${i.sizes[k]}`).join(", ")} KB`;
  return null;
}
function taskBlock(t, { title = true, open = false } = {}) {
  const prob = problemText(t);
  return el("div", { class: "block" },
    title ? el("h3", { class: "block-title" }, t.name) : null,
    prob ? el("div", { class: "problem" }, prob) : null,
    ...taskBody(t).filter(Boolean), traceList(t, open));
}

function taskCompareBlock(ev) {
  const items = ev.items, labels = ev.labels;
  const k = items[0]?.kind;
  const metric = (t) => (t.kind === "page" ? t.view.faults : t.kind === "disk" ? t.view.total : null);
  const unit = k === "page" ? "page faults" : k === "disk" ? "cylinders moved" : "";
  const vals = items.map(metric), max = Math.max(1, ...vals.filter((x) => x != null));
  const prob = problemText(items[0]);
  let summary;
  if (vals.every((x) => x != null)) {
    summary = el("div", { class: "bars" }, items.map((t, i) => el("div", { class: "bar-row" }, el("span", {}, labels[i]),
      el("div", { class: "bar-one" }, el("div", { class: "bar", style: `width:${(vals[i] / max) * 70}%` }), `${vals[i]} ${unit}`))));
  } else if (k === "alloc") {
    summary = el("div", { class: "table-wrap" }, el("table", { class: "data" },
      el("thead", {}, el("tr", {}, el("th", {}, "Strategy"), items[0].inputs.names.map((p) => el("th", {}, p)), el("th", {}, "Must wait"))),
      el("tbody", {}, items.map((t, i) => el("tr", {}, el("td", {}, el("b", {}, labels[i])), t.inputs.names.map((p) => el("td", {}, t.view.placed[p] || "waits")),
        el("td", {}, t.view.waiting.length ? t.view.waiting.join(", ") : "none"))))));
  } else summary = el("div", {}, items.map((t, i) => el("p", {}, el("b", {}, labels[i] + ": "), Object.values(t.summary).slice(0, 2).join("; "))));
  return el("div", { class: "block" },
    el("h3", { class: "block-title" }, k === "page" ? "Same reference string, different replacement rules" : k === "disk" ? "Same request queue, different schedulers" : "Same input, different algorithms"),
    prob ? el("div", { class: "problem" }, prob) : null, summary,
    ...tabbed(labels, (i) => [...taskBody(items[i]).filter(Boolean), traceList(items[i])]));
}

function sourcesBlock(items) {
  if (!items?.length) return null;
  const nUni = items.filter((s) => s.origin === "universal").length;
  const nMine = items.filter((s) => s.origin === "your files").length;
  const parts = [nUni ? `${nUni} from open textbooks and docs` : null, nMine ? `${nMine} from your files` : null].filter(Boolean);
  return el("details", { class: "sources" },
    el("summary", {}, `Based on ${items.length} passage${items.length > 1 ? "s" : ""}` + (parts.length ? `, ${parts.join(" and ")}` : " from the course notes")),
    el("ul", {}, items.map((s) => el("li", {},
      el("div", {}, el("span", { class: `badge ${s.origin === "universal" ? "universal" : s.origin === "your files" ? "mine" : ""}` }, s.origin === "universal" ? sourceKind(s) : s.origin === "your files" ? "Your file" : "Course notes"),
        s.url ? el("a", { href: s.url, target: "_blank", rel: "noopener" }, s.source) : el("b", {}, s.source + (s.page ? `, page ${s.page}` : ""))),
      el("span", { class: "excerpt" }, s.excerpt)))));
}
const sourceKind = (s) => {
  const t = `${s.url || ""} ${s.source}`;
  if (/ostep|three easy pieces|hailperin|os-book/i.test(t)) return "Textbook";
  if (/microsoft/i.test(t)) return "Windows docs";
  if (/man7|man-pages/i.test(t)) return "Linux man page";
  if (/kernel/i.test(t)) return "Linux kernel docs";
  return "Reference";
};

/* ------------------------------------------------------------------ mood */
const moodColor = (m) => `var(--m-${m || "neutral"})`;
function setReading(r, typing) {
  const box = $("#reading");
  $(".pulse", box).style.background = moodColor(r?.mood);
  box.classList.toggle("live", !!typing);
  let text = "Listening";
  const mood = r && r.mood !== "neutral", tone = r && r.tone && r.tone !== "neutral";
  if (mood) text = `Reading you as ${r.label}` + (tone ? `, ${r.tone} tone` : "");
  else if (tone) text = `Reading a ${r.tone} tone`;
  $(".reading-text", box).textContent = text;
}
let moodTimer = null;
function liveMood() {
  clearTimeout(moodTimer);
  const text = $("#input").value.trim();
  if (text.length < 3) { setReading(null); return; }
  moodTimer = setTimeout(async () => {
    try { setReading(await api("/api/mood", { student: S.student, message: text, history: S.history }), true); } catch { /* ignore */ }
  }, 350);
}

/* ------------------------------------------------------------------ chat */
// Each turn = one question and its answer. Editing or regenerating a turn keeps the old
// conversation as a version, like ChatGPT / Claude: arrows under the question switch between them.
//   turn  = { text, answer, mood, events, quiz, userNode, botNode, group }
//   group = { branches: [[turn, ...], ...], current }   (one group per edited position)
// turn.events keeps every server event (tokens merged), so a saved chat can be drawn again exactly.
S.turns = [];
let controller = null;

const ICON = {
  edit: '<path d="M4 20h4L19 9l-4-4L4 16v4z M13.5 6.5l4 4" />',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  regen: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6"/>',
  left: '<path d="M15 6l-6 6 6 6"/>',
  right: '<path d="M9 6l6 6-6 6"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
};
const svg = (name) => `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICON[name]}</svg>`;
function iconBtn(label, icon, onclick, cls = "") {
  return el("button", { type: "button", class: "act " + cls, title: label, "aria-label": label, html: svg(icon), onclick });
}

function scrollThread() { const t = $("#thread"); t.scrollTop = t.scrollHeight; }

function historyFrom(turns) {
  const h = [];
  for (const t of turns) {
    if (t.quiz) continue;
    h.push({ role: "user", content: t.text, mood: t.mood });
    if (t.answer) h.push({ role: "assistant", content: t.answer.slice(0, 1500) });
  }
  return h.slice(-12);
}
const syncHistory = () => { S.history = historyFrom(S.turns); };

async function copyText(text, btn) {
  try { await navigator.clipboard.writeText(text); }
  catch {
    const t = el("textarea", { style: "position:fixed;opacity:0" }); t.value = text; document.body.append(t); t.select();
    document.execCommand("copy"); t.remove();
  }
  btn.innerHTML = svg("check"); btn.classList.add("done");
  setTimeout(() => { btn.innerHTML = svg("copy"); btn.classList.remove("done"); }, 1400);
}

/* ---- the question bubble with Edit / Copy and version arrows */
function buildUser(turn) {
  const col = el("div", { class: "user-col" });
  const node = el("div", { class: "msg user" + (turn.quiz ? " quiz" : "") }, col);
  turn.userNode = node;
  showBubble(turn);
  return node;
}
function showBubble(turn) {
  const col = $(".user-col", turn.userNode);
  const pager = el("div", { class: "pager" });
  col.replaceChildren(...[
    el("div", { class: "bubble" }, turn.text),
    turn.quiz ? null : el("div", { class: "msg-actions" },
      pager,
      iconBtn("Edit", "edit", () => startEdit(turn)),
      iconBtn("Copy", "copy", (e) => copyText(turn.text, e.currentTarget)))].filter(Boolean));
  drawPager(turn, pager);
}
function drawPager(turn, pager = $(".pager", turn.userNode)) {
  if (!pager) return;
  const g = turn.group;
  if (!g || g.branches.length < 2) { pager.replaceChildren(); return; }
  pager.replaceChildren(
    iconBtn("Previous version", "left", () => switchVersion(turn, g.current - 1)),
    el("span", {}, `${g.current + 1} / ${g.branches.length}`),
    iconBtn("Next version", "right", () => switchVersion(turn, g.current + 1)));
  const [prev, next] = $$("button", pager);
  prev.disabled = g.current === 0; next.disabled = g.current === g.branches.length - 1;
}

function startEdit(turn) {
  const col = $(".user-col", turn.userNode);
  const box = el("textarea", { class: "edit-box", rows: 1, "aria-label": "Edit your message" });
  box.value = turn.text;
  const fit = () => { box.style.height = "auto"; box.style.height = Math.min(320, box.scrollHeight) + "px"; };
  const save = () => { const t = box.value.trim(); if (t) branchFrom(turn, t); };
  box.addEventListener("input", fit);
  box.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); save(); }
    if (e.key === "Escape") { e.preventDefault(); showBubble(turn); }
  });
  col.replaceChildren(el("div", { class: "editor" }, box,
    el("div", { class: "edit-foot" },
      el("span", {}, "Editing creates a new version of the conversation from here."),
      el("div", { class: "edit-btns" },
        el("button", { type: "button", class: "btn-ghost", onclick: () => showBubble(turn) }, "Cancel"),
        el("button", { type: "button", class: "btn-main", onclick: save }, "Send")))));
  requestAnimationFrame(() => { fit(); box.focus(); box.setSelectionRange(box.value.length, box.value.length); });
}

/* ---- versions: an edit or a regenerate starts a new branch at that turn's position */
function detach(turns) { for (const t of turns) { t.userNode.remove(); t.botNode?.remove(); } }
function attach(turns) { const th = $("#thread"); for (const t of turns) { th.append(t.userNode); if (t.botNode) th.append(t.botNode); } }

async function branchFrom(turn, text) {
  await settle();
  const idx = S.turns.indexOf(turn); if (idx < 0) return;
  const g = turn.group || (turn.group = { branches: [], current: 0 });
  if (!g.branches.length) g.branches.push(null);
  showBubble(turn);
  g.branches[g.current] = S.turns.slice(idx);
  detach(g.branches[g.current]);
  S.turns.length = idx; syncHistory();
  g.branches.push(null); g.current = g.branches.length - 1;
  send(text, g);
}

async function switchVersion(turn, j) {
  const g = turn.group; if (!g || j < 0 || j >= g.branches.length || j === g.current) return;
  await settle();
  const idx = S.turns.indexOf(turn); if (idx < 0) return;
  g.branches[g.current] = S.turns.slice(idx);
  detach(g.branches[g.current]);
  g.current = j;
  const tail = g.branches[j] || [];
  S.turns = S.turns.slice(0, idx).concat(tail);
  attach(tail);
  for (const t of S.turns) drawPager(t);
  syncHistory(); saveChat();
}

function regenerate(turn) { branchFrom(turn, turn.text); }

function pathBlock(path) {
  if (!path || !path.length) return null;
  return el("details", { class: "path" },
    el("summary", {}, "How this was answered"),
    el("ol", {}, path.map((step) => el("li", {}, step))));
}

/* ---- one answer: draws server events into the bot bubble (live, or replayed from a saved chat) */
function answerView(turn, bot) {
  let body = el("div", { class: "md" }, el("span", { class: "typing" }, el("i"), el("i"), el("i")));
  bot.append(body);
  let view = renderer(body), started = false, sources = null, route = null;
  const ensureText = () => { if (!started) { started = true; body.replaceChildren(); } };
  const before = (node, head) => { bot.insertBefore(node, body); if (head) bot.insertBefore(el("div", { class: "explain-head" }, head), body); };
  const record = (ev) => {
    const last = turn.events[turn.events.length - 1];
    if (ev.type === "token" && last?.type === "token") last.text += ev.text; else turn.events.push({ ...ev });
  };
  const handlers = {
    mood: (ev) => { turn.mood = ev.mood; if (ev.summary) bot.prepend(el("div", { class: "mood-line" }, el("span", { class: "swatch", style: `background:${moodColor(ev.mood)}` }), ev.summary)); },
    note: (ev) => before(el("div", { class: "note" }, ev.text)),
    example: (ev) => before(exampleBlock(ev), "Explanation"),
    comparison: (ev) => before(comparisonBlock(ev), "Why the results differ"),
    task: (ev) => before(taskBlock(ev), "Explanation"),
    task_compare: (ev) => before(taskCompareBlock(ev), "Why the results differ"),
    sources: (ev) => { sources = ev.items; },
    done: (ev) => { route = ev.path || null; },
    section: (ev) => {
      if (turn.answer) view.flush();
      if (!started) { body.remove(); started = true; }
      body = el("div", { class: "md" });
      bot.append(el("h3", { class: "series-head" }, ev.title), body);
      view = renderer(body);
      turn.answer += (turn.answer ? "\n\n" : "") + `### ${ev.title}\n\n`;
    },
    token: (ev) => { ensureText(); turn.answer += ev.text; view.add(ev.text); },
    error: (ev) => { ensureText(); body.append(el("p", { class: "error" }, ev.text)); },
  };
  return {
    handle(ev, live = true) {
      if (live) record(ev);
      (handlers[ev.type] || (() => {}))(ev);
      if (live && ev.type !== "token") scrollThread();
    },
    finish(stopped) {
      if (turn.answer) view.flush();
      ensureText();
      if (stopped) body.append(el("p", { class: "stopped" }, "Stopped."));
      else if (!turn.answer && !body.textContent) body.append(el("p", { class: "empty" }, "No answer came back."));
      const src = sourcesBlock(sources); if (src) bot.append(src);
      const how = pathBlock(route); if (how) bot.append(how);
      bot.append(el("div", { class: "msg-actions bot-actions" },
        iconBtn("Copy answer", "copy", (e) => copyText(turn.answer || body.innerText, e.currentTarget)),
        iconBtn("Regenerate", "regen", () => regenerate(turn), "regen")));
    },
  };
}

/* ---- sending and streaming */
function setBusy(on) {
  S.busy = on;
  const b = $("#send");
  b.classList.toggle("stop", on);
  b.setAttribute("aria-label", on ? "Stop" : "Send");
  b.innerHTML = on
    ? '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/></svg>'
    : '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M4 12h13M12 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
}
function stopAnswer() { controller?.abort(); }
async function settle() { if (controller) { stopAnswer(); await S.running; } }

function startThread() { $("#hello")?.remove(); }

async function send(text, group = null) {
  text = (text || "").trim();
  if (!text || S.busy) return;
  setBusy(true); startThread();
  let finished; S.running = new Promise((r) => (finished = r));
  if (!group) { $("#input").value = ""; autosize(); }
  setReading(null);

  const turn = { text, answer: "", mood: null, group, events: [] };
  if (group) group.branches[group.current] = null;
  const thread = $("#thread");
  thread.append(buildUser(turn));
  const bot = el("div", { class: "msg bot" });
  thread.append(bot); turn.botNode = bot;
  S.turns.push(turn); scrollThread();
  const view = answerView(turn, bot);

  const history = historyFrom(S.turns.slice(0, -1));
  let stopped = false;
  controller = new AbortController();
  try {
    await streamApi("/api/chat", { student: S.student, message: text, history, mode: "teach" }, (ev) => {
      view.handle(ev);
      if (ev.type === "token" && thread.scrollHeight - thread.scrollTop - thread.clientHeight < 160) scrollThread();
    }, controller.signal);
  } catch (e) {
    if (e.name === "AbortError") stopped = true;
    else view.handle({ type: "error", text: e.message });
  }
  controller = null;
  view.finish(stopped);
  syncHistory(); saveChat();
  setBusy(false); finished();
  if (!group) $("#input").focus();
}

function autosize() { const t = $("#input"); t.style.height = "auto"; t.style.height = Math.min(180, t.scrollHeight) + "px"; }

/* ------------------------------------------------------------------ saved chats (this browser only) */
const chatKey = () => `osllm.chats.${S.student || "anon"}`;
const loadChats = () => store.get(chatKey(), []);
function saveChat() {
  const turns = S.turns.filter((t) => t.text).map((t) => ({ text: t.text, answer: t.answer, mood: t.mood, quiz: t.quiz || null, events: t.events || [] }));
  if (!turns.length) return;
  let chats = loadChats();
  if (!S.chatId) S.chatId = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const first = turns.find((t) => !t.quiz) || turns[0];
  const rec = { id: S.chatId, title: first.text.replace(/\s+/g, " ").slice(0, 60), at: Date.now(), turns };
  chats = [rec, ...chats.filter((c) => c.id !== S.chatId)].slice(0, 40);
  // localStorage is small; drop the oldest chats until it fits
  while (chats.length && !store.set(chatKey(), chats)) chats.pop();
  renderChatList();
}
function when(ts) {
  const d = new Date(ts), now = new Date();
  if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString([], { day: "numeric", month: "short" });
}
function renderChatList() {
  const list = $("#chat-list"), chats = loadChats();
  if (!chats.length) { list.replaceChildren(el("li", { class: "none" }, "Your chats will be listed here.")); return; }
  list.replaceChildren(...chats.map((c) => el("li", { "aria-current": String(c.id === S.chatId) },
    el("button", { type: "button", class: "open", onclick: () => openChat(c.id) }, el("b", {}, c.title), el("small", {}, `${when(c.at)}, ${c.turns.length} message${c.turns.length === 1 ? "" : "s"}`)),
    el("button", { type: "button", class: "del", title: "Delete chat", "aria-label": `Delete chat: ${c.title}`, html: svg("x"), onclick: () => deleteChat(c.id) }))));
}
function deleteChat(id) {
  store.set(chatKey(), loadChats().filter((c) => c.id !== id));
  if (id === S.chatId) newChat(); else renderChatList();
}
async function openChat(id) {
  await settle();
  const c = loadChats().find((x) => x.id === id); if (!c) return;
  location.hash = "#chat";
  S.chatId = id; S.turns = [];
  const thread = $("#thread"); thread.replaceChildren();
  for (const saved of c.turns) {
    const turn = { ...saved, answer: "", events: saved.events || [], group: null };
    thread.append(buildUser(turn));
    const bot = el("div", { class: "msg bot" }); thread.append(bot); turn.botNode = bot;
    if (turn.quiz) { turn.answer = saved.answer; quizCard(turn, bot); }
    else {
      const view = answerView(turn, bot);
      for (const ev of turn.events) view.handle(ev, false);
      if (!turn.events.length && saved.answer) view.handle({ type: "token", text: saved.answer }, false);
      view.finish(false);
    }
    S.turns.push(turn);
  }
  syncHistory(); renderChatList(); scrollThread();
}
async function newChat() {
  await settle();
  S.turns = []; S.history = []; S.chatId = null;
  $("#thread").replaceChildren(helloNode);
  setReading(null); renderChatList();
  location.hash = "#chat";
  $("#input").focus();
}
let helloNode;

/* ---- the syllabus strip on the empty chat */
const UNIT_COLORS = ["var(--ink)", "var(--p1)", "var(--accent)", "var(--p4)", "var(--p5)", "var(--p6)", "var(--p3)", "var(--p2)", "var(--muted)"];
const STARTERS = {
  "Introduction & OS Structure": ["What happens step by step when a program calls read()?", "Monolithic vs microkernel, with examples", "Why do we need dual-mode operation?"],
  "Processes & Threads": ["How many processes do three fork() calls create?", "Draw the process state diagram and explain each transition", "Shared memory vs message passing"],
  "CPU Scheduling": ["Compare SJF and SRTF", "Give me an example of a Gantt chart and how to solve it", "bro i dont get round robin at all"],
  "Process Synchronization": ["Explain Peterson's solution and prove mutual exclusion", "Solve the bounded-buffer problem with semaphores", "Why can the dining philosophers deadlock?"],
  "Deadlocks": ["Give me a Banker's algorithm example and solve it", "Explain the four conditions for deadlock", "Can P1's request (1, 0, 2) be granted? Use the classic example"],
  "Memory Management": ["Compare first fit, best fit and worst fit with one example", "Translate logical address 3085 with a 1 KB page size", "Internal vs external fragmentation"],
  "Virtual Memory": ["Compare FIFO, LRU and Optimal page replacement", "Show me Belady's anomaly", "What causes thrashing and how is it fixed?"],
  "Storage & File Systems": ["Solve SSTF for 98, 183, 37, 122, 14, 124, 65, 67 with head at 53", "Compare SCAN, C-SCAN and LOOK", "Contiguous vs linked vs indexed allocation"],
  "Linux": ["What does chmod 754 mean?", "Explain pipes with ps aux | grep", "kill vs kill -9"],
};
function renderSyllabus() {
  const units = S.status?.units; if (!units) return;
  const strip = $("#syllabus");
  const actions = [
    { icon: "✦", title: "Explain a concept", desc: "Get a clear explanation with examples.", prompt: "Explain an important Operating Systems concept step by step, using a simple analogy and a practical example." },
    { icon: "∑", title: "Solve a numerical", desc: "Work through calculations and show each step.", prompt: "Give me a representative Operating Systems numerical and solve it step by step, explaining every calculation." },
    { icon: "◉", title: "Quiz me", desc: "Test understanding and get feedback.", quiz: true },
    { icon: "▤", title: "Prepare for viva", desc: "Practise likely questions with model answers.", prompt: "Act as an Operating Systems viva examiner. Ask me one question at a time, wait for my answer, then evaluate it and explain the ideal answer." },
    { icon: "⌘", title: "Build a study plan", desc: "Create a focused plan for the time available.", prompt: "Help me create a practical Operating Systems study plan. First ask how much time I have and which topics I find difficult, then build a prioritized plan." },
    { icon: "↗", title: "Find my weak areas", desc: "Start a guided review of key topics.", prompt: "Guide me through a short Operating Systems diagnostic. Ask one question at a time across the syllabus, identify my weak areas, and recommend what to revise." }
  ];
  strip.classList.add("agent-grid");
  strip.setAttribute("aria-label", "Choose an AI tutor task");
  strip.replaceChildren(...actions.map((a) => {
    const button = el("button", { type: "button", class: "agent-card", onclick: () => a.quiz ? toggleQuizMenu() : send(a.prompt) },
      el("span", { class: "agent-icon", "aria-hidden": "true" }, a.icon),
      el("span", { class: "agent-title" }, a.title),
      el("span", { class: "agent-desc" }, a.desc),
      el("span", { class: "agent-arrow", "aria-hidden": "true" }, "↗"));
    return button;
  }));
  const u = units[S.unit] || units[0];
  const focus = el("select", { class: "focus-select", "aria-label": "Optional course focus", onchange: (event) => { S.unit = Number(event.target.value); renderSyllabus(); } },
    ...units.map((unit, i) => el("option", { value: String(i), selected: i === S.unit }, unit.unit)));
  const suggestions = STARTERS[u.unit] || [`Explain ${u.topics[0]}`];
  $("#unit-pane").replaceChildren(
    el("div", { class: "focus-head" },
      el("div", {}, el("h2", {}, "Explore a course topic"), el("p", { class: "topics-line" }, "Optional: choose a unit for tailored examples and practice.")),
      focus),
    el("div", { class: "chips" }, suggestions.map((q) => el("button", { type: "button", onclick: () => send(q) }, q))));
}

/* ------------------------------------------------------------------ quiz me, inside the chat */
function quizKindsFor(topic) { return (S.status?.practice_types[topic] || ["mcq", "viva"]); }
function fillQuizMenu(topic) {
  const sel = $("#quiz-topic");
  if (!sel.options.length) {
    for (const u of S.status.units) sel.append(el("optgroup", { label: u.unit }, u.topics.map((t) => el("option", { value: t }, t))));
    sel.onchange = () => fillQuizMenu(sel.value);
  }
  if (topic) sel.value = topic;
  $("#quiz-kinds").replaceChildren(...quizKindsFor(sel.value).map((k) => el("button", { type: "button", class: "btn small" + (k === "mcq" ? " primary" : ""),
    onclick: () => { closeQuizMenu(); startQuiz(sel.value, k); } }, S.status.activity_labels[k] || k)));
}
async function toggleQuizMenu() {
  const menu = $("#quiz-menu"), btn = $("#quiz-btn");
  if (!menu.hidden) return closeQuizMenu();
  if (!S.status) return;
  const recent = $("#input").value.trim() || [...S.turns].reverse().find((t) => !t.quiz)?.text || "";
  let topic = S.topic || S.status.topics[0];
  if (recent) { try { topic = (await api(`/api/topic_for?text=${encodeURIComponent(recent)}`)).topic || topic; } catch { /* keep default */ } }
  fillQuizMenu(topic);
  menu.hidden = false; btn.setAttribute("aria-expanded", "true");
  $("#quiz-topic").focus();
}
function closeQuizMenu() { $("#quiz-menu").hidden = true; $("#quiz-btn").setAttribute("aria-expanded", "false"); }

async function startQuiz(topic, kind) {
  if (S.busy) return;
  startThread();
  const label = S.status.activity_labels[kind] || kind;
  const turn = { text: `Quiz me: ${label} on ${topic}`, answer: "", quiz: { topic, kind, item: null, result: null }, events: [] };
  const thread = $("#thread");
  thread.append(buildUser(turn));
  const bot = el("div", { class: "msg bot" }, el("p", { class: "empty" }, "Writing a question for you…"));
  thread.append(bot); turn.botNode = bot; S.turns.push(turn); scrollThread();
  try {
    turn.quiz.item = await api("/api/practice/new", { student: S.student, topic, kind, difficulty: "auto" });
    turn.answer = turn.quiz.item.question || turn.quiz.item.task?.problem || "";
    bot.replaceChildren(); quizCard(turn, bot);
  } catch (e) { bot.replaceChildren(el("p", { class: "error" }, e.message)); }
  saveChat(); scrollThread();
}
function quizCard(turn, bot) {
  const q = turn.quiz;
  if (!q?.item) { bot.replaceChildren(el("p", { class: "empty" }, "This quiz didn't load.")); return; }
  renderItem(q.item, bot, {
    saved: q.result,
    onResult: (r) => { q.result = r; saveChat(); scrollThread(); },
    after: () => el("div", { class: "actions" },
      el("button", { class: "btn primary", type: "button", onclick: () => startQuiz(q.topic, q.kind) }, "Another question"),
      el("button", { class: "btn", type: "button", onclick: () => { location.hash = "#learn"; S.topic = q.topic; setTimeout(renderTopics, 30); } }, `Review ${q.topic}`)),
  });
}

/* ------------------------------------------------------------------ learn */
async function renderTopics() {
  let prog = null; try { prog = await api(`/api/progress?student=${encodeURIComponent(S.student)}`); } catch { /* offline */ }
  const m = Object.fromEntries((prog?.topics || []).map((t) => [t.topic, t]));
  const list = $("#topic-list"); list.replaceChildren();
  S.status.units.forEach((u, ui) => {
    const ul = el("ul");
    for (const t of u.topics) {
      const b = el("button", { type: "button", "aria-current": String(S.topic === t), onclick: () => { S.topic = t; $$("button", list).forEach((x) => x.setAttribute("aria-current", String(x === b))); updateLearnButtons(); } },
        el("span", { class: "topic-name" }, t), m[t]?.mastery ? el("span", { class: "meter", title: `Mastery ${pct(m[t].mastery)}` }, el("i", { style: `width:${pct(m[t].mastery)}` })) : null);
      ul.append(el("li", {}, b));
    }
    list.append(el("section", { class: "unit" }, el("h3", {}, el("span", { class: "n" }, `U${ui + 1}`), u.unit), ul));
  });
  updateLearnButtons();
}
function updateLearnButtons() {
  $("#learn-explain").disabled = !S.topic || S.busy;
  $("#learn-example").disabled = !S.topic || S.busy || !(S.topic in S.status.numerical_topics);
  $("#learn-example").title = S.topic && !(S.topic in S.status.numerical_topics) ? "This topic has no numerical problems" : "";
}
async function learn(kind) {
  if (!S.topic || S.busy) return;
  S.busy = true; updateLearnButtons();
  const out = $("#learn-out"); const body = el("div", { class: "md" }, el("span", { class: "typing" }, el("i"), el("i"), el("i")));
  out.replaceChildren(el("h2", { class: "block-title", style: "font-size:24px" }, kind === "lesson" ? S.topic : `${S.topic}: worked example`), body);
  let text = "", started = false, sources = null;
  const view = renderer(body, S.topic);
  try {
    await streamApi("/api/learn", { student: S.student, topic: S.topic, level: S.level, kind }, (ev) => {
      if (ev.type === "example") { out.insertBefore(exampleBlock(ev), body); out.insertBefore(el("div", { class: "explain-head" }, "Step by step"), body); }
      else if (ev.type === "task") { out.insertBefore(taskBlock(ev, { title: true }), body); out.insertBefore(el("div", { class: "explain-head" }, "Step by step"), body); }
      else if (ev.type === "sources") sources = ev.items;
      else if (ev.type === "token") { if (!started) { started = true; body.replaceChildren(); } text += ev.text; view.add(ev.text); }
      else if (ev.type === "error") body.replaceChildren(el("p", { class: "error" }, ev.text));
    });
    if (text) view.flush();
    const src = sourcesBlock(sources); if (src) out.append(src);
    if (text) {
      const done = el("button", { class: "btn primary", type: "button", onclick: async () => {
        await api("/api/learn/done", { student: S.student, topic: S.topic, kind: kind === "lesson" ? "lesson" : "worked_example" });
        done.replaceWith(el("p", { class: "empty" }, "Saved to your progress.")); renderTopics();
      } }, "I've understood this");
      out.append(el("div", { class: "actions" }, done, el("button", { class: "btn", type: "button", onclick: () => { location.hash = "#practice"; setTimeout(() => newItem({ topic: S.topic }), 50); } }, "Practise this topic")));
    }
  } catch (e) { body.replaceChildren(el("p", { class: "error" }, e.message)); }
  S.busy = false; updateLearnButtons();
}

/* ------------------------------------------------------------------ practice (also used by quizzes in chat) */
function fillPracticeSelects() {
  const topic = $("#p-topic");
  topic.replaceChildren(...S.status.units.map((u) => el("optgroup", { label: u.unit }, u.topics.map((t) => el("option", { value: t }, t)))));
  const kinds = () => { $("#p-kind").replaceChildren(...S.status.practice_types[topic.value].map((k) => el("option", { value: k }, S.status.activity_labels[k]))); };
  topic.onchange = kinds; kinds();
}

async function newItem(opts = {}) {
  const out = $("#practice-out");
  out.replaceChildren(el("p", { class: "empty" }, "Writing a question for you…"));
  try {
    const body = { student: S.student, difficulty: $("#p-diff").value, ...opts };
    if (!opts.auto && !opts.topic) { body.topic = $("#p-topic").value; body.kind = $("#p-kind").value; }
    if (opts.topic && !opts.kind) body.kind = S.status.practice_types[opts.topic][0];
    if (opts.auto) body.force_practice = true;
    delete body.auto;
    const item = await api("/api/practice/new", body);
    if (item.plan) {
      // Older servers may still return a lesson recommendation for auto-pick.
      // Never replace the Practice view with that card; immediately request a quiz.
      if (opts.auto || body.force_practice) {
        return newItem({ topic: item.plan.topic, kind: (S.status.practice_types[item.plan.topic] || ["mcq"])[0], difficulty: item.plan.difficulty || "auto" });
      }
      return renderPlan(item.plan);
    }
    renderItem(item, out, { after: () => practiceAfter(item) });
  } catch (e) { out.replaceChildren(el("p", { class: "error" }, e.message)); }
}
function practiceAfter(item) {
  return el("div", { class: "actions" }, el("button", { class: "btn primary", type: "button", onclick: () => newItem({ auto: true }) }, "Next (picked for me)"),
    el("button", { class: "btn", type: "button", onclick: () => newItem({ topic: item.topic, kind: item.kind }) }, "Another like this"));
}

function renderPlan(p) {
  $("#practice-out").replaceChildren(
    el("p", { class: "q-meta" }, "Suggested next"), el("p", { class: "q-text" }, `${p.label}: ${p.topic}`), el("p", {}, p.reason),
    el("div", { class: "actions" }, el("button", { class: "btn primary", type: "button", onclick: () => {
      S.topic = p.topic; S.level = p.difficulty; location.hash = "#learn";
      setTimeout(() => { renderTopics(); syncLevel(); learn(p.activity === "worked_example" ? "worked_example" : p.activity === "relearn" ? "relearn" : "lesson"); }, 60);
    } }, "Open it in Learn")));
}

// Draws one question into `out`. ctx.after() gives the buttons shown after answering;
// ctx.onResult(r) is told the result; ctx.saved is a result to show straight away (restored chats).
function renderItem(it, out, ctx = {}) {
  const st = { hints: 0 };
  const hints = el("div", { class: "hints" });
  const maxHints = it.kind === "mcq" ? 1 : it.kind === "viva" ? it.hint_count : 3;
  const hintBtn = el("button", { class: "btn", type: "button", onclick: async () => {
    hintBtn.disabled = true;
    try { const h = await api("/api/practice/hint", { id: it.id }); hints.append(el("p", { class: "hint" }, el("b", {}, `Hint ${h.used}: `), h.hint)); st.hints = h.used; }
    catch (e) { hints.append(el("p", { class: "error" }, e.message)); }
    refreshHint();
  } }, "Hint");
  const refreshHint = () => { const used = st.hints; hintBtn.disabled = used >= maxHints; hintBtn.textContent = used >= maxHints ? "No more hints" : `Hint (${used + 1} of ${maxHints})`; };
  const lock = () => $$(".actions button, input, textarea, select, .option, .seg button", out).forEach((x) => { x.disabled = true; });
  const finish = (r, extra) => {
    lock();
    const s = r.revealed ? 0 : r.score;
    out.append(el("div", { class: "result" },
      el("div", { class: `score ${s >= .8 ? "good" : s >= .5 ? "mid" : "low"}` }, r.revealed ? "Solution shown" : pct(s)),
      r.mastery != null ? el("p", { class: "empty" }, `${it.topic} mastery is now ${pct(r.mastery)}.`) : null,
      ...[extra(r)].flat().filter(Boolean), ctx.after ? ctx.after() : null));
    ctx.onResult?.(r);
  };
  const submit = async (btn, payload, extra, busyText = "Checking…") => {
    const label = btn.textContent; btn.disabled = true; btn.textContent = busyText;
    try { const r = await api("/api/practice/submit", { id: it.id, ...payload }); btn.textContent = label === "Show solution" || label === "Show model answer" ? label : "Checked"; finish(r, extra); }
    catch (e) { out.append(el("p", { class: "error" }, e.message)); btn.disabled = false; btn.textContent = label; }
  };
  const meta = el("p", { class: "q-meta" }, `${it.label}: ${it.topic}, ${it.difficulty}`);
  const reason = it.reason ? el("p", { class: "note" }, it.reason) : null;
  let restore = null;

  if (it.kind === "mcq") {
    let choice = null;
    const opts = el("div", { class: "options" }, it.options.map((o, i) => el("button", { type: "button", class: "option", "aria-pressed": "false",
      onclick: (e) => { choice = i; $$(".option", opts).forEach((b) => b.setAttribute("aria-pressed", String(b === e.currentTarget))); } },
      el("span", { class: "key" }, "ABCD"[i]), el("span", {}, o))));
    const extra = (r) => {
      $$(".option", opts).forEach((b, i) => {
        if (i === r.answer_index) b.classList.add("right");
        else if (i === (r.choice ?? choice)) b.classList.add("wrong");
      });
      const earned = Number(r.points_earned ?? r.score ?? 0);
      const possible = Number(r.points_possible ?? 1);
      return [el("p", { class: "q-meta" }, `Marking: ${earned.toFixed(2)} / ${possible.toFixed(2)} point${possible === 1 ? "" : "s"}${st.hints ? ` · ${st.hints} hint used (15% deduction per hint)` : ""}`),
        el("div", { class: "md", html: md(r.feedback || r.explanation) })];
    };
    const go = el("button", { class: "btn primary", type: "button", onclick: () => { if (choice != null) submit(go, { choice }, (r) => extra({ ...r, choice })); } }, "Check answer");
    out.replaceChildren(reason || "", meta, el("p", { class: "q-text" }, it.question), opts, hints, el("div", { class: "actions" }, hintBtn, go));
    restore = (r) => extra(r);
  } else if (it.kind === "viva") {
    const ta = el("textarea", { class: "answer", placeholder: "Answer as you would in a viva…", "aria-label": "Your answer" });
    const extra = (r) => [
      !r.revealed ? el("div", { class: "cols" }, el("div", {}, el("h4", {}, "You covered"), el("ul", {}, (r.covered?.length ? r.covered : ["Nothing yet"]).map((x) => el("li", {}, x)))),
        el("div", {}, el("h4", {}, "Missing or incomplete"), el("ul", {}, (r.missing?.length ? r.missing : ["Nothing, nice"]).map((x) => el("li", {}, x))))) : null,
      r.feedback ? el("div", { class: "md", html: md(r.feedback) }) : null,
      el("details", { class: "steps", open: r.revealed }, el("summary", {}, "Model answer"), el("div", { style: "padding:10px 14px" }, el("p", {}, r.model_answer), el("ul", {}, (r.key_points || []).map((k) => el("li", {}, k)))))];
    const go = el("button", { class: "btn primary", type: "button", onclick: () => submit(go, { answer: ta.value }, extra, "Grading…") }, "Submit answer");
    const reveal = el("button", { class: "btn", type: "button", onclick: () => submit(reveal, { reveal: true }, extra) }, "Show model answer");
    out.replaceChildren(reason || "", meta, el("p", { class: "q-text" }, it.question), ta, hints, el("div", { class: "actions" }, hintBtn, reveal, go));
    restore = extra;
  } else if (it.task) {
    const t = it.task, fields = {};
    const ask = el("div", { class: "ask" }, it.ask.map((f) => {
      if (f.type === "choice") {
        const seg = el("div", { class: "seg", role: "radiogroup", "aria-label": f.label }, f.options.map((o) => el("button", { type: "button", role: "radio", "aria-checked": "false",
          onclick: (e) => { fields[f.key].value = o; $$("button", seg).forEach((b) => b.setAttribute("aria-checked", String(b === e.currentTarget))); } }, o)));
        fields[f.key] = { node: seg, value: "" };
        return el("div", { class: "field" }, el("span", { class: "field-label" }, f.label), seg);
      }
      const inp = el("input", { class: "input", inputmode: f.type === "int" ? "numeric" : "text", "aria-label": f.label });
      fields[f.key] = { node: inp, get value() { return inp.value; } };
      return el("label", {}, f.label, inp);
    }));
    const extra = (r) => {
      for (const [k, ok] of Object.entries(r.fields || {})) fields[k]?.node.classList.add(ok ? "ok" : "no");
      return [r.feedback ? el("p", {}, r.feedback) : null, el("h3", { class: "block-title" }, "Correct solution"), r.task ? taskBlock(r.task, { title: false, open: !!r.revealed }) : null];
    };
    const collect = () => Object.fromEntries(Object.entries(fields).map(([k, f]) => [k, f.value]));
    const go = el("button", { class: "btn primary", type: "button", onclick: () => submit(go, { answers: collect() }, extra) }, "Check my answer");
    const reveal = el("button", { class: "btn", type: "button", onclick: () => submit(reveal, { reveal: true }, extra) }, "Show solution");
    const diskConv = { SCAN: "SCAN travels to the disk edge before reversing.", "C-SCAN": "C-SCAN travels to the disk edge, and the return jump counts towards the total.",
      "C-LOOK": "The return jump of C-LOOK counts towards the total.", SSTF: "If two requests are equally close, take the one that comes first in the queue." };
    const conv = { page: "A page fault is counted every time a page is loaded, including into an empty frame.",
      disk: diskConv[t.algorithm] || null,
      alloc: "The chosen hole is split and the rest stays free; next fit resumes at the hole used last.",
      bankers: "Course convention: repeated passes over the processes in order. Any valid safe sequence is accepted." }[t.kind];
    out.replaceChildren(reason || "", meta, el("p", { class: "q-text" }, `Solve with ${t.name}.`), el("div", { class: "problem" }, t.problem),
      conv ? el("p", { class: "empty" }, conv) : "", ask, hints, el("div", { class: "actions" }, hintBtn, reveal, go));
    restore = extra;
  } else {
    const pids = it.processes.map((p) => p.pid);
    const gantt = el("input", { class: "input wide", placeholder: "e.g. P1, P2, P1, P3", "aria-label": "Gantt chart order" });
    const cell = (pid, k) => el("input", { inputmode: "decimal", "data-pid": pid, "data-k": k, "aria-label": `${k} of ${pid}` });
    const grid = el("table", { class: "data grid-in" }, el("thead", {}, el("tr", {}, ["Process", "CT", "TAT", "WT"].map((h) => el("th", {}, h)))),
      el("tbody", {}, pids.map((pid) => el("tr", {}, el("td", {}, pidTag(pid)), ["CT", "TAT", "WT"].map((k) => el("td", {}, cell(pid, k)))))));
    const at = el("input", { class: "input", inputmode: "decimal", "aria-label": "Average TAT" }), aw = el("input", { class: "input", inputmode: "decimal", "aria-label": "Average WT" });
    const collectRows = () => { const rows = {}; $$("input[data-pid]", grid).forEach((i) => { (rows[i.dataset.pid] ||= {})[i.dataset.k] = i.value === "" ? null : Number(i.value); }); return rows; };
    const num = (v) => (v.value === "" ? null : Number(v.value));
    const extra = (r) => {
      if (r.cells) $$("input[data-pid]", grid).forEach((i) => i.classList.add(r.cells[i.dataset.pid]?.[i.dataset.k] ? "ok" : "no"));
      return [r.mistakes?.length && !r.revealed ? el("p", {}, el("b", {}, "What went wrong: "), r.mistakes.join("; ")) : null,
        r.feedback ? el("div", { class: "md", html: md(r.feedback) }) : null,
        el("h3", { class: "block-title" }, "Correct solution"), stepsTable(r.solution, !!r.revealed), el("div", { html: ganttSVG(r.solution) }),
        resultTable(r.solution), averages(r.solution)];
    };
    const go = el("button", { class: "btn primary", type: "button", onclick: () => submit(go, { gantt: gantt.value, rows: collectRows(), avg_tat: num(at), avg_wt: num(aw) }, extra) }, "Check my solution");
    const reveal = el("button", { class: "btn", type: "button", onclick: () => submit(reveal, { reveal: true }, extra) }, "Show solution");
    const q = it.time_quantum ? `, time quantum ${it.time_quantum}` : "";
    out.replaceChildren(reason || "", meta, el("p", { class: "q-text" }, `Solve with ${it.name}${q}.`), it.scenario ? el("p", {}, it.scenario) : "",
      processTable(it.processes, it.with_priority),
      el("p", { class: "empty" }, "TAT = CT − AT, WT = TAT − BT. Lower priority number means higher priority. Ties go to the earlier arrival, then the lower process number."),
      el("div", { class: "inline-fields" }, el("label", {}, "Gantt chart order", gantt)), el("div", { class: "table-wrap" }, grid),
      el("div", { class: "inline-fields" }, el("label", {}, "Average TAT", at), el("label", {}, "Average WT", aw)),
      hints, el("div", { class: "actions" }, hintBtn, reveal, go));
    restore = extra;
  }
  refreshHint();
  if (ctx.saved && restore) { const cb = ctx.onResult; ctx.onResult = null; finish(ctx.saved, restore); ctx.onResult = cb; }
}

/* ------------------------------------------------------------------ progress */
async function renderProgress() {
  const out = $("#progress-out"); out.replaceChildren(el("p", { class: "empty" }, "Loading…"));
  try {
    const p = await api(`/api/progress?student=${encodeURIComponent(S.student)}`);
    const mastered = p.topics.filter((t) => t.mastered).length;
    const byTopic = Object.fromEntries(p.topics.map((t) => [t.topic, t]));
    const row = (t) => el("div", { class: "m-row" },
      el("div", {}, el("b", {}, t.topic), el("small", {}, t.weak.length ? `Keeps tripping on: ${t.weak.join(", ")}` : `${t.attempts} attempt${t.attempts === 1 ? "" : "s"}, ${t.lessons} lesson${t.lessons === 1 ? "" : "s"}`)),
      el("div", { class: "meter" }, el("i", { style: `width:${pct(t.mastery)};background:${t.mastered ? "var(--good)" : t.mastery < .4 ? "var(--bad)" : "var(--accent)"}` })),
      el("span", { class: "pct" }, pct(t.mastery)));
    out.replaceChildren(
      el("div", { class: "stats" },
        el("div", { class: "stat" }, el("b", {}, `${mastered} of ${p.topics.length}`), el("span", {}, "topics mastered")),
        el("div", { class: "stat" }, el("b", {}, p.total_attempts), el("span", {}, "questions answered")),
        el("div", { class: "stat" }, el("b", {}, p.average == null ? "None yet" : pct(p.average)), el("span", {}, "average score"))),
      el("div", { class: "next-up" }, el("h3", {}, `Suggested next: ${p.next.label} on ${p.next.topic}`),
        el("p", { class: "empty" }, `${p.next.reason} This is optional—you can practise any topic or question type whenever you want.`),
        el("div", { class: "actions" },
          el("button", { class: "btn primary", type: "button", onclick: () => { location.hash = "#practice"; setTimeout(() => newItem({ auto: true }), 50); } }, "Start recommendation"),
          el("button", { class: "btn", type: "button", onclick: () => {
            const topicSelect = $("#p-topic"), kindSelect = $("#p-kind"), diffSelect = $("#p-diff");
            topicSelect.value = p.next.topic;
            topicSelect.dispatchEvent(new Event("change"));
            if ([...kindSelect.options].some((o) => o.value === "mcq")) kindSelect.value = "mcq";
            diffSelect.value = "auto";
            location.hash = "#practice";
            setTimeout(() => newItem({ topic: p.next.topic, kind: kindSelect.value, difficulty: "auto" }), 50);
          } }, "Practice this topic now"))),
      el("h2", { style: "font-size:22px;margin-bottom:14px" }, "Mastery by unit"),
      el("div", { class: "mastery" }, S.status.units.map((u, i) => el("section", { class: "m-unit" }, el("h3", {}, el("span", { class: "n" }, `U${i + 1}`), u.unit),
        el("div", { class: "rows" }, u.topics.filter((t) => byTopic[t]).map((t) => row(byTopic[t])))))),
      p.attempts.length ? el("div", { class: "history" }, el("h2", { style: "font-size:22px;margin-bottom:10px" }, "Recent answers"),
        el("div", { class: "table-wrap" }, el("table", { class: "data" }, el("thead", {}, el("tr", {}, ["When", "Topic", "Type", "Level", "Score", "Hints"].map((h) => el("th", {}, h)))),
          el("tbody", {}, p.attempts.slice().reverse().slice(0, 15).map((a) => el("tr", {}, el("td", {}, a.created_at.replace("T", " ").slice(0, 16)), el("td", {}, a.topic),
            el("td", {}, S.status.activity_labels[a.activity] || a.activity), el("td", {}, a.difficulty), el("td", { class: "num" }, pct(a.score)), el("td", { class: "num" }, a.hints_used)))))))
        : el("p", { class: "empty" }, "Answer a few practice questions and your history will show up here."));
  } catch (e) { out.replaceChildren(el("p", { class: "error" }, e.message)); }
}

/* ------------------------------------------------------------------ my files */
let filesTimer = null;
function showIndexing(ix) {
  const box = $("#index-state");
  box.className = "index-state" + (ix?.busy ? " busy" : ix?.error ? " err" : "");
  box.textContent = ix?.busy ? ix.message || "Indexing…" : ix?.error || ix?.message || "";
  $("#reindex").disabled = !!ix?.busy;
}
async function renderFiles() {
  const out = $("#files-out");
  try {
    const d = await api("/api/files");
    showIndexing(d.indexing);
    out.replaceChildren(d.files.length
      ? el("div", { class: "table-wrap" }, el("table", { class: "data" },
          el("thead", {}, el("tr", {}, el("th", {}, "File"), el("th", { class: "num" }, "Size"), el("th", { class: "num" }, "Passages indexed"), el("th", {}, ""))),
          el("tbody", {}, d.files.map((f) => el("tr", {}, el("td", {}, el("b", {}, f.name)), el("td", { class: "num" }, f.kb >= 1024 ? `${(f.kb / 1024).toFixed(1)} MB` : `${f.kb} KB`),
            el("td", { class: "num" }, f.chunks || (d.indexing.busy ? "indexing…" : "0")),
            el("td", { class: "num" }, el("button", { class: "btn danger", type: "button", disabled: d.indexing.busy, onclick: () => removeFile(f.name) }, "Remove")))))))
      : el("p", { class: "empty" }, "No files added yet. Anything you add here is searched together with the course notes."));
    clearTimeout(filesTimer);
    if (d.indexing.busy) filesTimer = setTimeout(() => { if (location.hash === "#files") renderFiles(); else pollIndex(); }, 1500);
    else if (d.indexing.message?.startsWith("Done")) loadStatus();
  } catch (e) { out.replaceChildren(el("p", { class: "error" }, e.message)); }
}
async function pollIndex() {
  try { const d = await api("/api/files"); if (d.indexing.busy) filesTimer = setTimeout(pollIndex, 2000); else loadStatus(); } catch { /* ignore */ }
}
async function waitIndex() {
  for (;;) { const d = await api("/api/files"); showIndexing(d.indexing); if (!d.indexing.busy) return d.indexing; await new Promise((r) => setTimeout(r, 1200)); }
}
const readFile = (f) => new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = () => rej(new Error(`Couldn't read ${f.name}.`)); r.readAsDataURL(f); });
async function uploadFiles(list) {
  const files = [...list].filter((f) => /\.(pdf|md|txt)$/i.test(f.name));
  if (!files.length) { showIndexing({ error: "Only PDF, Markdown (.md) and text (.txt) files can be added." }); return; }
  for (const f of files) {
    try {
      if (f.size > 40 * 1024 * 1024) throw new Error(`${f.name} is over 40 MB.`);
      await waitIndex();
      showIndexing({ busy: true, message: `Uploading ${f.name}…` });
      await api("/api/files", { name: f.name, data: await readFile(f) });
      await renderFiles();
      const ix = await waitIndex();
      if (ix.error) break;
    } catch (e) { showIndexing({ error: e.message }); break; }
  }
  renderFiles();
}
async function removeFile(name) {
  if (!confirm(`Remove ${name} from the knowledge base?`)) return;
  try { await api(`/api/files/${encodeURIComponent(name)}`, null, "DELETE"); } catch (e) { showIndexing({ error: e.message }); }
  renderFiles();
}

/* ------------------------------------------------------------------ shell */
const PAGES = ["chat", "learn", "practice", "progress", "files"];
function route() {
  const page = (location.hash || "#chat").slice(1);
  const valid = PAGES.includes(page) ? page : "chat";
  $$(".page").forEach((p) => (p.hidden = p.id !== `page-${valid}`));
  $$(".nav a").forEach((a) => (a.dataset.page === valid ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  if (!S.status) return;
  if (valid === "learn") renderTopics();
  if (valid === "progress") renderProgress();
  if (valid === "files") renderFiles();
}
function syncLevel() { $$("#level button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.v === S.level))); }

async function loadStatus() {
  const box = $("#status");
  try {
    S.status = await api("/api/status");
    const ix = S.status.indexing || {};
    box.className = `status ${ix.busy ? "busy" : S.status.llm_ok ? "ok" : "bad"}`;
    const kb = S.status.kb;
    box.lastElementChild.textContent = ix.busy ? "Updating the index…" : S.status.llm_ok ? `Ready, ${kb.chunks} passages indexed` : S.status.llm;
    if (!loadStatus.done) { loadStatus.done = true; fillPracticeSelects(); renderSyllabus(); route(); }
  } catch { box.className = "status bad"; box.lastElementChild.textContent = "Server not reachable"; }
}

function showKB() {
  const kb = S.status?.kb; if (!kb) return;
  const groups = { "course notes": "Our course notes", universal: "Open textbooks and documentation", "your files": "Your added files" };
  const mine = kb.sources.filter((s) => s.origin === "your files").length;
  $("#kb-summary").textContent = `${kb.chunks} passages are indexed, covering all nine units of the course. ${kb.universal} come from open sources: chapters of Operating Systems: Three Easy Pieces and Hailperin's Operating Systems and Middleware, Linux man pages and kernel documentation, and Microsoft's Windows scheduling docs.${mine ? ` ${mine} file${mine === 1 ? " is" : "s are"} your own.` : ""} Answers cite the passages they use.`;
  $("#kb-list").replaceChildren(...Object.entries(groups).map(([k, label]) => {
    const items = kb.sources.filter((s) => s.origin === k); if (!items.length) return "";
    return el("div", {}, el("h3", {}, `${label} (${items.length})`), el("ul", {}, items.map((s) => el("li", {}, s.url ? el("a", { href: s.url, target: "_blank", rel: "noopener" }, s.source) : s.source))));
  }));
  $("#kb-modal").showModal();
}

function init() {
  helloNode = $("#hello");
  $("#kb-btn").onclick = showKB;
  $("[data-close]").onclick = () => $("#kb-modal").close();

  const input = $("#input");
  input.addEventListener("input", () => { autosize(); liveMood(); });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (!S.busy) send(input.value); } });
  $("#composer").addEventListener("submit", (e) => { e.preventDefault(); if (S.busy) stopAnswer(); else send(input.value); });
  $("#new-chat").onclick = newChat;
  $("#quiz-btn").onclick = toggleQuizMenu;
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#quiz-menu").hidden) { closeQuizMenu(); $("#quiz-btn").focus(); } });
  document.addEventListener("click", (e) => { if (!$("#quiz-menu").hidden && !e.target.closest(".quiz-wrap")) closeQuizMenu(); });

  $$("#level button").forEach((b) => (b.onclick = () => { S.level = b.dataset.v; syncLevel(); }));
  $("#learn-explain").onclick = () => learn("lesson");
  $("#learn-example").onclick = () => learn("worked_example");
  $("#pick-for-me").onclick = () => newItem({ auto: true });
  $("#p-new").onclick = () => newItem();

  const drop = $("#drop");
  $("#file-input").onchange = (e) => { uploadFiles(e.target.files); e.target.value = ""; };
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); uploadFiles(e.dataTransfer.files); });
  $("#reindex").onclick = async () => { try { await api("/api/reindex", {}); } catch (e) { showIndexing({ error: e.message }); } renderFiles(); };

  window.addEventListener("hashchange", route);
  renderChatList();
  route(); loadStatus();
  setInterval(() => { if (!S.busy) loadStatus(); }, 30000);
}
document.addEventListener("DOMContentLoaded", init);
