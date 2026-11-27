"""Walks folders of scanned contracts on disk; every file is stored once, by its bytes."""

import mimetypes
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


def nfc(text: str) -> str:
    # macOS stores names decomposed (NFD); everything else expects composed text.
    return unicodedata.normalize("NFC", text)


@dataclass(frozen=True)
class DiskFile:
    path: str
    absolute: Path
    content_type: str


def _skip(name: str) -> bool:
    # Hidden files and Office lock files ("~$name.docx") are not documents.
    return name.startswith((".", "~$"))


def walk(folder: Path) -> Iterator[DiskFile]:
    """Every document under `folder`, its path given relative to the folder's parent."""
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder.parent)
        if path.is_file() and not any(_skip(p) for p in relative.parts):
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            yield DiskFile(path=nfc(relative.as_posix()), absolute=path, content_type=content_type)
