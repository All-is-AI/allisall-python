"""A CSV import's multipart body: the parts, their order and names, and its retries."""

from __future__ import annotations

import io
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

import allisall
from allisall import ImportPreview, ImportResult
from allisall._generated import requests as generated_requests
from allisall._options import CallOptions
from samples import sample

from support import Harness, json_response

MAPPING = {"columns": {"timestamp": "Time", "agent_key": "Agent"}, "timezone": "Asia/Tokyo"}


def parts(request: httpx.Request) -> list[tuple[str, str, str, bytes]]:
    """Each part's name, file name, type and content, in order."""
    content_type = request.headers["content-type"]
    boundary = content_type.split("boundary=", 1)[1].encode()
    found = []
    for chunk in request.content.split(b"--" + boundary)[1:-1]:
        # Each part sits between the CRLF after its boundary and the CRLF before the next.
        assert chunk.startswith(b"\r\n")
        assert chunk.endswith(b"\r\n")
        head, _, body = chunk[2:-2].partition(b"\r\n\r\n")
        disposition = re.search(rb'name="([^"]*)"; filename="([^"]*)"', head)
        kind = re.search(rb"Content-Type: (\S+)", head)
        assert disposition is not None
        assert kind is not None
        found.append(
            (
                disposition.group(1).decode(),
                disposition.group(2).decode(),
                kind.group(1).decode(),
                body,
            )
        )
    return found


def commit(harness: Harness, upload: Any, **options: Any) -> ImportResult:
    return harness.call("commitImport", ImportResult, body=upload, options=CallOptions(**options))


def ok(request: httpx.Request) -> httpx.Response:
    return json_response(sample(ImportResult))


def test_the_form_holds_the_mapping_then_the_file(make: Callable[..., Harness]) -> None:
    harness = make(ok)
    commit(harness, {"mapping": MAPPING, "file": b"Time,Agent\n"})
    (request,) = harness.requests
    assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
    (mapping, file) = parts(request)
    assert mapping[:3] == ("mapping", "mapping.json", "application/json")
    assert json.loads(mapping[3]) == MAPPING
    assert file == ("file", "upload.csv", "text/csv", b"Time,Agent\n")


def test_preview_sends_the_same_form_with_a_str_file_as_its_content(
    make: Callable[..., Harness],
) -> None:
    harness = make(lambda r: json_response(sample(ImportPreview)))
    harness.call("previewImport", ImportPreview, body={"mapping": MAPPING, "file": "a,é\n"})
    (request,) = harness.requests
    assert [part[0] for part in parts(request)] == ["mapping", "file"]
    assert parts(request)[1][3] == "a,é\n".encode()
    assert "idempotency-key" not in request.headers


@pytest.mark.parametrize(
    ("upload", "name"),
    [
        ({"file": b"x"}, "upload.csv"),
        ({"file": "x"}, "upload.csv"),
        ({"file": b"x", "filename": ""}, "upload.csv"),
        ({"file": b"x", "filename": "march.csv"}, "march.csv"),
        ({"path": "events.csv"}, "events.csv"),
        ({"path": "events.csv", "filename": "named.csv"}, "named.csv"),
        ({"path": "events.csv", "filename": ""}, "events.csv"),
    ],
    ids=[
        "bytes-content",
        "str-content",
        "bytes-content-empty-filename",
        "bytes-content-filename",
        "path",
        "path-filename",
        "path-empty-filename",
    ],
)
def test_the_file_part_s_name(
    make: Callable[..., Harness], tmp_path: Path, upload: dict[str, Any], name: str
) -> None:
    if "path" in upload:
        path = tmp_path / upload.pop("path")
        path.write_bytes(b"x")
        upload["file"] = path
    harness = make(ok)
    commit(harness, {"mapping": MAPPING, **upload})
    assert parts(harness.requests[0])[1][:2] == ("file", name)


@pytest.mark.parametrize(
    "file",
    [io.BytesIO(b"x"), io.StringIO("x"), bytearray(b"x"), memoryview(b"x"), 7],
    ids=["binary-file", "text-file", "bytearray", "memoryview", "int"],
)
def test_a_file_that_cannot_be_read_again_is_refused(
    make: Callable[..., Harness], file: object
) -> None:
    harness = make(ok)
    with pytest.raises(ValueError, match="pass bytes, a str or a path"):
        commit(harness, {"mapping": MAPPING, "file": file})
    assert harness.requests == []


class BytesPath:
    """An `os.PathLike` whose path is `bytes`."""

    def __fspath__(self) -> bytes:
        return b"events.csv"


def test_a_str_file_holding_a_lone_surrogate_is_refused(make: Callable[..., Harness]) -> None:
    harness = make(ok)
    with pytest.raises(ValueError, match="not valid Unicode"):
        commit(harness, {"mapping": MAPPING, "file": "Time\n\ud800\n"})
    assert harness.requests == []


@pytest.mark.parametrize(
    "upload",
    [
        b"x",
        {"file": b"x"},
        {"mapping": MAPPING},
        {"mapping": [], "file": b"x"},
        {"mapping": MAPPING, "file": b"x", "filename": 3},
        {"mapping": MAPPING, "file": BytesPath()},
    ],
    ids=["not-a-mapping", "no-mapping", "no-file", "mapping-a-list", "filename-int", "bytes-path"],
)
def test_an_upload_of_the_wrong_shape_is_refused(
    make: Callable[..., Harness], upload: object
) -> None:
    harness = make(ok)
    with pytest.raises(ValueError, match="import"):
        commit(harness, upload)
    assert harness.requests == []


def test_a_missing_path_propagates_its_os_error_and_is_not_retried(
    make: Callable[..., Harness], tmp_path: Path
) -> None:
    harness = make(ok)
    with pytest.raises(FileNotFoundError):
        commit(harness, {"mapping": MAPPING, "file": tmp_path / "absent.csv"})
    assert harness.requests == []


def test_a_path_is_opened_afresh_for_each_attempt(
    make: Callable[..., Harness], tmp_path: Path
) -> None:
    path = tmp_path / "events.csv"
    path.write_bytes(b"first\n")

    def handler(request: httpx.Request) -> httpx.Response:
        if len(harness.requests) == 1:
            # The file changes while the first attempt fails: a second attempt that reads it
            # again sends the new content.
            path.write_bytes(b"second\n")
            return httpx.Response(503)
        return ok(request)

    harness = make(handler)
    commit(harness, {"mapping": MAPPING, "file": path})
    first, second = harness.requests
    assert parts(first)[1][3] == b"first\n"
    assert parts(second)[1][3] == b"second\n"


def test_a_retried_commit_sends_the_same_key_and_parts(make: Callable[..., Harness]) -> None:
    answers = iter([httpx.Response(500)])
    harness = make(lambda r: next(answers, None) or ok(r))
    commit(harness, {"mapping": MAPPING, "file": b"Time\n1\n", "filename": "a.csv"})
    first, second = harness.requests
    assert first.headers["idempotency-key"] == second.headers["idempotency-key"]
    assert parts(first) == parts(second)
    assert [part[0] for part in parts(second)] == ["mapping", "file"]


def test_the_exported_upload_is_the_sdk_s_own() -> None:
    assert allisall.ImportUpload is not generated_requests.ImportUpload
    assert allisall.ImportUpload.__required_keys__ == {"mapping", "file"}
    assert allisall.ImportUpload.__optional_keys__ == {"filename"}
