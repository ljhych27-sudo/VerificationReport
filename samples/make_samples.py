"""데모용 예제 입력 파일 생성기 (실제 도구 출력 형식과 동일).

python samples/make_samples.py
"""
import csv
import json
import os
import random
from xml.sax.saxutils import quoteattr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "C:/build/demo/src"
rnd = random.Random(42)

MODULES = {
    "core": ["scheduler.c", "task.c", "timer.c"],
    "comm": ["can.c", "uart.c", "protocol.c"],
    "diag": ["dtc.c", "uds.c"],
    "util": ["crc.c", "ringbuf.c", "str_util.c"],
}

# 파일별 함수 목록 (이름, 시작라인, 끝라인, CCN, NLOC)
FUNCS = {}
for mod, files in MODULES.items():
    for fn in files:
        path = f"{ROOT}/{mod}/{fn}"
        base = fn[:-2]
        line, funcs = 10, []
        for i in range(rnd.randint(4, 9)):
            length = rnd.choice([8, 12, 20, 25, 35, 45, 60]) if rnd.random() > 0.12 else rnd.randint(81, 160)
            ccn = rnd.randint(1, 8) if rnd.random() > 0.15 else rnd.randint(11, 27)
            funcs.append((f"{base}_{['init', 'process', 'handle', 'update', 'check', 'parse', 'send', 'reset', 'get'][i]}",
                          line, line + length - 1, ccn, int(length * 0.8)))
            line += length + 3
        FUNCS[path] = funcs


def lizard_csv():
    with open(os.path.join(HERE, "lizard.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["NLOC", "CCN", "token", "PARAM", "length", "location", "file", "function",
                    "long_name", "start", "end"])
        for path, funcs in FUNCS.items():
            for name, s, e, ccn, nloc in funcs:
                params = rnd.randint(0, 4)
                w.writerow([nloc, ccn, nloc * 6, params, e - s + 1, f"{name}@{s}-{e}@{path}", path, name,
                            f"{name}( {', '.join('int a%d' % i for i in range(params))} )", s, e])


def coverage_json():
    files, functions = [], []
    for path, funcs in FUNCS.items():
        quality = rnd.uniform(0.35, 0.98)
        lines_c = lines_n = f_cov = br_c = br_n = rg_c = rg_n = 0
        for name, s, e, ccn, nloc in funcs:
            executed = rnd.random() < quality + 0.1
            regs = []
            nreg = ccn * 2 + 1
            for r in range(nreg):
                ls = s + 1 + r * max(1, (e - s - 2) // nreg)
                cnt = rnd.randint(1, 500) if executed and rnd.random() < quality + 0.05 else 0
                regs.append([ls, 5, ls + 1, 20, cnt, 0, 0, 0])
            regs[0] = [s, 1, e, 2, rnd.randint(1, 900) if executed else 0, 0, 0, 0]
            functions.append({"name": name, "count": regs[0][4], "regions": regs,
                              "branches": [], "filenames": [path]})
            c = sum(1 for r in regs if r[4] > 0)
            rg_c, rg_n = rg_c + c, rg_n + nreg
            f_cov += 1 if executed else 0
            lines_n += nloc
            lines_c += int(nloc * (c / nreg)) if executed else 0
            br_n += (ccn - 1) * 2
            br_c += int((ccn - 1) * 2 * (c / nreg)) if executed else 0

        def s_(c, n):
            return {"count": n, "covered": c, "percent": 100.0 * c / n if n else 0}
        files.append({"filename": path, "segments": [], "branches": [], "expansions": [],
                      "summary": {"lines": s_(lines_c, lines_n), "functions": s_(f_cov, len(funcs)),
                                  "instantiations": s_(f_cov, len(funcs)), "regions": s_(rg_c, rg_n),
                                  "branches": s_(br_c, br_n)}})
    data = {"type": "llvm.coverage.json.export", "version": "2.0.1",
            "data": [{"files": files, "functions": functions, "totals": {}}]}
    with open(os.path.join(HERE, "coverage.json"), "w", encoding="utf-8") as f:
        json.dump(data, f)


def cppcheck_xml():
    rules = [("error", "nullPointer", "Null pointer dereference: p", "476"),
             ("error", "arrayIndexOutOfBounds", "Array 'buf[16]' accessed at index 16, which is out of bounds.", "788"),
             ("warning", "uninitvar", "Uninitialized variable: len", "457"),
             ("warning", "shiftTooManyBits", "Shifting 32-bit value by 32 bits is undefined behaviour", "758"),
             ("style", "variableScope", "The scope of the variable 'i' can be reduced.", "398"),
             ("style", "constParameter", "Parameter 'cfg' can be declared as pointer to const", "398"),
             ("style", "unusedFunction", "The function 'debug_dump' is never used.", "561"),
             ("performance", "passedByValue", "Function parameter 'msg' should be passed by const reference.", "398"),
             ("portability", "invalidPointerCast", "Casting from float * to int * is not portable", "704"),
             ("information", "missingIncludeSystem", "Include file: <stdint.h> not found.", "")]
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<results version="2">',
           '    <cppcheck version="2.14.0"/>', '    <errors>']
    for path, funcs in FUNCS.items():
        for _ in range(rnd.randint(0, 6)):
            sev, rid, msg, cwe = rnd.choice(rules[:-1])
            name, s, e, *_ = rnd.choice(funcs)
            line = rnd.randint(s, e)
            out.append(f'        <error id="{rid}" severity="{sev}" msg={quoteattr(msg)} verbose={quoteattr(msg)}'
                       + (f' cwe="{cwe}"' if cwe else "") + f' file0={quoteattr(path)}>')
            out.append(f'            <location file={quoteattr(path)} line="{line}" column="5"/>')
            out.append("        </error>")
    sev, rid, msg, _ = rules[-1]
    out.append(f'        <error id="{rid}" severity="{sev}" msg={quoteattr(msg)} verbose={quoteattr(msg)}/>')
    out += ["    </errors>", "</results>"]
    with open(os.path.join(HERE, "cppcheck.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def gtest_files():
    suites = {"SchedulerTest": "core", "TimerTest": "core", "TaskTest": "core",
              "CrcTest": "util", "RingBufferTest": "util", "DtcTest": "diag"}
    out = ['<?xml version="1.0" encoding="UTF-8"?>']
    all_cases = []
    for sname, mod in suites.items():
        cases = []
        for i in range(rnd.randint(4, 10)):
            r = rnd.random()
            st = "failed" if r < 0.07 else "skipped" if r < 0.12 else "passed"
            cases.append((f"Case{i + 1:02d}_{rnd.choice(['Basic', 'Boundary', 'Overflow', 'Timeout', 'Invalid'])}",
                          st, round(rnd.uniform(0, 0.05), 3), mod))
        all_cases.append((sname, cases))
    total = sum(len(c) for _, c in all_cases)
    fails = sum(1 for _, c in all_cases for x in c if x[1] == "failed")
    out.append(f'<testsuites tests="{total}" failures="{fails}" disabled="0" errors="0" time="1.234" '
               f'timestamp="2026-11-27T09:12:33" name="AllTests">')
    for sname, cases in all_cases:
        f = sum(1 for x in cases if x[1] == "failed")
        out.append(f'  <testsuite name="{sname}" tests="{len(cases)}" failures="{f}" disabled="0" skipped="0" '
                   f'errors="0" time="0.1">')
        for i, (cname, st, t, mod) in enumerate(cases):
            fpath = f"C:/build/demo/test/{mod}/{sname[:-4].lower()}_test.cpp"
            attrs = (f'name="{cname}" file="{fpath}" line="{20 + i * 15}" status="run" result="completed" '
                     f'time="{t}" timestamp="2026-11-27T09:12:33" classname="{sname}"')
            if st == "passed":
                out.append(f"    <testcase {attrs} />")
            elif st == "skipped":
                out.append(f'    <testcase {attrs.replace("completed", "skipped")}>\n      <skipped message="" />\n    </testcase>')
            else:
                msg = f"{fpath}:{22 + i * 15}\nExpected equality of these values:\n  expected\n    Which is: 16\n  actual\n    Which is: 15"
                out.append(f"    <testcase {attrs}>\n      <failure message={quoteattr(msg)} type=\"\"></failure>\n    </testcase>")
        out.append("  </testsuite>")
    out.append("</testsuites>")
    with open(os.path.join(HERE, "gtest_core.xml"), "w", encoding="utf-8") as fp:
        fp.write("\n".join(out) + "\n")

    # 두 번째 테스트 실행파일은 JSON 형식 (--gtest_output=json)
    js = {"tests": 0, "testsuites": []}
    for sname in ("CanTest", "UartTest", "ProtocolTest"):
        cases = []
        for i in range(rnd.randint(4, 8)):
            c = {"name": f"Case{i + 1:02d}", "file": f"C:/build/demo/test/comm/{sname[:-4].lower()}_test.cpp",
                 "line": 30 + i * 12, "status": "RUN", "result": "COMPLETED",
                 "time": f"{rnd.uniform(0, 0.03):.3f}s", "classname": sname}
            if rnd.random() < 0.08:
                c["failures"] = [{"failure": "protocol_test.cpp:88\nValue of: rx_ok\n  Actual: false\nExpected: true",
                                  "type": ""}]
            if rnd.random() < 0.05:
                c["status"], c["result"] = "NOTRUN", "SUPPRESSED"
            cases.append(c)
        js["testsuites"].append({"name": sname, "tests": len(cases), "testsuite": cases})
    with open(os.path.join(HERE, "gtest_comm.json"), "w", encoding="utf-8") as fp:
        json.dump(js, fp, indent=1)


if __name__ == "__main__":
    lizard_csv()
    coverage_json()
    cppcheck_xml()
    gtest_files()
    print("samples generated in", HERE)
