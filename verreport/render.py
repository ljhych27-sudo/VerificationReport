"""HTML 리포트 렌더러 (외부 의존성 없음, 오프라인에서 동작하는 정적 HTML)."""
import html
import os

from .util import pct, fmt_pct
from .parsers.cppcheck import SEVERITIES

PAGES = [("index.html", "대시보드"), ("gtest.html", "Google Test"),
         ("coverage.html", "커버리지"), ("cppcheck.html", "CPPCheck"),
         ("lizard.html", "Lizard")]

STATUS_LABEL = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN", "INFO": "INFO", "NA": "결과 없음"}

CSS = """
:root{--bg:#f5f6f8;--card:#fff;--fg:#1d2330;--muted:#667085;--line:#e3e6eb;--head:#f0f2f5;
--pass:#1f9d55;--fail:#d64545;--warn:#d99a1e;--info:#3b7ddd;--na:#98a2b3;--track:#e8ebef;
--sev-error:#d64545;--sev-warning:#e07b24;--sev-style:#3b7ddd;--sev-performance:#8b5cf6;
--sev-portability:#0e9f9a;--sev-information:#98a2b3}
@media (prefers-color-scheme:dark){:root{--bg:#12151b;--card:#1b2029;--fg:#e6e9ef;--muted:#98a2b3;
--line:#2c333f;--head:#222833;--track:#2c333f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 "Segoe UI","Malgun Gothic",system-ui,sans-serif}
a{color:var(--info);text-decoration:none}
header.top{background:var(--card);border-bottom:1px solid var(--line);padding:14px 24px;display:flex;
flex-wrap:wrap;gap:12px 32px;align-items:center}
header.top h1{font-size:18px;margin:0}
.meta{display:flex;flex-wrap:wrap;gap:4px 20px;color:var(--muted);font-size:13px}
.meta b{color:var(--fg);font-weight:600}
nav{display:flex;gap:4px;padding:0 24px;background:var(--card);border-bottom:1px solid var(--line);overflow-x:auto}
nav a{padding:10px 14px;color:var(--muted);border-bottom:2px solid transparent;white-space:nowrap}
nav a.active{color:var(--fg);border-color:var(--info);font-weight:600}
main{padding:20px 24px;max-width:1400px;margin:0 auto}
h2{font-size:16px;margin:24px 0 10px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;display:flex;flex-direction:column;gap:12px}
.card h3{margin:0;font-size:15px;display:flex;justify-content:space-between;align-items:center}
.card .big{font-size:26px;font-weight:700}
.card .sub{color:var(--muted);font-size:13px}
.card .chart{min-height:130px;display:flex;align-items:center;gap:16px}
.btn{display:inline-block;padding:7px 14px;border-radius:6px;background:var(--info);color:#fff;font-weight:600;
text-align:center;border:0;cursor:pointer;font-size:13px}
.btn.ghost{background:transparent;color:var(--fg);border:1px solid var(--line)}
.card .btn{margin-top:auto}
.badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:700;color:#fff}
.b-PASS{background:var(--pass)}.b-FAIL{background:var(--fail)}.b-WARN{background:var(--warn)}
.b-INFO{background:var(--info)}.b-NA{background:var(--na)}
.badge.big{font-size:14px;padding:4px 14px}
table{width:100%;border-collapse:collapse;background:var(--card)}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:var(--head);font-weight:600;font-size:13px;white-space:nowrap}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tbl{border:1px solid var(--line);border-radius:10px;overflow:auto}
.tbl table{min-width:640px}
.legend{display:flex;flex-direction:column;gap:4px;font-size:13px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
.hbars{display:flex;flex-direction:column;gap:8px;width:100%}
.hbar .lbl{display:flex;justify-content:space-between;font-size:12px;color:var(--muted)}
.hbar .lbl b{color:var(--fg)}
.track{height:10px;background:var(--track);border-radius:5px;overflow:hidden}
.track span{display:block;height:100%;border-radius:5px}
.pbar{display:flex;align-items:center;gap:8px;min-width:150px}
.pbar .track{flex:1;height:8px}
.pbar em{font-style:normal;width:52px;text-align:right;font-variant-numeric:tabular-nums}
.hi{background:var(--pass)}.mid{background:var(--warn)}.lo{background:var(--fail)}
.st-passed{color:var(--pass);font-weight:600}.st-failed{color:var(--fail);font-weight:600}.st-skipped{color:var(--muted)}
.over{color:var(--fail);font-weight:700}
.sev{display:inline-block;padding:1px 7px;border-radius:4px;color:#fff;font-size:12px;font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:4px}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:4px 0 12px}
.toolbar input{flex:1;min-width:220px;padding:8px 10px;border:1px solid var(--line);border-radius:6px;
background:var(--card);color:var(--fg)}
details.mod{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:10px;overflow:hidden}
details.mod>summary{cursor:pointer;padding:10px 14px;display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center;list-style:none}
details.mod>summary::-webkit-details-marker{display:none}
details.mod>summary::before{content:"▸";color:var(--muted)}
details.mod[open]>summary::before{content:"▾"}
details.mod>summary .name{font-weight:700;min-width:160px}
details.mod>summary .stat{color:var(--muted);font-size:13px}
details.mod>summary .stat b{color:var(--fg)}
details.mod>.tbl{border:0;border-top:1px solid var(--line);border-radius:0}
details.mod>.tbl>table>thead th:first-child{width:34%}
tr.row.has-detail{cursor:pointer}
tr.row.has-detail td:first-child::before{content:"▸ ";color:var(--muted)}
tr.row.has-detail.open td:first-child::before{content:"▾ "}
tr.row.has-detail:hover{background:var(--head)}
tr.detail{display:none}
tr.row.open+tr.detail{display:table-row}
tr.detail>td{background:var(--bg);padding:10px 14px 14px 28px}
tr.detail table{border:1px solid var(--line)}
.hide{display:none!important}
pre.msg{margin:0;white-space:pre-wrap;word-break:break-word;font:12px/1.45 Consolas,monospace;color:var(--fail)}
code{font:12px Consolas,monospace}
.empty{padding:40px;text-align:center;color:var(--muted);background:var(--card);border:1px dashed var(--line);border-radius:10px}
footer{color:var(--muted);font-size:12px;text-align:center;padding:24px}
@media (max-width:600px){main,header.top{padding-left:16px;padding-right:16px}nav{padding:0 8px}}
"""

JS = """
document.addEventListener('click',function(e){
  var tr=e.target.closest('tr.row.has-detail'); if(tr) tr.classList.toggle('open');
  var b=e.target.closest('[data-expand]'); if(b){var on=b.dataset.expand==='1';
    document.querySelectorAll('details.mod').forEach(function(d){d.open=on});
    document.querySelectorAll('tr.row.has-detail').forEach(function(r){r.classList.toggle('open',on)});}
});
var q=document.getElementById('q');
if(q){q.addEventListener('input',function(){var t=q.value.trim().toLowerCase();
  document.querySelectorAll('details.mod').forEach(function(d){var any=false;
    var modHit=d.querySelector('summary').textContent.toLowerCase().indexOf(t)>=0;
    d.querySelectorAll('tr.row').forEach(function(r){var nx=r.nextElementSibling;
      var txt=r.textContent+(nx&&nx.classList.contains('detail')?nx.textContent:'');
      var hit=!t||modHit||txt.toLowerCase().indexOf(t)>=0;
      r.classList.toggle('hide',!hit); if(nx&&nx.classList.contains('detail'))nx.classList.toggle('hide',!hit);
      if(hit)any=true;});
    var show=!t||any||modHit; d.classList.toggle('hide',!show); if(t&&any)d.open=true;});});}
"""


def e(v):
    return html.escape("" if v is None else str(v))


def badge(status, big=False):
    return f'<span class="badge b-{status}{" big" if big else ""}">{STATUS_LABEL[status]}</span>'


def level(p):
    return "hi" if p >= 80 else "mid" if p >= 50 else "lo"


def pbar(p):
    if p is None:
        return '<div class="pbar"><div class="track"></div><em>-</em></div>'
    return (f'<div class="pbar"><div class="track"><span class="{level(p)}" style="width:{p:.1f}%"></span>'
            f'</div><em>{p:.1f}%</em></div>')


def cov_cell(t):
    """{"count","covered"} -> 진행바 + (covered/count)."""
    p = pct(t["covered"], t["count"])
    return f'{pbar(p)}<div class="sub" style="font-size:11px;color:var(--muted)">{t["covered"]:,}/{t["count"]:,}</div>'


def donut(segments, center, sub=""):
    """segments: [(label, value, css_color)]. SVG 도넛 차트 + 범례."""
    total = sum(v for _, v, _ in segments)
    arcs, offset = [], 25.0
    for _, v, color in segments:
        if total and v:
            p = 100.0 * v / total
            arcs.append(f'<circle r="15.915" cx="21" cy="21" fill="none" stroke="{color}" stroke-width="5" '
                        f'stroke-dasharray="{p:.3f} {100 - p:.3f}" stroke-dashoffset="{offset:.3f}"/>')
            offset -= p
    svg = (f'<svg viewBox="0 0 42 42" width="130" height="130" role="img" aria-label="{e(center)}">'
           f'<circle r="15.915" cx="21" cy="21" fill="none" stroke="var(--track)" stroke-width="5"/>'
           f'{"".join(arcs)}'
           f'<text x="21" y="21" text-anchor="middle" font-size="7" font-weight="700" fill="var(--fg)">{e(center)}</text>'
           f'<text x="21" y="27.5" text-anchor="middle" font-size="3.4" fill="var(--muted)">{e(sub)}</text></svg>')
    leg = "".join(f'<div><i style="background:{c}"></i>{e(l)} <b>{v:,}</b></div>' for l, v, c in segments)
    return f'{svg}<div class="legend">{leg}</div>'


def hbars(items):
    """items: [(label, value_text, ratio 0..1, css_color_or_class)]."""
    out = []
    for label, text, ratio, color in items:
        style = f"width:{max(0.0, min(1.0, ratio)) * 100:.1f}%"
        cls = ""
        if color in ("hi", "mid", "lo"):
            cls = f' class="{color}"'
        else:
            style += f";background:{color}"
        out.append(f'<div class="hbar"><div class="lbl"><span>{e(label)}</span><b>{e(text)}</b></div>'
                   f'<div class="track"><span{cls} style="{style}"></span></div></div>')
    return f'<div class="hbars">{"".join(out)}</div>'


def table(headers, rows, cls=""):
    """headers: [(text, numeric?)], rows: [[cell_html]] (셀은 이미 escape 된 HTML)."""
    th = "".join(f'<th class="n">{e(h)}</th>' if n else f"<th>{e(h)}</th>" for h, n in headers)
    body = []
    for r in rows:
        body.append("<tr>" + "".join(
            f'<td class="n">{c}</td>' if headers[i][1] else f"<td>{c}</td>" for i, c in enumerate(r)) + "</tr>")
    return f'<div class="tbl {cls}"><table><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def tree_section(name, stats_html, headers, rows, open_=False):
    """모듈 > 파일(행) > 상세(펼침 행) 구조. rows: [(cells, detail_html|None)]."""
    th = "".join(f'<th class="n">{e(h)}</th>' if n else f"<th>{e(h)}</th>" for h, n in headers)
    body = []
    for cells, detail in rows:
        tds = "".join(f'<td class="n">{c}</td>' if headers[i][1] else f"<td>{c}</td>" for i, c in enumerate(cells))
        if detail:
            body.append(f'<tr class="row has-detail">{tds}</tr>'
                        f'<tr class="detail"><td colspan="{len(headers)}">{detail}</td></tr>')
        else:
            body.append(f'<tr class="row">{tds}</tr>')
    tbl = (f'<div class="tbl"><table><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
           if rows else "")
    return (f'<details class="mod"{" open" if open_ else ""}><summary><span class="name">{e(name)}</span>'
            f'{stats_html}</summary>{tbl}</details>')


def stat(label, value):
    return f'<span class="stat">{e(label)} <b>{value}</b></span>'


def sev_chip(sev, n=None):
    txt = e(sev) if n is None else f"{e(sev)} {n}"
    return f'<span class="sev" style="background:var(--sev-{e(sev)},var(--na))">{txt}</span>'


TOOLBAR = ('<div class="toolbar"><input id="q" type="search" placeholder="모듈 / 파일 / 함수 / 메시지 검색">'
           '<button class="btn ghost" data-expand="1">모두 펼치기</button>'
           '<button class="btn ghost" data-expand="0">모두 접기</button></div>')


# ---------------------------------------------------------------- 상태 판정
def statuses(ctx):
    g, c, k, l = ctx.get("gtest"), ctx.get("coverage"), ctx.get("cppcheck"), ctx.get("lizard")
    st = {}
    st["gtest"] = "NA" if g is None else "FAIL" if g["failed"] else "WARN" if not g["total"] else "PASS"
    if c is None:
        st["coverage"] = "NA"
    else:
        th = ctx["meta"].get("cov_threshold")
        lp = pct(c["totals"]["lines"]["covered"], c["totals"]["lines"]["count"]) or 0.0
        st["coverage"] = "INFO" if th is None else "PASS" if lp >= th else "FAIL"
    st["cppcheck"] = "NA" if k is None else "FAIL" if k["counts"].get("error") else "WARN" if k["total"] else "PASS"
    st["lizard"] = "NA" if l is None else "WARN" if l["violations"] else "PASS"
    vals = [v for v in st.values() if v != "NA"]
    st["overall"] = ("FAIL" if "FAIL" in vals else "WARN" if "WARN" in vals else "PASS" if vals else "NA")
    return st


# ---------------------------------------------------------------- 페이지 골격
def link(text, url):
    return f'<a href="{e(url)}" target="_blank" rel="noopener">{e(text)}</a>' if url else e(text)


def header_meta(m):
    """헤더에 표시할 (라벨, HTML) 목록. CI 정보가 있으면 링크로 연결한다."""
    commit = m.get("commit", "")
    build = m.get("build_number", "")
    if build and m.get("run_url"):
        build = link(f"#{build}", m["run_url"])
    else:
        build = e(build)
    return [("프로젝트", e(m.get("project"))),
            ("빌드", build),
            ("빌드 일시", e(m.get("build_time"))),
            ("브랜치", e(m.get("branch"))),
            ("커밋", link(commit[:7] if len(commit) == 40 else commit, m.get("commit_url")) if commit else ""),
            ("PR", link(f"#{m['pr_number']}", m.get("pr_url")) if m.get("pr_number") else ""),
            ("CI", link(m["ci_provider"] + " 실행 보기", m.get("run_url")) if m.get("ci_provider") else "")]


def page(ctx, active, title, body):
    m = ctx["meta"]
    nav = "".join(f'<a href="{f}" class="{"active" if f == active else ""}">{e(t)}</a>' for f, t in PAGES)
    meta_html = "".join(f"<span>{e(k)}: <b>{v}</b></span>" for k, v in header_meta(m) if v)
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} - VERReport</title><style>{CSS}</style></head>
<body><header class="top"><h1>VERReport</h1><div class="meta">{meta_html}</div>
<div style="margin-left:auto">{badge(ctx["status"]["overall"], True)}</div></header>
<nav>{nav}</nav><main>{body}</main>
<footer>생성 일시 {e(m.get("generated"))} · VERReport</footer><script>{JS}</script></body></html>"""


EMPTY_ISSUES = '<div class="empty">위반 사항이 없습니다.</div>'


def no_data(tool):
    return f'<div class="empty">{e(tool)} 결과 파일이 지정되지 않았습니다.</div>'


# ---------------------------------------------------------------- 대시보드
def render_dashboard(ctx):
    st = ctx["status"]
    g, c, k, l = ctx.get("gtest"), ctx.get("coverage"), ctx.get("cppcheck"), ctx.get("lizard")
    cards, summary = [], []

    def card(title, status, big, sub, chart, href):
        inner = (f'<div class="big">{big}</div><div class="sub">{sub}</div><div class="chart">{chart}</div>'
                 if status != "NA" else '<div class="empty" style="padding:30px">결과 없음</div>')
        cards.append(f'<div class="card"><h3>{e(title)} {badge(status)}</h3>{inner}'
                     f'<a class="btn" href="{href}">상세 결과 보기</a></div>')

    # Google Test
    if g:
        rate = pct(g["passed"], g["total"] - g["skipped"])
        card("Google Test", st["gtest"], f'{g["passed"]:,} / {g["total"]:,}',
             f'성공률 {fmt_pct(rate)} · 실행시간 {g["time"]:.2f}s · 스위트 {len(g["suites"])}개',
             donut([("성공", g["passed"], "var(--pass)"), ("실패", g["failed"], "var(--fail)"),
                    ("스킵", g["skipped"], "var(--na)")], fmt_pct(rate), "pass rate"), "gtest.html")
        summary += [["Google Test", "전체 / 성공 / 실패 / 스킵",
                     f'{g["total"]:,} / {g["passed"]:,} / {g["failed"]:,} / {g["skipped"]:,}', st["gtest"], "gtest.html"]]
    else:
        card("Google Test", "NA", "", "", "", "gtest.html")
        summary.append(["Google Test", "-", "-", "NA", "gtest.html"])

    # Coverage
    if c:
        t = c["totals"]
        names = {"lines": "Line", "functions": "Function", "regions": "Region", "branches": "Branch"}
        bars = []
        for key, label in names.items():
            p = pct(t[key]["covered"], t[key]["count"])
            bars.append((label, fmt_pct(p), (p or 0) / 100, level(p or 0) if p is not None else "lo"))
        lp = pct(t["lines"]["covered"], t["lines"]["count"])
        th = ctx["meta"].get("cov_threshold")
        card("VVLM 커버리지", st["coverage"], f"Line {fmt_pct(lp)}",
             f'{len(c["modules"])}개 모듈 · {c["files"]}개 파일' + (f" · 기준 {th:g}%" if th is not None else ""),
             hbars(bars), "coverage.html")
        summary.append(["VVLM 커버리지", "Line / Function / Branch",
                        " / ".join(fmt_pct(pct(t[x]["covered"], t[x]["count"])) for x in ("lines", "functions", "branches")),
                        st["coverage"], "coverage.html"])
    else:
        card("VVLM 커버리지", "NA", "", "", "", "coverage.html")
        summary.append(["VVLM 커버리지", "-", "-", "NA", "coverage.html"])

    # CPPCheck
    if k:
        mx = max(k["counts"].values()) or 1
        card("CPPCheck", st["cppcheck"], f'{k["total"]:,}건',
             f'error {k["counts"].get("error", 0)} · warning {k["counts"].get("warning", 0)}',
             hbars([(s, f'{k["counts"].get(s, 0):,}', k["counts"].get(s, 0) / mx, f"var(--sev-{s})")
                    for s in SEVERITIES]), "cppcheck.html")
        summary.append(["CPPCheck", "위반 (error / warning / 기타)",
                        f'{k["total"]:,} ({k["counts"].get("error", 0)} / {k["counts"].get("warning", 0)} / '
                        f'{k["total"] - k["counts"].get("error", 0) - k["counts"].get("warning", 0)})',
                        st["cppcheck"], "cppcheck.html"])
    else:
        card("CPPCheck", "NA", "", "", "", "cppcheck.html")
        summary.append(["CPPCheck", "-", "-", "NA", "cppcheck.html"])

    # Lizard
    if l:
        ok = l["total_functions"] - l["violations"]
        card("Lizard 복잡도", st["lizard"], f'{l["violations"]:,}개 함수',
             f'분석 함수 {l["total_functions"]:,}개 · CCN &gt; {l["max_ccn"]}, 길이 &gt; {l["max_length"]}',
             donut([(f'CCN > {l["max_ccn"]}', l["ccn_violations"], "var(--fail)"),
                    (f'길이 > {l["max_length"]}', l["length_violations"], "var(--warn)"),
                    ("정상 함수", ok, "var(--pass)")], f'{l["violations"]}', "violations"), "lizard.html")
        summary.append(["Lizard", f'CCN&gt;{l["max_ccn"]} / 길이&gt;{l["max_length"]} / 위반 함수',
                        f'{l["ccn_violations"]:,} / {l["length_violations"]:,} / {l["violations"]:,}',
                        st["lizard"], "lizard.html"])
    else:
        card("Lizard 복잡도", "NA", "", "", "", "lizard.html")
        summary.append(["Lizard", "-", "-", "NA", "lizard.html"])

    rows = [[e(a), b, c_, badge(s), f'<a class="btn ghost" href="{h}">상세 결과 보기</a>']
            for a, b, c_, s, h in summary]
    body = (f'<h2>총괄 결과</h2><div class="grid">{"".join(cards)}</div>'
            f'<h2>도구별 요약</h2>{table([("도구", 0), ("항목", 0), ("값", 0), ("결과", 0), ("상세", 0)], rows)}')
    body += module_matrix(ctx)
    return page(ctx, "index.html", "대시보드", body)


def module_matrix(ctx):
    """커버리지 / CPPCheck / Lizard 결과를 모듈 기준으로 교차 요약."""
    c, k, l = ctx.get("coverage"), ctx.get("cppcheck"), ctx.get("lizard")
    mods = sorted(set((c or {}).get("modules", {})) | set((k or {}).get("modules", {})) |
                  set((l or {}).get("modules", {})))
    if not mods:
        return ""
    rows = []
    for m in mods:
        cm = (c or {}).get("modules", {}).get(m)
        km = (k or {}).get("modules", {}).get(m)
        lm = (l or {}).get("modules", {}).get(m)
        rows.append([
            f"<b>{e(m)}</b>",
            cov_cell(cm["totals"]["lines"]) if cm else "-",
            cov_cell(cm["totals"]["branches"]) if cm else "-",
            f'{km["count"]:,}' if km else ("0" if k else "-"),
            f'{lm["violations"]:,} / {lm["functions"]:,}' if lm else "-",
        ])
    return ("<h2>모듈별 요약</h2>" + table(
        [("모듈", 0), ("Line 커버리지", 0), ("Branch 커버리지", 0), ("CPPCheck 위반", 1),
         ("Lizard 위반 / 분석 함수", 1)], rows))


# ---------------------------------------------------------------- Google Test
def render_gtest(ctx):
    g = ctx.get("gtest")
    if not g:
        return page(ctx, "gtest.html", "Google Test", "<h2>Google Test</h2>" + no_data("Google Test"))
    head = table([("전체", 1), ("성공", 1), ("실패", 1), ("스킵", 1), ("성공률", 0), ("실행시간(s)", 1)],
                 [[f'{g["total"]:,}', f'{g["passed"]:,}', f'{g["failed"]:,}', f'{g["skipped"]:,}',
                   pbar(pct(g["passed"], g["total"] - g["skipped"])), f'{g["time"]:.3f}']])
    sections = []
    for s in sorted(g["suites"], key=lambda x: (-x["failed"], x["name"])):
        rows = []
        for t in sorted(s["tests"], key=lambda x: ({"failed": 0, "skipped": 1}.get(x["status"], 2), x["name"])):
            loc = f'{t["file"]}:{t["line"]}' if t["file"] else ""
            detail = f'<pre class="msg">{e(t["message"])}</pre>' if t["status"] == "failed" and t["message"] else None
            rows.append(([e(t["name"]), f'<span class="st-{t["status"]}">{t["status"].upper()}</span>',
                          f"<code>{e(loc)}</code>", f'{t["time"]:.3f}'], detail))
        stats = (stat("전체", s["total"]) + stat("성공", s["passed"]) + stat("실패", s["failed"]) +
                 stat("스킵", s["skipped"]) + stat("시간", f'{s["time"]:.3f}s') +
                 (badge("FAIL") if s["failed"] else badge("PASS")))
        sections.append(tree_section(s["name"], stats, [("테스트 케이스", 0), ("결과", 0), ("위치", 0),
                                                         ("시간(s)", 1)], rows, open_=bool(s["failed"])))
    body = (f'<h2>Google Test 결과 {badge(ctx["status"]["gtest"])}</h2>{head}'
            f'<h2>테스트 스위트 &gt; 테스트 케이스</h2>{TOOLBAR}{"".join(sections)}')
    return page(ctx, "gtest.html", "Google Test", body)


# ---------------------------------------------------------------- Coverage
def render_coverage(ctx):
    c = ctx.get("coverage")
    if not c:
        return page(ctx, "coverage.html", "커버리지", "<h2>VVLM 커버리지</h2>" + no_data("커버리지"))
    t = c["totals"]
    keys = ("lines", "functions", "regions", "branches")
    hdr = [("구분", 0), ("Line", 0), ("Function", 0), ("Region", 0), ("Branch", 0)]
    head = table(hdr, [["<b>전체</b>"] + [cov_cell(t[x]) for x in keys]] +
                 [[e(m)] + [cov_cell(v["totals"][x]) for x in keys] for m, v in c["modules"].items()])
    sections = []
    for m, v in c["modules"].items():
        rows = []
        for f in v["files"]:
            detail = None
            if f["functions"]:
                detail = table([("함수", 0), ("라인", 1), ("실행 횟수", 1), ("Region 커버리지", 0)],
                               [[f'<code>{e(fn["name"])}</code>', f'{fn["line"]}', f'{fn["count"]:,}',
                                 pbar(fn["percent"])] for fn in f["functions"]])
            rows.append(([f'<code>{e(f["name"])}</code>'] + [cov_cell(f["totals"][x]) for x in keys], detail))
        lp = pct(v["totals"]["lines"]["covered"], v["totals"]["lines"]["count"])
        stats = (stat("파일", len(v["files"])) + stat("Line", fmt_pct(lp)) +
                 stat("Function", fmt_pct(pct(v["totals"]["functions"]["covered"], v["totals"]["functions"]["count"]))) +
                 stat("Branch", fmt_pct(pct(v["totals"]["branches"]["covered"], v["totals"]["branches"]["count"]))))
        sections.append(tree_section(m, stats, [("파일", 0)] + hdr[1:], rows))
    note = "" if c["has_functions"] else \
        '<p class="sub">함수 단위 결과가 없습니다. <code>llvm-cov export</code> 시 -summary-only 를 빼면 표시됩니다.</p>'
    body = (f'<h2>VVLM 커버리지 {badge(ctx["status"]["coverage"])}</h2>{head}'
            f'<h2>모듈 &gt; 파일 &gt; 함수</h2>{note}{TOOLBAR}{"".join(sections)}')
    return page(ctx, "coverage.html", "커버리지", body)


# ---------------------------------------------------------------- CPPCheck
def render_cppcheck(ctx):
    k = ctx.get("cppcheck")
    if not k:
        return page(ctx, "cppcheck.html", "CPPCheck", "<h2>CPPCheck</h2>" + no_data("CPPCheck"))
    head = table([(s, 1) for s in SEVERITIES] + [("합계", 1)],
                 [[f'{k["counts"].get(s, 0):,}' for s in SEVERITIES] + [f'<b>{k["total"]:,}</b>']])
    by_id = {}
    for i in k["issues"]:
        d = by_id.setdefault(i["id"], {"severity": i["severity"], "n": 0, "msg": i["msg"]})
        d["n"] += 1
    rules = table([("규칙 ID", 0), ("심각도", 0), ("건수", 1), ("메시지 예시", 0)],
                  [[f'<code>{e(rid)}</code>', sev_chip(d["severity"]), f'{d["n"]:,}', e(d["msg"])]
                   for rid, d in sorted(by_id.items(), key=lambda x: (SEVERITIES.index(x[1]["severity"])
                                                                       if x[1]["severity"] in SEVERITIES else 99,
                                                                       -x[1]["n"]))])
    sections = []
    for m, v in k["modules"].items():
        rows, sev_tot = [], {}
        for path, issues in v["files"].items():
            sc = {}
            for i in issues:
                sc[i["severity"]] = sc.get(i["severity"], 0) + 1
                sev_tot[i["severity"]] = sev_tot.get(i["severity"], 0) + 1
            detail = table([("라인", 1), ("함수", 0), ("심각도", 0), ("규칙 ID", 0), ("메시지", 0), ("CWE", 1)],
                           [[str(i["line"]), f'<code>{e(i["function"] or "-")}</code>', sev_chip(i["severity"]),
                             f'<code>{e(i["id"])}</code>', e(i["msg"]), e(i["cwe"] or "-")] for i in issues])
            chips = "".join(sev_chip(s, sc[s]) for s in SEVERITIES if sc.get(s))
            rows.append(([f'<code>{e(path)}</code>', f'{len(issues):,}', f'<div class="chips">{chips}</div>'], detail))
        stats = stat("파일", len(v["files"])) + stat("위반", f'{v["count"]:,}') + \
            '<span class="chips">' + "".join(sev_chip(s, sev_tot[s]) for s in SEVERITIES if sev_tot.get(s)) + "</span>"
        sections.append(tree_section(m, stats, [("파일", 0), ("위반 수", 1), ("심각도별", 0)], rows,
                                     open_=bool(sev_tot.get("error"))))
    ver = f' <span class="sub">(cppcheck {e(k["version"])})</span>' if k["version"] else ""
    body = (f'<h2>CPPCheck 위반 사항 {badge(ctx["status"]["cppcheck"])}{ver}</h2>{head}'
            f'<h2>규칙별 통계</h2>{rules}'
            f'<h2>모듈 &gt; 파일 &gt; 위반(함수)</h2>{TOOLBAR}'
            f'{"".join(sections) or EMPTY_ISSUES}')
    return page(ctx, "cppcheck.html", "CPPCheck", body)


# ---------------------------------------------------------------- Lizard
def render_lizard(ctx):
    l = ctx.get("lizard")
    if not l:
        return page(ctx, "lizard.html", "Lizard", "<h2>Lizard</h2>" + no_data("Lizard"))
    mc, ml = l["max_ccn"], l["max_length"]
    head = table([("분석 함수", 1), (f"CCN > {mc}", 1), (f"함수 길이 > {ml}", 1), ("위반 함수(중복 제외)", 1)],
                 [[f'{l["total_functions"]:,}', f'{l["ccn_violations"]:,}', f'{l["length_violations"]:,}',
                   f'<b>{l["violations"]:,}</b>']])
    sections = []
    for m, v in l["modules"].items():
        rows = []
        for path, f in v["files"].items():
            vs = f["violations"]
            if not vs:
                continue
            detail = table([("함수", 0), ("라인", 1), ("CCN", 1), ("길이", 1), ("NLOC", 1), ("파라미터", 1), ("위반", 0)],
                           [[f'<code title="{e(x["long_name"])}">{e(x["name"])}</code>', f'{x["start"]}-{x["end"]}',
                             f'<span class="{"over" if x["ccn"] > mc else ""}">{x["ccn"]}</span>',
                             f'<span class="{"over" if x["length"] > ml else ""}">{x["length"]}</span>',
                             str(x["nloc"]), str(x["params"]),
                             ", ".join({"ccn": f"CCN&gt;{mc}", "length": f"길이&gt;{ml}"}[r] for r in x["reasons"])]
                            for x in sorted(vs, key=lambda x: (-x["ccn"], -x["length"]))])
            rows.append(([f'<code>{e(path)}</code>', f'{f["functions"]:,}', f'{len(vs):,}',
                          str(max(x["ccn"] for x in vs)), str(max(x["length"] for x in vs))], detail))
        stats = stat("분석 함수", f'{v["functions"]:,}') + stat("위반 함수", f'{v["violations"]:,}') + \
            (badge("WARN") if v["violations"] else badge("PASS"))
        sections.append(tree_section(m, stats, [("파일", 0), ("분석 함수", 1), ("위반 함수", 1), ("최대 CCN", 1),
                                                ("최대 길이", 1)], rows))
    body = (f'<h2>Lizard 복잡도 (CCN &gt; {mc}, 함수 라인 수 &gt; {ml}) {badge(ctx["status"]["lizard"])}</h2>{head}'
            f'<h2>모듈 &gt; 파일 &gt; 함수</h2>{TOOLBAR}{"".join(sections)}')
    return page(ctx, "lizard.html", "Lizard", body)


def write_report(ctx, out_dir):
    ctx["status"] = statuses(ctx)
    os.makedirs(out_dir, exist_ok=True)
    renderers = {"index.html": render_dashboard, "gtest.html": render_gtest, "coverage.html": render_coverage,
                 "cppcheck.html": render_cppcheck, "lizard.html": render_lizard}
    for name, fn in renderers.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(fn(ctx))
    return os.path.join(out_dir, "index.html")
