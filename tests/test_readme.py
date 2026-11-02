"""The README's examples type-check against the package, as written.

Each ```python block of README.md is written to a file of its own and
checked with mypy --strict, as the package's own source is. The examples
are checked, never run, so none of them reaches the network.
"""

import re
from pathlib import Path

from mypy import api

README = Path(__file__).resolve().parent.parent / "README.md"


def readme_examples() -> list[str]:
    text = README.read_text(encoding="utf-8").replace("\r\n", "\n")
    return re.findall(r"```python\n(.*?)```", text, re.DOTALL)


def test_the_readme_has_examples() -> None:
    assert readme_examples(), "README.md has no python examples"


def test_the_readme_examples_type_check(tmp_path: Path) -> None:
    files = []
    for i, code in enumerate(readme_examples(), start=1):
        path = tmp_path / f"example_{i}.py"
        path.write_text(code, encoding="utf-8")
        files.append(str(path))
    stdout, stderr, status = api.run(
        ["--strict", "--python-version", "3.11", "--no-incremental", "--config-file", "", *files]
    )
    assert status == 0, stdout + stderr


def test_a_wrong_example_fails_the_check(tmp_path: Path) -> None:
    # The check above would pass on a mypy that never read the package.
    path = tmp_path / "wrong.py"
    path.write_text(
        "from allisall import Allisall\n\nAllisall(max_retries='two')\n", encoding="utf-8"
    )
    stdout, _, status = api.run(
        ["--strict", "--python-version", "3.11", "--no-incremental", "--config-file", "", str(path)]
    )
    assert status == 1
    assert "max_retries" in stdout
