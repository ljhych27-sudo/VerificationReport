"""Google Test 결과 파서 (--gtest_output=xml:... 또는 json:...)."""
import json
import xml.etree.ElementTree as ET


def _num(v):
    try:
        return float(str(v).rstrip("s"))
    except (TypeError, ValueError):
        return 0.0


def _parse_xml(path):
    suites = []
    for ts in ET.parse(path).getroot().iter("testsuite"):
        tests = []
        for tc in ts.findall("testcase"):
            fails = tc.findall("failure")
            if fails:
                status = "failed"
                msg = "\n".join((f.get("message") or f.text or "") for f in fails).strip()
            elif (tc.find("skipped") is not None or tc.get("status") == "notrun"
                  or tc.get("result") in ("suppressed", "skipped")):
                status, msg = "skipped", ""
            else:
                status, msg = "passed", ""
            tests.append({"name": tc.get("name", ""), "status": status,
                          "time": _num(tc.get("time")), "file": tc.get("file", ""),
                          "line": tc.get("line", ""), "message": msg})
        suites.append({"name": ts.get("name", ""), "tests": tests})
    return suites


def _parse_json(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    suites = []
    for ts in data.get("testsuites", []):
        tests = []
        for tc in ts.get("testsuite", []):
            fails = tc.get("failures") or []
            if fails:
                status = "failed"
                msg = "\n".join(x.get("failure", "") for x in fails)
            elif tc.get("status") == "NOTRUN" or tc.get("result") in ("SUPPRESSED", "SKIPPED"):
                status, msg = "skipped", ""
            else:
                status, msg = "passed", ""
            tests.append({"name": tc.get("name", ""), "status": status,
                          "time": _num(tc.get("time")), "file": tc.get("file", ""),
                          "line": str(tc.get("line", "")), "message": msg})
        suites.append({"name": ts.get("name", ""), "tests": tests})
    return suites


def parse(paths):
    """하나 이상의 결과 파일(테스트 실행파일별)을 병합해 반환."""
    suites = []
    for p in paths:
        suites += _parse_json(p) if p.lower().endswith(".json") else _parse_xml(p)
    for s in suites:
        for k in ("passed", "failed", "skipped"):
            s[k] = sum(1 for t in s["tests"] if t["status"] == k)
        s["total"] = len(s["tests"])
        s["time"] = sum(t["time"] for t in s["tests"])
    tests = [t for s in suites for t in s["tests"]]
    return {
        "suites": suites,
        "total": len(tests),
        "passed": sum(s["passed"] for s in suites),
        "failed": sum(s["failed"] for s in suites),
        "skipped": sum(s["skipped"] for s in suites),
        "time": sum(t["time"] for t in tests),
    }
