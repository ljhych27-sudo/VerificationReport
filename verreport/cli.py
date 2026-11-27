"""명령행 인터페이스.

예)
  python -m verreport --gtest out/test_a.xml out/test_b.xml --coverage coverage.json \
      --cppcheck cppcheck.xml --lizard lizard.csv --project MyECU --build-number 123 -o report
"""
import argparse
import datetime as dt
import os
import sys

from . import __version__
from .parsers import gtest, llvmcov, cppcheck, lizard
from .render import write_report

def _samples_dir():
    """소스 체크아웃의 samples/ (설치된 패키지로 실행 시 현재 디렉터리의 samples/)."""
    src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")
    return src if os.path.isdir(src) else os.path.abspath("samples")


def build_parser():
    p = argparse.ArgumentParser(prog="verreport", description="Verification 결과 HTML 대시보드 생성기")
    p.add_argument("--gtest", nargs="+", metavar="FILE", help="Google Test 결과 XML/JSON (여러 개 가능)")
    p.add_argument("--coverage", metavar="FILE", help="llvm-cov export JSON")
    p.add_argument("--cppcheck", metavar="FILE", help="CPPCheck XML (--xml-version=2)")
    p.add_argument("--lizard", metavar="FILE", help="Lizard CSV (lizard --csv)")
    p.add_argument("-o", "--out", default="report", help="출력 디렉터리 (기본: report)")
    p.add_argument("--project", default="", help="프로젝트 이름")
    p.add_argument("--build-number", default="", help="빌드 번호")
    p.add_argument("--build-time", default="", help="빌드 일시 (미지정 시 현재 시각)")
    p.add_argument("--branch", default="", help="브랜치")
    p.add_argument("--commit", default="", help="커밋 해시")
    p.add_argument("--strip-prefix", default=None,
                   help="파일 경로에서 제거할 소스 루트 (미지정 시 공통 상위 디렉터리 자동 제거)")
    p.add_argument("--max-ccn", type=int, default=10, help="순환복잡도 기준, 초과 시 위반 (기본 10)")
    p.add_argument("--max-length", type=int, default=80, help="함수 라인 수 기준, 초과 시 위반 (기본 80)")
    p.add_argument("--cov-threshold", type=float, default=None,
                   help="Line 커버리지 합격 기준(%%). 미지정 시 판정 없이 INFO 표시")
    p.add_argument("--fail-on-error", action="store_true",
                   help="총괄 결과가 FAIL 이면 종료 코드 1 반환 (CI 용)")
    p.add_argument("--demo", action="store_true", help="samples/ 의 예제 데이터로 리포트 생성")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _safe_console():
    """cp1252 등 한글을 표현 못 하는 콘솔/파이프(CI 등)에서 UnicodeEncodeError 로 죽지 않도록 한다."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except (ValueError, OSError):
                pass


def main(argv=None):
    _safe_console()
    a = build_parser().parse_args(argv)
    if a.demo:
        SAMPLES = _samples_dir()
        if not os.path.isdir(SAMPLES):
            build_parser().error(f"--demo: 예제 디렉터리를 찾을 수 없습니다: {SAMPLES}")
        a.gtest = a.gtest or [os.path.join(SAMPLES, "gtest_core.xml"), os.path.join(SAMPLES, "gtest_comm.json")]
        a.coverage = a.coverage or os.path.join(SAMPLES, "coverage.json")
        a.cppcheck = a.cppcheck or os.path.join(SAMPLES, "cppcheck.xml")
        a.lizard = a.lizard or os.path.join(SAMPLES, "lizard.csv")
        a.project = a.project or "DemoProject"
        a.build_number = a.build_number or "1024"
    if not any([a.gtest, a.coverage, a.cppcheck, a.lizard]):
        build_parser().error("입력 파일을 하나 이상 지정하세요 (--gtest/--coverage/--cppcheck/--lizard) 또는 --demo")

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ctx = {"meta": {"project": a.project, "build_number": a.build_number,
                    "build_time": a.build_time or now, "branch": a.branch, "commit": a.commit,
                    "generated": now, "cov_threshold": a.cov_threshold}}

    rows = lizard.read_rows(a.lizard) if a.lizard else None
    if a.gtest:
        ctx["gtest"] = gtest.parse(a.gtest)
    if a.coverage:
        ctx["coverage"] = llvmcov.parse(a.coverage, a.strip_prefix)
    if a.lizard:
        ctx["lizard"] = lizard.parse(a.lizard, a.strip_prefix, a.max_ccn, a.max_length, rows=rows)
    if a.cppcheck:
        locator = lizard.make_locator(rows) if rows else None
        ctx["cppcheck"] = cppcheck.parse(a.cppcheck, a.strip_prefix, locator)

    index = write_report(ctx, a.out)
    print(f"[VERReport] 총괄 결과: {ctx['status']['overall']}  ->  {os.path.abspath(index)}")
    if a.fail_on_error and ctx["status"]["overall"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
