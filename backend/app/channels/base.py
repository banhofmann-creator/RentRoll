from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class ExportFile:
    filename: str
    content: bytes
    file_type: str
    category: str


@dataclass(slots=True)
class ExportMetadata:
    stichtag: date
    fund: str
    properties: list[str]
    reporting_period_id: int


@dataclass(slots=True)
class PushResult:
    success: bool
    channel: str
    files_pushed: int
    destination: str
    errors: list[str] = field(default_factory=list)


class OutputChannel(ABC):
    name = "output_channel"
    description = "Abstract output channel"

    @abstractmethod
    def push(self, files: list[ExportFile], metadata: ExportMetadata) -> PushResult:
        """Push generated files to the destination."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify credentials and connectivity."""
