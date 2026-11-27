import os
import subprocess
import sys
import tempfile
import unittest

import json
from unittest import mock

from verreport import cli, ci
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
            rc = cli.main(["--demo", "-o", d, "--build-time", "2026-01-02 03:04:05", "--no-ci-detect"])
            self.assertEqual(rc, 0)
            for f in ("index.html", "gtest.html", "coverage.html", "cppcheck.html", "lizard.html"):
                self.assertTrue(os.path.exists(os.path.join(d, f)))
            idx = read(os.path.join(d, "index.html"))
            self.assertIn("2026-01-02 03:04:05", idx)
            self.assertIn("상세 결과 보기", idx)
            self.assertIn("<svg", idx)

    def test_fail_on_error_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(cli.main(["--demo", "-o", d, "--fail-on-error", "--no-ci-detect"]), 1)

    def test_non_utf8_console(self):
        """한글을 표현 못 하는 콘솔(cp1252)에서도 CLI 가 죽지 않아야 한다."""
        root = os.path.dirname(SAMPLES)
        env = dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONUTF8="0")
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, "-m", "verreport", "--demo", "-o", d, "--no-ci-detect"],
                               cwd=root, env=env, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr.decode("cp1252", "replace"))

    def test_single_tool_only(self):
        with tempfile.TemporaryDirectory() as d:
            cli.main(["--lizard", sample("lizard.csv"), "-o", d, "--no-ci-detect"])
            html = read(os.path.join(d, "gtest.html"))
            self.assertIn("결과 파일이 지정되지 않았습니다", html)


GH_ENV = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "acme/firmware", "GITHUB_RUN_ID": "99",
          "GITHUB_RUN_NUMBER": "42", "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": "m" * 40,
          "GITHUB_REF_NAME": "7/merge", "GITHUB_HEAD_REF": "feature/x", "GITHUB_SERVER_URL": "https://github.com",
          "GITHUB_EVENT_NAME": "pull_request"}


class CiTest(unittest.TestCase):
    def test_not_ci(self):
        self.assertIsNone(ci.detect({}))

    def test_github_pull_request(self):
        with tempfile.TemporaryDirectory() as d:
            ev = os.path.join(d, "event.json")
            with open(ev, "w", encoding="utf-8") as f:
                json.dump({"pull_request": {"number": 7, "html_url": "https://github.com/acme/firmware/pull/7",
                                            "head": {"sha": "h" * 40}}}, f)
            info = ci.detect(dict(GH_ENV, GITHUB_EVENT_PATH=ev))
        self.assertEqual(info["build_number"], "42")
        self.assertEqual(info["branch"], "feature/x")
        self.assertEqual(info["commit"], "h" * 40)  # 머지 커밋이 아닌 PR head
        self.assertEqual(info["pr_number"], "7")
        self.assertEqual(info["run_url"], "https://github.com/acme/firmware/actions/runs/99")
        self.assertEqual(info["project"], "firmware")

    def test_jenkins_and_gitlab(self):
        j = ci.detect({"JENKINS_URL": "x", "BUILD_NUMBER": "5", "GIT_BRANCH": "origin/dev", "BUILD_URL": "u"})
        self.assertEqual((j["build_number"], j["branch"], j["run_url"]), ("5", "dev", "u"))
        g = ci.detect({"GITLAB_CI": "true", "CI_PIPELINE_IID": "3", "CI_COMMIT_REF_NAME": "main"})
        self.assertEqual((g["provider"], g["build_number"]), ("GitLab CI", "3"))

    def test_cli_in_github_actions(self):
        with tempfile.TemporaryDirectory() as d:
            step = os.path.join(d, "step.md")
            env = dict(GH_ENV, GITHUB_STEP_SUMMARY=step, GITHUB_EVENT_NAME="push", GITHUB_HEAD_REF="",
                       GITHUB_REF_NAME="main")
            with mock.patch.dict(os.environ, env, clear=False):
                os.environ.pop("GITHUB_EVENT_PATH", None)
                cli.main(["--demo", "-o", os.path.join(d, "r"), "--report-url", "https://acme.github.io/r/",
                          "--summary-md", os.path.join(d, "s.md")])
            idx = read(os.path.join(d, "r", "index.html"))
            self.assertIn("https://github.com/acme/firmware/actions/runs/99", idx)
            self.assertIn(">#42</a>", idx)
            self.assertIn("firmware", idx)
            md = read(step)
            self.assertEqual(md.strip(), read(os.path.join(d, "s.md")).strip())
            self.assertIn("<!-- verreport-summary -->", md)
            self.assertIn("[전체 리포트 보기](https://acme.github.io/r/)", md)
            self.assertIn("| Google Test | ❌ FAIL |", md)
            self.assertIn("실패한 테스트", md)


if __name__ == "__main__":
    unittest.main()
