from __future__ import annotations

from pathlib import Path

from app.channels.base import ExportFile, ExportMetadata, OutputChannel, PushResult


class LocalFilesystemChannel(OutputChannel):
    name = "local_filesystem"
    description = "Save exports to exports/{fund}/{stichtag}/ on the local filesystem."

    def __init__(self, base_dir: str | Path = "exports"):
        self.base_dir = Path(base_dir)

    def _destination_dir(self, metadata: ExportMetadata) -> Path:
        return self.base_dir / metadata.fund / metadata.stichtag.isoformat()

    def test_connection(self) -> bool:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
        return self.base_dir.is_dir()

    def push(self, files: list[ExportFile], metadata: ExportMetadata) -> PushResult:
        destination_dir = self._destination_dir(metadata)
        errors: list[str] = []
        files_pushed = 0

        try:
            destination_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return PushResult(
                success=False,
                channel=self.name,
                files_pushed=0,
                destination=str(destination_dir),
                errors=[str(exc)],
            )

        for export_file in files:
            target = destination_dir / export_file.filename
            try:
                target.write_bytes(export_file.content)
                files_pushed += 1
            except OSError as exc:
                errors.append(f"{export_file.filename}: {exc}")

        return PushResult(
            success=not errors,
            channel=self.name,
            files_pushed=files_pushed,
            destination=str(destination_dir),
            errors=errors,
        )
