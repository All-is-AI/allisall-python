"""Generates the SDK's wire types from the API's OpenAPI document.

It runs datamodel-code-generator twice, once per direction:

- `src/allisall/_generated/requests.py`: every request body, as a `TypedDict` whose enums are
  `Literal`s. Every request `Money` member is widened to `MoneyInput`, an instant to
  `InstantInput` and a date to `DateInput`.
- `src/allisall/_generated/responses.py`: every `2xx` response, as a frozen, keyword-only
  dataclass whose enums are `StrEnum`s. `Money` is `Decimal`.

Each run reads a copy of the document that holds only the schemas its direction reaches from the
operations the SDK calls. The script then formats both files with the package's own ruff.

Usage, from the package directory:

    uv run python scripts/generate.py           writes both files
    uv run python scripts/generate.py --check   exits 1 when either file is stale

Both files are committed and reviewed as a diff at every regeneration. Never edit them by hand:
change the document or this script, and regenerate. The document exists only in the monorepo, so
this script runs there.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import yaml

PACKAGE = Path(__file__).resolve().parents[1]
SPEC = PACKAGE.parent / "openapi" / "openapi.yaml"
OUTPUT_DIR = PACKAGE / "src" / "allisall" / "_generated"

HEADER = """\
# Generated from the API's OpenAPI document by scripts/generate.py, with
# datamodel-code-generator. Never edit this file by hand: change the document or
# the script, and regenerate."""

SCHEMA_REF = "#/components/schemas/"
METHODS = ("get", "put", "post", "delete", "patch")

# The access policies of the operations the SDK does not call: a signed-in session's
# trust acts, and the share-token read.
EXCLUDED_POLICIES = frozenset({"SessionOnly", "ShareToken"})

COMMON_FLAGS = (
    "--input-file-type",
    "openapi",
    "--target-python-version",
    "3.11",
    "--use-union-operator",
    "--disable-timestamp",
    "--formatters",
    "builtin",
)

REQUEST_FLAGS = (
    "--output-model-type",
    "typing.TypedDict",
    "--naming-strategy",
    "parent-prefixed",
    "--no-use-closed-typed-dict",
    "--use-standard-collections",
    "--use-schema-description",
    "--use-field-description",
)

RESPONSE_FLAGS = (
    "--output-model-type",
    "dataclasses.dataclass",
    "--frozen-dataclasses",
    "--keyword-only",
    "--capitalise-enum-members",
    "--use-generic-container-types",
    "--use-standard-collections",
    "--naming-strategy",
    "parent-prefixed",
    "--use-schema-description",
    "--use-field-description",
)

TYPES = "allisall._types"

# Every request `Money` member carries keywords beside its `$ref`, such as `minimum`, so the
# schema-level override misses it and the generator would write `float`. Each is named here.
REQUEST_MONEY_MEMBERS = (
    "EventInput.cost",
    "ValueLineItemInput.unit_value",
    "CostLineItemCreate.monthly_amount",
    "CostLineItemPatch.monthly_amount",
    "ModelRateInput.input_per_1k",
    "ModelRateInput.output_per_1k",
)

REQUEST_OVERRIDES: dict[str, str] = {
    "Money": "decimal.Decimal",
    **{member: f"{TYPES}.MoneyInput" for member in REQUEST_MONEY_MEMBERS},
    "InstantInput": f"{TYPES}.InstantInput",
    "DateInput": f"{TYPES}.DateInput",
}

RESPONSE_OVERRIDES: dict[str, str] = {
    "Money": "decimal.Decimal",
    "ErrorCode": f"{TYPES}.ErrorCode",
    "FieldErrorCode": f"{TYPES}.FieldErrorCode",
    "EventCategory": f"{TYPES}.EventCategory",
}

# Names the generator invents for an inline object that would otherwise end in a digit.
RESPONSE_NAME_MAP: dict[str, str] = {"Client1": "AgentDetailClient"}


def operations(spec: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Every operation the SDK calls: one with a `2xx` answer, not a `HEAD`, whose access
    policy is neither a session's trust act nor the share-token read."""
    for item in spec["paths"].values():
        for method in METHODS:
            operation = item.get(method)
            if operation is None:
                continue
            if operation["x-access"]["policy"] in EXCLUDED_POLICIES:
                continue
            if not any(str(status).startswith("2") for status in operation["responses"]):
                continue
            yield {
                **operation,
                "parameters": [*item.get("parameters", []), *operation.get("parameters", [])],
            }


def resolve(spec: dict[str, Any], node: object) -> Any:  # noqa: ANN401 - free-form JSON
    """Follows local `$ref`s until a node that is not one."""
    while isinstance(node, dict) and isinstance(node.get("$ref"), str):
        ref: str = node["$ref"]
        if not ref.startswith("#/"):
            raise ValueError(f"{ref} is not a local reference")
        target: Any = spec
        for key in ref[2:].split("/"):
            target = target[key.replace("~1", "/").replace("~0", "~")]
        node = target
    return node


def reached(spec: dict[str, Any], roots: Iterable[object]) -> set[str]:
    """The names of every component schema the roots reach, through any `$ref`."""
    schemas: dict[str, Any] = spec["components"]["schemas"]
    found: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(SCHEMA_REF):
            name = ref.removeprefix(SCHEMA_REF)
            if name not in found:
                found.add(name)
                walk(schemas[name])
        for value in node.values():
            walk(value)

    for root in roots:
        walk(root)
    return found


def request_roots(spec: dict[str, Any]) -> Iterator[object]:
    """Each request body and each parameter of the operations the SDK calls."""
    for operation in operations(spec):
        if "requestBody" in operation:
            yield resolve(spec, operation["requestBody"])
        for parameter in operation["parameters"]:
            yield resolve(spec, parameter)


def response_roots(spec: dict[str, Any]) -> Iterator[object]:
    """Each `2xx` answer of the operations the SDK calls."""
    for operation in operations(spec):
        for status, response in operation["responses"].items():
            if str(status).startswith("2"):
                yield resolve(spec, response).get("content", {})


def subset(spec: dict[str, Any], names: set[str]) -> dict[str, Any]:
    """A document holding only the named component schemas, in the document's order."""
    schemas: dict[str, Any] = spec["components"]["schemas"]
    return {
        "openapi": spec["openapi"],
        "info": spec["info"],
        "paths": {},
        "components": {"schemas": {n: s for n, s in schemas.items() if n in names}},
    }


def run_generator(
    document: dict[str, Any],
    output: Path,
    flags: Iterable[str],
    overrides: dict[str, str],
    name_map: dict[str, str] | None = None,
) -> None:
    with tempfile.TemporaryDirectory() as scratch:
        source = Path(scratch) / "openapi.yaml"
        source.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        command = [
            sys.executable,
            "-m",
            "datamodel_code_generator",
            "--input",
            str(source),
            "--output",
            str(output),
            "--custom-file-header",
            HEADER,
            *COMMON_FLAGS,
            *flags,
            "--type-overrides",
            json.dumps(overrides),
        ]
        if name_map:
            command += ["--model-name-map", json.dumps(name_map)]
        subprocess.run(command, check=True, cwd=PACKAGE, capture_output=True, text=True)


def ruff(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "ruff", *args], check=True, cwd=PACKAGE, capture_output=True
    )


def generate(spec_path: Path, out_dir: Path) -> None:
    """Writes `requests.py` and `responses.py` into `out_dir` from the document at
    `spec_path`."""
    spec: dict[str, Any] = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    requests = out_dir / "requests.py"
    responses = out_dir / "responses.py"
    run_generator(
        subset(spec, reached(spec, request_roots(spec))),
        requests,
        REQUEST_FLAGS,
        REQUEST_OVERRIDES,
    )
    run_generator(
        subset(spec, reached(spec, response_roots(spec))),
        responses,
        RESPONSE_FLAGS,
        RESPONSE_OVERRIDES,
        RESPONSE_NAME_MAP,
    )
    files = [str(requests), str(responses)]
    # The package's own configuration applies, so the files pass the lint unchanged.
    ruff("check", "--fix-only", "--quiet", "--config", str(PACKAGE / "pyproject.toml"), *files)
    ruff("format", "--quiet", "--config", str(PACKAGE / "pyproject.toml"), *files)


def stale(spec_path: Path, committed: Path) -> list[str]:
    """The names of the committed files that differ from a fresh generation."""
    with tempfile.TemporaryDirectory() as scratch:
        fresh = Path(scratch)
        generate(spec_path, fresh)
        return [
            name
            for name in ("requests.py", "responses.py")
            if not (committed / name).is_file()
            or (committed / name).read_bytes() != (fresh / name).read_bytes()
        ]


def main(argv: list[str]) -> int:
    if argv == ["--check"]:
        names = stale(SPEC, OUTPUT_DIR)
        for name in names:
            print(f"{name} is stale: run scripts/generate.py", file=sys.stderr)
        return 1 if names else 0
    if argv:
        print("usage: generate.py [--check]", file=sys.stderr)
        return 2
    generate(SPEC, OUTPUT_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
