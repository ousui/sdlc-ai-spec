"""URL parsing only. This module never fetches URLs or guesses a remote."""
from __future__ import annotations
import re
from urllib.parse import urlsplit, unquote
from .models import GithubError
from .operations import REPOSITORY


def parse_url(url: str, *, ref: str | None = None, path: str | None = None) -> dict:
    try:
        u = urlsplit(url)
        valid = u.scheme == "https" and u.netloc == "github.com" and not u.username and not u.password and not u.port
    except ValueError:
        raise GithubError("TARGET_MISMATCH") from None
    if not valid or u.query or u.fragment or "\\" in url or re.search(r"%(?:2f|5c|2e|25|00)", url, re.I):
        raise GithubError("TARGET_MISMATCH")
    parts = unquote(u.path).strip("/").split("/")
    if len(parts) < 2 or any(not x or x in {".", ".."} or any(ord(c) < 32 for c in x) for x in parts):
        raise GithubError("TARGET_MISMATCH")
    repository = "/".join(parts[:2])
    if not re.fullmatch(REPOSITORY["pattern"], repository):
        raise GithubError("TARGET_MISMATCH")
    result = {"repository": repository.lower()}
    rest = parts[2:]
    if not rest:
        return result
    if len(rest) == 2 and rest[0] in {"issues", "pull"} and rest[1].isdigit() and int(rest[1]) > 0:
        return {**result, "subject_type": "issue" if rest[0] == "issues" else "pr", "number": int(rest[1])}
    if len(rest) == 3 and rest[:2] == ["actions", "runs"] and rest[2].isdigit() and int(rest[2]) > 0:
        return {**result, "run_id": int(rest[2])}
    if len(rest) >= 3 and rest[:2] == ["releases", "tag"]:
        return {**result, "tag": "/".join(rest[2:])}
    if len(rest) >= 3 and rest[0] == "blob":
        tail = "/".join(rest[1:])
        if re.fullmatch(r"[0-9a-fA-F]{40}", rest[1]):
            return {**result, "sha": rest[1].lower(), "path": "/".join(rest[2:])}
        if not ref or not path:
            raise GithubError("REF_AMBIGUOUS")
        if tail != ref + "/" + path:
            raise GithubError("TARGET_MISMATCH")
        return {**result, "ref": ref, "path": path}
    raise GithubError("TARGET_MISMATCH")


def merge_target(explicit: dict, derived: dict) -> dict:
    result = dict(explicit)
    for k, v in derived.items():
        existing = result.get(k)
        if k == "repository" and isinstance(existing, str):
            existing = existing.lower()
        if existing is not None and existing != v:
            raise GithubError("TARGET_MISMATCH")
        result[k] = v
    return result


def repository_from_remotes(remotes: list[str]) -> str:
    """Only consume the host's explicit list; never inspect filesystem Git config."""
    candidates = set()
    for remote in remotes:
        if remote.startswith("git@github.com:"):
            remote = "https://github.com/" + remote[len("git@github.com:"):]
        if remote.endswith(".git"):
            remote = remote[:-4]
        try:
            target = parse_url(remote)
            if set(target) != {"repository"}:
                raise GithubError("TARGET_REQUIRED")
            candidates.add(target["repository"])
        except GithubError:
            raise GithubError("TARGET_REQUIRED") from None
    if len(candidates) != 1:
        raise GithubError("TARGET_REQUIRED")
    return candidates.pop()
