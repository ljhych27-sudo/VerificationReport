"""Lizard CSV 파서.

입력: lizard --csv <src> > lizard.csv
CSV 컬럼: NLOC, CCN, token, PARAM, length, location, file, function, long_name, start, end
"""
import csv
from ..util import relativize, module_of, norm


def read_rows(path):
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.reader(f):
            if len(r) < 11 or not r[0].strip().isdigit():
                continue  # 헤더/잘못된 행 무시
            rows.append({"nloc": int(r[0]), "ccn": int(r[1]), "token": int(r[2]),
                         "params": int(r[3]), "length": int(r[4]), "file": r[6],
                         "name": r[7], "long_name": r[8],
                         "start": int(r[9]), "end": int(r[10])})
    return rows


def make_locator(rows):
    """(file, line) -> 함수명. CPPCheck 위반을 함수 단위로 매핑할 때 사용."""
    by_file = {}
    for r in rows:
        by_file.setdefault(norm(r["file"]).lower(), []).append(r)
    keys = list(by_file)

    def locate(file, line):
        k = norm(file).lower()
        if k not in by_file:
            s = k.lstrip("./")
            hits = [x for x in keys if x.endswith("/" + s) or s.endswith("/" + x.lstrip("./"))]
            if len(hits) != 1:
                return ""
            k = hits[0]
        best = ""
        for r in by_file[k]:  # 중첩 함수(람다 등)는 가장 안쪽 것을 선택
            if r["start"] <= line <= r["end"]:
                best = r["name"]
        return best
    return locate


def parse(path, strip_prefix=None, max_ccn=10, max_length=80, rows=None):
    rows = rows if rows is not None else read_rows(path)
    rel = relativize({r["file"] for r in rows}, strip_prefix)
    modules = {}
    n_viol = n_ccn = n_len = 0
    for r in rows:
        p = rel[r["file"]]
        m = modules.setdefault(module_of(p), {"functions": 0, "violations": 0, "files": {}})
        f = m["files"].setdefault(p, {"functions": 0, "violations": []})
        m["functions"] += 1
        f["functions"] += 1
        reasons = []
        if r["ccn"] > max_ccn:
            reasons.append("ccn")
            n_ccn += 1
        if r["length"] > max_length:
            reasons.append("length")
            n_len += 1
        if reasons:
            f["violations"].append(dict(r, reasons=reasons))
            m["violations"] += 1
            n_viol += 1
    for m in modules.values():
        m["files"] = dict(sorted(m["files"].items()))
    return {"total_functions": len(rows), "violations": n_viol,
            "ccn_violations": n_ccn, "length_violations": n_len,
            "max_ccn": max_ccn, "max_length": max_length,
            "modules": dict(sorted(modules.items()))}
