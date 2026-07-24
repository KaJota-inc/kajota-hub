from importlib import resources
from typing import NewType

import yaml

from payflow.models import Dialect, ResponseCode

KB = NewType("KB", dict[tuple[Dialect, str], ResponseCode])

DIALECT_FILES: dict[Dialect, str] = {
    Dialect.CORE: "core.yaml",
    Dialect.FINACLE: "finacle.yaml",
    Dialect.FLEXCUBE: "flexcube.yaml",
    Dialect.GTB: "gtb.yaml",
    Dialect.POSTILION: "postilion.yaml",
    Dialect.UBN: "ubn.yaml",
}


def load_kb() -> KB:
    """Load all dialect YAMLs. Keyed by (dialect, code) so the same numeric code
    across dialects resolves to different entries — the whole point of this KB.
    """
    kb: dict[tuple[Dialect, str], ResponseCode] = {}
    for dialect, filename in DIALECT_FILES.items():
        with resources.files("payflow.kb").joinpath(filename).open() as f:
            data = yaml.safe_load(f) or {}
        for code, meta in (data.get("codes") or {}).items():
            code_str = str(code)
            kb[(dialect, code_str)] = ResponseCode(
                dialect=dialect, code=code_str, **meta
            )
    return KB(kb)


def lookup(kb: KB, dialect: Dialect, code: str) -> ResponseCode | None:
    return kb.get((dialect, code))
