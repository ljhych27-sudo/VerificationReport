import os
import tempfile
import unittest

from verreport import cli
from verreport.parsers import gtest, llvmcov, cppcheck, lizard
from verreport.util import relativize, module_of

SAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def sample(name):
    return os.path.join(SAMPLES, name)


class UtilTest(unittest.TestCase):
    def test_relativize_and_module(self):
        rel = relativize(["C:\\src\\core\\a.c", "C:/src/util/b.c"])
        self.assertEqual(rel["C:\\src\\core\\a.c"], "core/a.c")
        self.assertEqual(module_of("core/a.c"), "core")
        self.assertEqual(module_of("a.c"), "(root)")


class ParserTest(unittest.TestCase):
    def test_gtest_xml_and_json_merge(self):
        r = gtest.parse([sample("gtest_core.xml"), sample("gtest_comm.json")])
        self.assertEqual(r["total"], r["passed"] + r["failed"] + r["skipped"])
        self.assertGreater(r["failed"], 0)
        self.assertIn("CanTest", [s["name"] for s in r["suites"]])

    def test_coverage(self):
        r = llvmcov.parse(sample("coverage.json"))
        self.assertEqual(set(r["modules"]), {"core", "comm", "diag", "util"})
        lines = sum(m["totals"]["lines"]["count"] for m in r["modules"].values())
        self.assertEqual(lines, r["totals"]["lines"]["count"])
        self.assertTrue(r["modules"]["core"]["files"][0]["functions"])

    def test_lizard_thresholds(self):
        r = lizard.parse(sample("lizard.csv"), max_ccn=10, max_length=80)
        rows = lizard.read_rows(sample("lizard.csv"))
        expected = sum(1 for x in rows if x["ccn"] > 10 or x["length"] > 80)
        self.assertEqual(r["violations"], expected)
        self.assertEqual(r["total_functions"], len(rows))

    def test_cppcheck_function_mapping(self):
        loc = lizard.make_locator(lizard.read_rows(sample("lizard.csv")))
        r = cppcheck.parse(sample("cppcheck.xml"), locate_function=loc)
        self.assertEqual(r["total"], sum(r["counts"].values()))
        located = [i for i in r["issues"] if i["file"]]
        self.assertTrue(all(i["function"] for i in located))
        self.assertIn("(global)", r["modules"])


class EndToEndTest(unittest.TestCase):
    def test_demo_report(self):
        with tempfile.TemporaryDirectory() as d:
            rc = cli.main(["--demo", "-o", d, "--build-time", "2026-01-02 03:04:05"])
            self.assertEqual(rc, 0)
            for f in ("index.html", "gtest.html", "coverage.html", "cppcheck.html", "lizard.html"):
                self.assertTrue(os.path.exists(os.path.join(d, f)))
            idx = read(os.path.join(d, "index.html"))
            self.assertIn("2026-01-02 03:04:05", idx)
            self.assertIn("상세 결과 보기", idx)
            self.assertIn("<svg", idx)

    def test_fail_on_error_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(cli.main(["--demo", "-o", d, "--fail-on-error"]), 1)

    def test_single_tool_only(self):
        with tempfile.TemporaryDirectory() as d:
            cli.main(["--lizard", sample("lizard.csv"), "-o", d])
            html = read(os.path.join(d, "gtest.html"))
            self.assertIn("결과 파일이 지정되지 않았습니다", html)


if __name__ == "__main__":
    unittest.main()
