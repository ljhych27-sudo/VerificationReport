"""LLVM 커버리지(llvm-cov export JSON) 파서.

입력: llvm-cov export -format=text <binary> -instr-profile=x.profdata > coverage.json
함수 단위 결과가 필요하면 -summary-only 옵션을 사용하지 않는다.
"""
import json
from ..util import relativize, module_of, pct

KEYS = ("lines", "functions", "regions", "branches")


def _empty():
    return {k: {"count": 0, "covered": 0} for k in KEYS}


def _tot(summary):
    t = _empty()
    for k in KEYS:
        t[k]["count"] = summary.get(k, {}).get("count", 0)
        t[k]["covered"] = summary.get(k, {}).get("covered", 0)
    return t


def _add(a, b):
    for k in KEYS:
        a[k]["count"] += b[k]["count"]
        a[k]["covered"] += b[k]["covered"]


def parse(path, strip_prefix=None):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)["data"][0]
    files = data.get("files", [])
    rel = relativize([f["filename"] for f in files], strip_prefix)

    # 함수 단위: region = [lineStart, colStart, lineEnd, colEnd, count, fileId, expFileId, kind]
    funcs_by_file = {}
    for fn in data.get("functions", []):
        all_regs = fn.get("regions", [])
        regs = [r for r in all_regs if len(r) > 7 and r[7] == 0]  # CodeRegion 만
        covered = sum(1 for r in regs if r[4] > 0)
        line = all_regs[0][0] if all_regs else 0
        end = max((r[2] for r in regs), default=line)
        for fname in fn.get("filenames", [])[:1]:
            funcs_by_file.setdefault(fname, []).append({
                "name": fn.get("name", ""), "line": line, "end": end,
                "count": fn.get("count", 0), "regions": len(regs),
                "regions_covered": covered, "percent": pct(covered, len(regs))})

    modules = {}
    for f in files:
        r = rel[f["filename"]]
        t = _tot(f.get("summary", {}))
        fns = sorted(funcs_by_file.get(f["filename"], []), key=lambda x: x["line"])
        m = modules.setdefault(module_of(r), {"totals": _empty(), "files": []})
        _add(m["totals"], t)
        m["files"].append({"name": r, "totals": t, "functions": fns})
    totals = _empty()
    for m in modules.values():
        _add(totals, m["totals"])
        m["files"].sort(key=lambda x: x["name"])
    return {"totals": totals, "modules": dict(sorted(modules.items())),
            "files": sum(len(m["files"]) for m in modules.values()),
            "has_functions": bool(data.get("functions"))}
