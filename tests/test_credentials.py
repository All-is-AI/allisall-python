"""A credential is trimmed, then must be printable ASCII without the space, U+0021 to U+007E.

Leading and trailing whitespace is removed first, and the trimmed value is the one sent. Any
other character outside the range is refused: at construction for an API key, and before
the attempt for a provider's token. The error never holds the credential or any part of it.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import pytest

from allisall import Allisall, AllisallError, AsyncAllisall, IngestError

from support import Harness, event

SECRET = "aia_SECRET0123456789"
REFUSED = "outside U+0021 to U+007E"

# C0 controls and DEL, which would split or end an HTTP header.
CONTROLS = ["\n", "\r", "\x00", "\t", "\x1f", "\x7f"]
# Characters a control-character check alone would let through.
NO_BREAK_SPACE = chr(0xA0)
OUTSIDE_ASCII = [" ", "é", "\U0001f511", NO_BREAK_SPACE]


def bad_keys() -> list[str]:
    # Every refused character sits where trimming cannot remove it: inside the key, or at an
    # end only when it is not whitespace.
    keys = [f"{SECRET}{c}X-Injected: 1" for c in CONTROLS + OUTSIDE_ASCII]
    keys += [f"{c}{SECRET}" for c in ("\x00", "\x7f", "é")]
    keys += [f"{SECRET}\U0001f511", f" {SECRET} x \n"]
    return keys


# Keys and tokens that trim to "aia_k".
PADDED = [" aia_k ", "aia_k\n", "\taia_k\r\n", "\n\n aia_k"]
BLANK = ["   ", "\n", "\t\r\n "]


def messages(err: BaseException) -> list[str]:
    """`str`, `repr` and `args` of the error and of every error under it."""
    found: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = err
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        found += [str(current), repr(current), *(str(a) for a in current.args)]
        current = current.__cause__ or current.__context__
    return found


def assert_secret_absent(err: BaseException, key: str) -> None:
    # A plain space is in every message, so only the other refused characters are checked.
    offending = [c for c in key if not 0x21 <= ord(c) <= 0x7E and c != " "]
    for text in messages(err):
        assert "SECRET" not in text, text
        assert "0123456789" not in text, text
        for char in offending:
            assert char not in text, text
            assert ascii(char)[1:-1] not in text, text


def construct(mode: str, **options: object) -> Allisall | AsyncAllisall:
    if mode == "sync":
        return Allisall(**options)  # type: ignore[arg-type]
    return AsyncAllisall(**options)  # type: ignore[arg-type]


@pytest.mark.parametrize("key", bad_keys())
def test_an_api_key_option_outside_printable_ascii_fails(mode: str, key: str) -> None:
    with pytest.raises(
        AllisallError, match=f"^{re.escape(f'api_key contains a character {REFUSED}')}$"
    ) as caught:
        construct(mode, api_key=key)
    assert_secret_absent(caught.value, key)


# An environment variable cannot hold NUL, so those keys are left out here.
@pytest.mark.parametrize("key", [k for k in bad_keys() if "\x00" not in k])
def test_an_environment_key_outside_printable_ascii_fails(
    mode: str, monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    monkeypatch.setenv("AIA_API_KEY", key)
    with pytest.raises(
        AllisallError, match=f"^{re.escape(f'AIA_API_KEY contains a character {REFUSED}')}$"
    ) as caught:
        construct(mode)
    assert_secret_absent(caught.value, key)


@pytest.mark.parametrize("key", bad_keys())
def test_a_provider_token_outside_printable_ascii_fails_the_batch(
    make: Callable[..., Harness], key: str
) -> None:
    calls = 0

    def provider() -> str:
        nonlocal calls
        calls += 1
        return key

    harness = make(token_provider=provider)
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(0), event(1)])
    error = caught.value

    assert harness.requests == []
    assert calls == 1
    assert harness.sleeps == []
    assert type(error.__cause__) is AllisallError
    assert REFUSED in str(error.__cause__)
    assert error.remaining_from == 0
    assert len(error.remaining) == 2
    assert_secret_absent(error, key)


def test_a_good_token_after_a_bad_one_is_not_reached(make: Callable[..., Harness]) -> None:
    # The refusal is not retried: the provider is not asked again.
    tokens = iter([f"{SECRET}é", "aia_good"])
    harness = make(token_provider=lambda: next(tokens))
    with pytest.raises(IngestError):
        harness.ingest([event(0)])
    assert harness.requests == []
    assert next(tokens) == "aia_good"


@pytest.mark.parametrize("key", [f"{SECRET}\r\nX", f"{SECRET} x", f"{SECRET}é"])
def test_an_async_provider_token_is_checked(key: str) -> None:
    async def provider() -> str:
        return key

    harness = Harness("async", token_provider=provider)
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(0)])
    assert harness.requests == []
    assert_secret_absent(caught.value, key)


PRINTABLE_ASCII = "".join(chr(code) for code in range(0x21, 0x7F))


@pytest.mark.parametrize("key", ["aia_plain", f"aia_{PRINTABLE_ASCII}", PRINTABLE_ASCII])
def test_printable_ascii_keys_are_accepted(make: Callable[..., Harness], key: str) -> None:
    harness = make(api_key=key)
    harness.ingest([event(0)])
    assert harness.requests[0].headers["authorization"] == f"Bearer {key}"


@pytest.mark.parametrize("key", [f"aia_{PRINTABLE_ASCII}", PRINTABLE_ASCII])
def test_printable_ascii_tokens_are_accepted(make: Callable[..., Harness], key: str) -> None:
    harness = make(token_provider=lambda: key)
    harness.ingest([event(0)])
    assert harness.requests[0].headers["authorization"] == f"Bearer {key}"


@pytest.mark.parametrize("key", PADDED)
def test_an_api_key_option_is_trimmed(make: Callable[..., Harness], key: str) -> None:
    harness = make(api_key=key)
    harness.ingest([event(0)])
    assert harness.requests[0].headers["authorization"] == "Bearer aia_k"


@pytest.mark.parametrize("key", PADDED)
def test_an_environment_key_is_trimmed(
    make: Callable[..., Harness], monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    monkeypatch.setenv("AIA_API_KEY", key)
    harness = make(api_key=None)
    harness.ingest([event(0)])
    assert harness.requests[0].headers["authorization"] == "Bearer aia_k"


@pytest.mark.parametrize("key", PADDED)
def test_a_provider_token_is_trimmed(make: Callable[..., Harness], key: str) -> None:
    harness = make(token_provider=lambda: key)
    harness.ingest([event(0)])
    assert harness.requests[0].headers["authorization"] == "Bearer aia_k"


@pytest.mark.parametrize("key", PADDED)
def test_an_async_provider_token_is_trimmed(key: str) -> None:
    async def provider() -> str:
        return key

    harness = Harness("async", token_provider=provider)
    harness.ingest([event(0)])
    assert harness.requests[0].headers["authorization"] == "Bearer aia_k"


@pytest.mark.parametrize("key", BLANK)
def test_a_blank_api_key_option_is_empty(mode: str, key: str) -> None:
    with pytest.raises(AllisallError, match=r"^api_key is empty$"):
        construct(mode, api_key=key)


@pytest.mark.parametrize("key", BLANK)
def test_a_blank_environment_key_is_missing(
    mode: str, monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    monkeypatch.setenv("AIA_API_KEY", key)
    with pytest.raises(AllisallError, match=r"^no credential"):
        construct(mode)


@pytest.mark.parametrize("key", [*BLANK, ""])
def test_a_blank_provider_token_fails_the_batch(make: Callable[..., Harness], key: str) -> None:
    harness = make(token_provider=lambda: key)
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(0)])
    assert harness.requests == []
    assert type(caught.value.__cause__) is AllisallError
    assert str(caught.value.__cause__) == "the token provider returned an empty token"


def test_a_space_inside_a_padded_key_is_still_refused(mode: str) -> None:
    with pytest.raises(AllisallError, match=re.escape(REFUSED)):
        construct(mode, api_key="  aia_k with space\n")
