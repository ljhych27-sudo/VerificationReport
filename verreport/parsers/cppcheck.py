"""CPPCheck XML(version 2) 파서.

입력: cppcheck --xml --xml-version=2 <src> 2> cppcheck.xml
"""
import xml.etree.ElementTree as ET
from ..util import relativize, module_of

SEVERITIES = ("error", "warning", "style", "performance", "portability", "information")


def parse(path, strip_prefix=None, locate_function=None):
    """locate_function(file, line) -> 함수명. (선택: Lizard 결과로 위반 위치를 함수에 매핑)"""
    root = ET.parse(path).getroot()
    ver = root.find("cppcheck")
    raw = []
    for e in root.iter("error"):
        loc = e.find("location")
        raw.append({
            "id": e.get("id", ""), "severity": e.get("severity", ""),
            "msg": e.get("msg", ""), "cwe": e.get("cwe", ""),
            "file": loc.get("file", "") if loc is not None else (e.get("file0") or ""),
            "line": int(loc.get("line", 0) or 0) if loc is not None else 0,
        })
    rel = relativize({r["file"] for r in raw if r["file"]}, strip_prefix)
    for r in raw:
        if r["file"]:
            r["path"] = rel[r["file"]]
            r["module"] = module_of(r["path"])
            r["function"] = locate_function(r["file"], r["line"]) if locate_function else ""
        else:
            r["path"] = r["module"] = "(global)"
            r["function"] = ""
    counts = {s: 0 for s in SEVERITIES}
    for r in raw:
        counts[r["severity"]] = counts.get(r["severity"], 0) + 1
    modules = {}
    for r in sorted(raw, key=lambda x: (x["path"], x["line"])):
        m = modules.setdefault(r["module"], {"files": {}, "count": 0})
        m["files"].setdefault(r["path"], []).append(r)
        m["count"] += 1
    return {"version": ver.get("version", "") if ver is not None else "",
            "issues": raw, "total": len(raw), "counts": counts,
            "modules": dict(sorted(modules.items()))}
