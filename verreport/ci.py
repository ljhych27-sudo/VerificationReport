"""CI 환경 자동 감지 (GitHub Actions / GitLab CI / Jenkins).

감지된 값은 명령행 옵션(--build-number 등)을 지정하지 않았을 때 기본값으로 사용된다.
"""
import json
import os


def _github(env):
    server = env.get("GITHUB_SERVER_URL", "https://github.com")
    repo = env.get("GITHUB_REPOSITORY", "")
    info = {
        "provider": "GitHub Actions",
        "project": repo.split("/")[-1],
        "build_number": env.get("GITHUB_RUN_NUMBER", ""),
        "branch": env.get("GITHUB_HEAD_REF") or env.get("GITHUB_REF_NAME", ""),
        "commit": env.get("GITHUB_SHA", ""),
        "run_url": f"{server}/{repo}/actions/runs/{env['GITHUB_RUN_ID']}" if env.get("GITHUB_RUN_ID") else "",
        "workflow": env.get("GITHUB_WORKFLOW", ""),
        "event": env.get("GITHUB_EVENT_NAME", ""),
        "pr_number": "", "pr_url": "",
        "commit_url": "",
    }
    attempt = env.get("GITHUB_RUN_ATTEMPT", "1")
    if info["build_number"] and attempt not in ("", "1"):
        info["build_number"] += f".{attempt}"
    # PR 이벤트에서 GITHUB_SHA 는 임시 머지 커밋이므로 이벤트 페이로드의 head SHA 를 사용
    path = env.get("GITHUB_EVENT_PATH")
    if path and os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                pr = json.load(f).get("pull_request") or {}
        except (OSError, ValueError):
            pr = {}
        if pr:
            info["pr_number"] = str(pr.get("number", ""))
            info["pr_url"] = pr.get("html_url", "")
            info["commit"] = (pr.get("head") or {}).get("sha") or info["commit"]
    if repo and info["commit"]:
        info["commit_url"] = f"{server}/{repo}/commit/{info['commit']}"
    return info


def _gitlab(env):
    return {
        "provider": "GitLab CI",
        "project": env.get("CI_PROJECT_NAME", ""),
        "build_number": env.get("CI_PIPELINE_IID", ""),
        "branch": env.get("CI_MERGE_REQUEST_SOURCE_BRANCH_NAME") or env.get("CI_COMMIT_REF_NAME", ""),
        "commit": env.get("CI_COMMIT_SHA", ""),
        "run_url": env.get("CI_PIPELINE_URL", ""),
        "workflow": "", "event": env.get("CI_PIPELINE_SOURCE", ""),
        "pr_number": env.get("CI_MERGE_REQUEST_IID", ""), "pr_url": "",
        "commit_url": (f"{env['CI_PROJECT_URL']}/-/commit/{env['CI_COMMIT_SHA']}"
                       if env.get("CI_PROJECT_URL") and env.get("CI_COMMIT_SHA") else ""),
    }


def _jenkins(env):
    branch = env.get("BRANCH_NAME") or env.get("GIT_BRANCH", "")
    return {
        "provider": "Jenkins",
        "project": env.get("JOB_BASE_NAME", ""),
        "build_number": env.get("BUILD_NUMBER", ""),
        "branch": branch.split("origin/", 1)[-1] if branch.startswith("origin/") else branch,
        "commit": env.get("GIT_COMMIT", ""),
        "run_url": env.get("BUILD_URL", ""),
        "workflow": "", "event": "",
        "pr_number": env.get("CHANGE_ID", ""), "pr_url": env.get("CHANGE_URL", ""),
        "commit_url": "",
    }


def detect(env=None):
    """CI 정보 dict 를 반환. CI 환경이 아니면 None."""
    env = os.environ if env is None else env
    if env.get("GITHUB_ACTIONS") == "true":
        return _github(env)
    if env.get("GITLAB_CI") == "true":
        return _gitlab(env)
    if env.get("JENKINS_URL") or env.get("JENKINS_HOME"):
        return _jenkins(env)
    return None
