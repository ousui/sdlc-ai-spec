"""Durable, content-minimizing, append-observed operation journal.

Exclusive directory creation is the send claim. A process never steals a claim,
including an empty directory left by a crash. Observation files are immutable.
"""
from __future__ import annotations
from contextlib import contextmanager
import errno
import json
import os
import re
from pathlib import Path
from uuid import UUID, uuid4

from packages.sdlc_runtime.local_paths import absolute_root, directory, private_stat, LocalPathError
from .models import GithubError, canonical, digest, ensure_no_secret, now

MAX_RECORD = 256 * 1024


class Records:
    def __init__(self, data_root: str | Path):
        try:
            self.root = absolute_root(data_root)
        except (OSError, ValueError):
            raise GithubError("STORAGE_UNSAFE") from None

    def _key(self, actor: int, repository: str, request_id: str) -> tuple[str, ...]:
        if isinstance(actor, bool) or not isinstance(actor, int) or actor < 1:
            raise GithubError("ARGUMENT_INVALID")
        try:
            if str(UUID(request_id, version=4)) != request_id:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise GithubError("ARGUMENT_INVALID") from None
        return (".local", "github", str(actor), digest(repository), "operations", request_id)

    @contextmanager
    def _directory(self, actor, repo, rid, *, create=False, parent=False):
        key = self._key(actor, repo, rid)
        try:
            with directory(self.root, key[:-1] if parent else key, create=create) as fd:
                yield fd
        except GithubError:
            raise
        except FileNotFoundError:
            raise GithubError("RECEIPT_NOT_FOUND") from None
        except (LocalPathError, NotADirectoryError):
            raise GithubError("STORAGE_UNSAFE") from None
        except OSError as e:
            raise GithubError("STORAGE_UNSAFE" if e.errno == errno.ELOOP else "STORAGE_FAILED") from None

    @staticmethod
    def _load(fd: int, name: str):
        try:
            handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        except FileNotFoundError:
            return None
        try:
            private_stat(os.fstat(handle), directory=False)
            if os.fstat(handle).st_size > MAX_RECORD:
                raise GithubError("RECORD_CORRUPT")
            content = b""
            while len(content) <= MAX_RECORD:
                block = os.read(handle, min(65536, MAX_RECORD + 1 - len(content)))
                if not block:
                    break
                content += block
            value = json.loads(content)
            if not isinstance(value, dict) or not isinstance(value.get("payload"), dict) or set(value) != {"payload", "sha256"} or digest(value["payload"]) != value["sha256"]:
                raise GithubError("RECORD_CORRUPT")
            return value["payload"]
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            raise GithubError("RECORD_CORRUPT") from None
        finally:
            os.close(handle)

    @staticmethod
    def _save(fd: int, name: str, value: dict) -> None:
        ensure_no_secret(value)
        encoded = canonical({"payload": value, "sha256": digest(value)})
        if len(encoded) > MAX_RECORD:
            raise GithubError("STORAGE_FAILED")
        temp = ".tmp-" + str(uuid4())
        handle = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            view = memoryview(encoded)
            while view:
                count = os.write(handle, view)
                if count <= 0:
                    raise GithubError("STORAGE_FAILED")
                view = view[count:]
            os.fsync(handle)
        finally:
            os.close(handle)
        try:
            # Atomic no-overwrite publication. No partial JSON is ever visible.
            os.link(temp, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
        finally:
            os.unlink(temp, dir_fd=fd)
        os.fsync(fd)

    def claim(self, intent: dict) -> bool:
        actor, repo, rid = intent["actor"]["id"], intent["repository"], intent["request_id"]
        with self._directory(actor, repo, rid, create=True, parent=True) as parent:
            try:
                os.mkdir(rid, mode=0o700, dir_fd=parent)
                os.fsync(parent)
            except FileExistsError:
                return False
            handle = os.open(rid, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            try:
                private_stat(os.fstat(handle), directory=True)
                self._save(handle, "intent.json", intent)
            finally:
                os.close(handle)
        return True

    def load(self, actor: int, repo: str, rid: str) -> tuple[dict | None, dict | None]:
        with self._directory(actor, repo, rid) as fd:
            intent = self._load(fd, "intent.json")
            if intent is None:
                return None, None
            required = {"version", "actor", "repository", "request_id", "operation", "params_digest", "expected_hashes", "target", "created_at", "before_hashes"}
            from .operations import WRITES
            if (set(intent) != required or type(intent["version"]) is not int or intent["version"] != 1
                    or not isinstance(intent["actor"], dict) or intent["actor"].get("id") != actor
                    or intent["repository"] != repo or intent["request_id"] != rid
                    or not isinstance(intent["operation"], str) or intent["operation"] not in WRITES
                    or (intent["target"] is not None and not isinstance(intent["target"], dict))
                    or not isinstance(intent["created_at"], str)
                    or not isinstance(intent["params_digest"], str) or not re.fullmatch(r"[0-9a-f]{64}", intent["params_digest"])):
                raise GithubError("RECORD_CORRUPT")
            for field in ("expected_hashes", "before_hashes"):
                hashes = intent[field]
                if not isinstance(hashes, dict) or any(k not in {"title", "body", "state", "head", "base", "draft"}
                        or not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v) for k, v in hashes.items()):
                    raise GithubError("RECORD_CORRUPT")
            receipt = self._load(fd, "receipt.json")
            observations = sorted(x for x in os.listdir(fd) if x.startswith("observation-") and x.endswith(".json"))
            if len(observations) > 1000:
                raise GithubError("RECORD_CORRUPT")
            for name in observations:
                observation = self._load(fd, name)
                if not isinstance(observation, dict) or "result" not in observation:
                    raise GithubError("RECORD_CORRUPT")
                receipt = observation
            if receipt is not None:
                if receipt.get("request_id") != rid or not isinstance(receipt.get("result"), dict):
                    raise GithubError("RECORD_CORRUPT")
                result = receipt["result"]
                from jsonschema import Draft202012Validator
                schema = json.loads((Path(__file__).resolve().parents[2] / "skills/_shared/schemas/github-result.schema.json").read_bytes())
                if (not Draft202012Validator(schema).is_valid(result) or not isinstance(result.get("actor"), dict)
                        or result["actor"].get("id") != actor or result.get("repository") != repo or result.get("operation") != intent["operation"]):
                    raise GithubError("RECORD_CORRUPT")
            return intent, receipt

    def save_receipt(self, intent: dict, result: dict, *, observation=False) -> None:
        with self._directory(intent["actor"]["id"], intent["repository"], intent["request_id"]) as fd:
            value = {"request_id": intent["request_id"], "observed_at": now(), "result": result}
            name = "observation-" + value["observed_at"].replace(":", "-") + "-" + str(uuid4()) + ".json" if observation else "receipt.json"
            self._save(fd, name, value)
