from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from io import BytesIO
from typing import Any


@dataclass
class ParseMetadata:
    fund_label: str | None = None
    stichtag: date | None = None
    column_headers: list[str] = field(default_factory=list)
    column_fingerprint: str = ""


@dataclass
class ParseResult:
    metadata: ParseMetadata
    rows: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


class RentRollParser(ABC):
    @staticmethod
    @abstractmethod
    def detect(file_content: bytes, filename: str) -> bool:
        """Return True if this parser can handle the given file."""

    @abstractmethod
    def extract_metadata(self, file_content: bytes) -> ParseMetadata:
        """Extract header metadata (fund label, stichtag, column headers) without parsing all rows."""

    @abstractmethod
    def parse(self, file_content: bytes) -> ParseResult:
        """Parse the full file and return normalized row dicts ready for DB insertion."""
