"""A CSV import's body: a form of two parts, the mapping and then the file.

No I/O until an attempt opens a path: `Allisall` and `AsyncAllisall` share it.
"""

# No `from __future__ import annotations` here: on Python 3.11 it hides `Required` and
# `NotRequired` from `TypedDict`, as in `_types.py`.
import os
from collections.abc import Iterator, Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from typing import IO, NotRequired, Required, TypedDict

from ._encode import encode_body
from ._generated.requests import ImportMapping

DEFAULT_FILENAME = "upload.csv"

FilePart = tuple[str, bytes | IO[bytes], str]
"""One part as httpx takes it: its file name, its content and its type."""


class ImportUpload(TypedDict):
    """A CSV upload: the mapping of its columns, and the file itself.

    `file` is one of three things:

    - `bytes`: the CSV content itself.
    - a `str`: the CSV content itself, sent as UTF-8. A `str` is never opened as a path, so
      `file="events.csv"` uploads the ten characters `events.csv`, not that file.
    - a `pathlib.Path`, or another `os.PathLike`: a file on disk, opened afresh for each
      attempt and streamed without being read into memory first. Pass a path this way, such
      as `file=Path("events.csv")`.

    An open file object is not accepted, because a retry must send the same bytes again.

    `filename` is the file name the import records. It defaults to a path's base name, and
    otherwise to `upload.csv`; an empty `filename` counts as none.
    """

    mapping: Required[ImportMapping]
    file: Required[bytes | str | os.PathLike[str]]
    filename: NotRequired[str]


@dataclass(frozen=True)
class Upload:
    """A form fixed before the first attempt: the mapping's JSON, and the file's content or
    path, with its name."""

    mapping: bytes
    source: bytes | os.PathLike[str]
    """The file's bytes, or the path to open for each attempt."""
    filename: str

    @contextmanager
    def parts(self) -> Iterator[list[tuple[str, FilePart]]]:
        """The two parts of one attempt, `mapping` before `file`. A path is opened here, and
        closed when the attempt ends. An `OSError` from opening it propagates unchanged."""
        with ExitStack() as stack:
            content: bytes | IO[bytes]
            if isinstance(self.source, bytes):
                content = self.source
            else:
                content = stack.enter_context(open(self.source, "rb"))
            yield [
                ("mapping", ("mapping.json", self.mapping, "application/json")),
                ("file", (self.filename, content, "text/csv")),
            ]


def upload_of(upload: object) -> Upload:
    """Fix an upload's parts before the first attempt.

    Raises `ValueError` when the upload is not a mapping holding `mapping` and `file`, when the
    mapping cannot be encoded, when `file` is not `bytes`, a `str` or a path, or when
    `filename` is not a `str`.
    """
    if not isinstance(upload, Mapping):
        raise ValueError(
            f"an import takes a mapping with mapping and file, not a {type(upload).__name__}"
        )
    for member in ("mapping", "file"):
        if member not in upload:
            raise ValueError(f"an import's upload has no {member}")
    try:
        mapping = encode_body(upload["mapping"])
    except ValueError as err:
        raise ValueError(f"an import's mapping cannot be sent: {err}") from err
    file = upload["file"]
    filename = upload.get("filename")
    if filename is not None and not isinstance(filename, str):
        raise ValueError(f"an import's filename is a {type(filename).__name__}; pass a str")
    source: bytes | os.PathLike[str]
    default = DEFAULT_FILENAME
    if isinstance(file, bytes):
        source = file
    elif isinstance(file, str):
        try:
            source = file.encode("utf-8")
        except UnicodeEncodeError as err:
            raise ValueError(
                f"an import's file holds text that is not valid Unicode: {err}"
            ) from err
    elif isinstance(file, os.PathLike):
        name = os.fspath(file)
        if not isinstance(name, str):
            raise ValueError("an import's file is a bytes path; pass a str path")
        source = file
        default = os.path.basename(name) or DEFAULT_FILENAME
    else:
        raise ValueError(
            f"an import's file is a {type(file).__name__}; pass bytes, a str or a path. "
            "An open file cannot be read again for a retry: pass its path instead"
        )
    return Upload(mapping=mapping, source=source, filename=filename or default)
