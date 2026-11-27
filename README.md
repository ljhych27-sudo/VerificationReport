# VerificationReport (VERReport)

[![CI](https://github.com/ljhych27-sudo/VerificationReport/actions/workflows/ci.yml/badge.svg)](https://github.com/ljhych27-sudo/VerificationReport/actions/workflows/ci.yml)

테스트, 정적분석 등의 결과를 한 번에 보여준다.

Google Test / VVLM(LLVM) 커버리지 / CPPCheck / Lizard 결과를 읽어
**대시보드 + 도구별 상세 결과** HTML 리포트를 생성하는 파이썬 도구입니다.

- 외부 패키지 의존성 없음 (Python 3.10+ 표준 라이브러리만 사용)
- 생성된 리포트는 정적 HTML이라 CI 아티팩트로 그대로 열람 가능 (인터넷 불필요)

## 리포트 구성

| 페이지 | 내용 |
|---|---|
| `index.html` 대시보드 | 빌드 정보(빌드 일시/번호/브랜치/커밋), 총괄 판정, 도구별 카드(차트 + 핵심 수치 + **상세 결과 보기** 버튼), 도구별 요약 표, 모듈별 교차 요약 표 |
| `gtest.html` | 테스트 스위트 > 테스트 케이스 (결과, 위치, 시간, 실패 메시지) |
| `coverage.html` | 모듈 > 파일 > 함수 (Line / Function / Region / Branch, 함수별 실행 횟수·Region 커버리지) |
| `cppcheck.html` | 심각도별 집계, 규칙 ID별 통계, 모듈 > 파일 > 위반(라인, **함수**, 규칙, 메시지, CWE) |
| `lizard.html` | 모듈 > 파일 > 함수 (CCN > 10, 함수 라인 수 > 80 초과 항목) |

상세 페이지는 검색(모듈/파일/함수/메시지), 모두 펼치기/접기를 지원합니다.
파일 행을 클릭하면 함수 단위 상세가 펼쳐집니다.

> 모듈은 소스 루트 기준 **최상위 디렉터리**입니다 (예: `src/core/task.c` → `core`).
> CPPCheck 위반의 함수명은 Lizard 결과의 함수 라인 범위로 매핑합니다 (`--lizard` 함께 지정 시).

## 빠른 시작

```bash
python -m verreport --demo -o report      # samples/ 예제 데이터로 생성
start report\index.html                     # Windows
```

## 입력 파일 만들기

```bash
# Google Test (실행파일별로 여러 개 가능, xml/json 모두 지원)
./unit_tests --gtest_output=xml:gtest_result.xml

# LLVM 커버리지 (함수 단위 결과를 위해 -summary-only 를 쓰지 않음)
llvm-profdata merge -sparse default.profraw -o cov.profdata
llvm-cov export -format=text ./unit_tests -instr-profile=cov.profdata -Xdemangler=c++filt > coverage.json

# CPPCheck
cppcheck --enable=all --xml --xml-version=2 src 2> cppcheck.xml

# Lizard (전체 함수를 CSV로 출력, 기준 초과 판정은 VERReport가 수행)
lizard --csv src > lizard.csv
```

## 실행

```bash
python -m verreport \
  --gtest gtest_a.xml gtest_b.xml \
  --coverage coverage.json \
  --cppcheck cppcheck.xml \
  --lizard lizard.csv \
  --project MyProject --build-number 123 --branch main --commit abc1234 \
  --build-time "2026-11-27 09:00:00" \
  -o report
```

| 옵션 | 설명 | 기본값 |
|---|---|---|
| `--gtest FILE...` | Google Test 결과 (XML/JSON, 여러 개 병합) | - |
| `--coverage FILE` | `llvm-cov export` JSON | - |
| `--cppcheck FILE` | CPPCheck XML v2 | - |
| `--lizard FILE` | Lizard CSV | - |
| `-o, --out DIR` | 출력 디렉터리 | `report` |
| `--project / --build-number / --branch / --commit` | 헤더에 표시할 빌드 정보 | - |
| `--build-time` | 빌드 일시 | 현재 시각 |
| `--strip-prefix PATH` | 경로에서 제거할 소스 루트 | 공통 상위 디렉터리 자동 |
| `--max-ccn N` | 순환복잡도 기준 (초과 시 위반) | 10 |
| `--max-length N` | 함수 라인 수 기준 (초과 시 위반) | 80 |
| `--cov-threshold P` | Line 커버리지 합격 기준(%) | 미지정 → INFO |
| `--fail-on-error` | 총괄 결과 FAIL이면 종료 코드 1 | off |
| `--summary-md FILE` | 마크다운 요약 파일 출력 | - |
| `--report-url URL` | 요약에 넣을 "전체 리포트 보기" 링크 | - |
| `--no-ci-detect` | CI 환경변수 자동 감지 끄기 | off |
| `--no-step-summary` | `$GITHUB_STEP_SUMMARY` 기록 끄기 | off |

입력은 일부만 지정해도 되며, 지정하지 않은 도구는 "결과 없음"으로 표시됩니다.
`pip install .` 후에는 `verreport ...` 명령으로도 실행할 수 있습니다.

## 판정 기준

| 도구 | PASS | WARN | FAIL |
|---|---|---|---|
| Google Test | 실패 0건 | 테스트 0건 | 실패 1건 이상 |
| 커버리지 | Line ≥ 기준 | - | Line < 기준 (기준 미지정 시 INFO) |
| CPPCheck | 위반 0건 | error 외 위반 존재 | error 1건 이상 |
| Lizard | 위반 0건 | 위반 1건 이상 | - |

총괄 결과는 FAIL > WARN > PASS 순으로 가장 나쁜 결과를 따릅니다.

## CI 연동

| 기능 | 동작 |
|---|---|
| CI 정보 자동 표시 | GitHub Actions / GitLab CI / Jenkins 환경변수에서 빌드 번호·브랜치·커밋·PR·실행 링크를 읽어 리포트 헤더에 표시합니다. 명령행 옵션을 주면 옵션이 우선합니다. (`--no-ci-detect`로 끄기) |
| Actions 실행 요약 | GitHub Actions에서 실행하면 판정과 주요 수치, 실패 테스트, CPPCheck error, Lizard 상위 위반을 `$GITHUB_STEP_SUMMARY`에 자동 기록합니다. (`--no-step-summary`로 끄기) |
| 요약 마크다운 | `--summary-md FILE`로 같은 요약을 파일로 저장합니다. PR 코멘트 등에 사용하고, `--report-url`로 넘긴 주소가 "전체 리포트 보기" 링크가 됩니다. |

이 저장소의 [`.github/workflows/ci.yml`](.github/workflows/ci.yml)은 예제 데이터(`--demo`)로 위 기능을 모두 사용합니다.

- **PR:** 요약을 PR 코멘트로 작성합니다. 새 커밋이 오면 같은 코멘트를 갱신합니다. 전체 리포트는 실행 화면의 `verreport` 아티팩트로 받을 수 있습니다.
- **main:** 리포트를 GitHub Pages에 배포합니다 → https://ljhych27-sudo.github.io/VerificationReport/

### 실제 C/C++ 프로젝트에 적용하기

```yaml
      - name: Verification report
        run: |
          pip install git+https://github.com/ljhych27-sudo/VerificationReport.git
          verreport --gtest build/test-results/*.xml \
                    --coverage build/coverage.json \
                    --cppcheck build/cppcheck.xml \
                    --lizard build/lizard.csv \
                    --strip-prefix "$GITHUB_WORKSPACE/src" \
                    --summary-md summary.md -o report --fail-on-error
```

`--fail-on-error`를 주면 총괄 결과가 FAIL일 때 job이 실패합니다. 이 경우 뒤의
업로드/코멘트 단계에는 `if: always()`를 붙여야 실패한 빌드에서도 리포트가 남습니다.

## 개발

```bash
python samples/make_samples.py         # 예제 입력 재생성
python -m unittest discover -s tests   # 테스트
```

```
verreport/
  cli.py            명령행 진입점
  render.py         HTML/차트(SVG·CSS) 렌더링
  summary.py        마크다운 요약 (Job Summary / PR 코멘트)
  ci.py             CI 환경 자동 감지
  util.py           경로 정규화, 모듈 판정
  parsers/          gtest.py, llvmcov.py, cppcheck.py, lizard.py
samples/            예제 입력 + 생성 스크립트
tests/              단위/통합 테스트
```
