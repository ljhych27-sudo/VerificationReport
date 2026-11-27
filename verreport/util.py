"""경로/수치 공용 유틸."""
import posixpath


def norm(path):
    return (path or "").replace("\\", "/")


def common_dir(paths):
    """모든 경로가 공유하는 디렉터리(posix 문자열)."""
    dirs = [posixpath.dirname(norm(p)).split("/") for p in paths if p]
    if not dirs:
        return ""
    prefix = dirs[0]
    for d in dirs[1:]:
        n = 0
        while n < min(len(prefix), len(d)) and prefix[n] == d[n]:
            n += 1
        prefix = prefix[:n]
    return "/".join(prefix)


def relativize(paths, prefix=None):
    """{원본경로: 상대경로}. prefix 미지정 시 공통 디렉터리를 제거한다."""
    paths = list(paths)
    base = norm(prefix).rstrip("/") if prefix else common_dir(paths)
    out = {}
    for p in paths:
        n = norm(p)
        if base and n.startswith(base + "/"):
            n = n[len(base) + 1:]
        out[p] = n
    return out


def module_of(rel):
    """상대경로의 최상위 디렉터리를 모듈로 본다."""
    parts = rel.split("/")
    return parts[0] if len(parts) > 1 else "(root)"


def pct(covered, count):
    return None if not count else 100.0 * covered / count


def fmt_pct(p):
    return "-" if p is None else f"{p:.1f}%"
