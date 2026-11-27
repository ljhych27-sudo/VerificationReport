"""마크다운 요약 (GitHub Actions Job Summary / PR 코멘트 용)."""
from .util import pct, fmt_pct

MARKER = "<!-- verreport-summary -->"
ICON = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️", "NA": "➖"}
MAX_ITEMS = 10


def _md(text):
    """표/목록 안에서 마크다운 문법이 깨지지 않게 이스케이프."""
    return (str(text).replace("\\", "\\\\").replace("|", "\\|").replace("<", "&lt;")
            .replace(">", "&gt;").replace("\n", " ").replace("`", "'"))


def _code(text):
    """`...` 코드 스팬 안에 넣을 텍스트 (HTML 이스케이프는 하지 않음)."""
    return str(text).replace("`", "'").replace("|", "\\|").replace("\n", " ")


def _st(status):
    return f"{ICON[status]} {status if status != 'NA' else '결과 없음'}"


def render_markdown(ctx, report_url=""):
    st, m = ctx["status"], ctx["meta"]
    g, c, k, l = ctx.get("gtest"), ctx.get("coverage"), ctx.get("cppcheck"), ctx.get("lizard")
    out = [MARKER, f"## VERReport 결과: {_st(st['overall'])}", ""]

    rows = []
    if g:
        rows.append(("Google Test", st["gtest"],
                     f"{g['total']:,}개 중 성공 {g['passed']:,} / 실패 {g['failed']:,} / 스킵 {g['skipped']:,}"))
    if c:
        t = c["totals"]
        val = " · ".join(f"{n} {fmt_pct(pct(t[key]['covered'], t[key]['count']))}"
                         for n, key in (("Line", "lines"), ("Function", "functions"), ("Branch", "branches")))
        th = m.get("cov_threshold")
        rows.append(("VVLM 커버리지", st["coverage"], val + (f" (기준 Line {th:g}%)" if th is not None else "")))
    if k:
        rows.append(("CPPCheck", st["cppcheck"],
                     f"{k['total']:,}건 (error {k['counts'].get('error', 0)}, warning {k['counts'].get('warning', 0)})"))
    if l:
        rows.append(("Lizard", st["lizard"],
                     f"위반 함수 {l['violations']:,} / {l['total_functions']:,} "
                     f"(CCN>{l['max_ccn']}: {l['ccn_violations']}, 길이>{l['max_length']}: {l['length_violations']})"))
    out += ["| 도구 | 결과 | 주요 수치 |", "|---|---|---|"]
    out += [f"| {name} | {_st(s)} | {_md(v)} |" for name, s, v in rows]
    out.append("")

    if g and g["failed"]:
        fails = [(s["name"], t) for s in g["suites"] for t in s["tests"] if t["status"] == "failed"]
        out.append(f"<details><summary>실패한 테스트 ({len(fails)})</summary>\n")
        for sname, t in fails[:MAX_ITEMS]:
            loc = f" — `{_code(t['file'].replace(chr(92), '/').split('/')[-1])}:{t['line']}`" if t["file"] else ""
            out.append(f"- `{_code(sname)}.{_code(t['name'])}`{loc}")
        if len(fails) > MAX_ITEMS:
            out.append(f"- … 외 {len(fails) - MAX_ITEMS}건")
        out += ["", "</details>", ""]
    if k and k["counts"].get("error"):
        errs = [i for i in k["issues"] if i["severity"] == "error"]
        out.append(f"<details><summary>CPPCheck error ({len(errs)})</summary>\n")
        for i in errs[:MAX_ITEMS]:
            fn = f" `{_code(i['function'])}()`" if i["function"] else ""
            out.append(f"- `{_code(i['path'])}:{i['line']}`{fn} [{_md(i['id'])}] {_md(i['msg'])}")
        if len(errs) > MAX_ITEMS:
            out.append(f"- … 외 {len(errs) - MAX_ITEMS}건")
        out += ["", "</details>", ""]
    if l and l["violations"]:
        viol = sorted((v for mod in l["modules"].values() for f in mod["files"].values() for v in f["violations"]),
                      key=lambda v: (-v["ccn"], -v["length"]))
        out.append(f"<details><summary>Lizard 위반 상위 {min(len(viol), MAX_ITEMS)}개</summary>\n")
        out += ["| 함수 | 파일 | CCN | 길이 |", "|---|---|---:|---:|"]
        rel = {v["file"]: p for mod in l["modules"].values() for p, f in mod["files"].items() for v in f["violations"]}
        out += [f"| `{_code(v['name'])}` | `{_code(rel.get(v['file'], v['file']))}` | {v['ccn']} | {v['length']} |"
                for v in viol[:MAX_ITEMS]]
        out += ["", "</details>", ""]

    info = [f"빌드 #{m['build_number']}" if m.get("build_number") else "",
            f"`{m['branch']}`" if m.get("branch") else "",
            f"`{m['commit'][:7]}`" if m.get("commit") else "",
            m.get("build_time", "")]
    links = []
    if report_url:
        links.append(f"📊 [전체 리포트 보기]({report_url})")
    if m.get("run_url"):
        links.append(f"[CI 실행 로그]({m['run_url']})")
    out.append(" · ".join(x for x in info if x))
    if links:
        out += ["", " · ".join(links)]
    return "\n".join(out) + "\n"
