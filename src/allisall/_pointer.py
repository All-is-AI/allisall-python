"""JSON Pointers (RFC 6901), as the encoder and the decoder name a value in their errors."""


def escape(name: str) -> str:
    """A member name as one JSON Pointer reference token: `~` as `~0`, `/` as `~1`."""
    return name.replace("~", "~0").replace("/", "~1")
