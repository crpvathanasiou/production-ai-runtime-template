"""Application-owned telemetry port."""

from __future__ import annotations

from typing import Protocol

from app.application.execution import ApplicationTelemetryEvent


class TelemetryPort(Protocol):
    def emit(self, event: ApplicationTelemetryEvent) -> None: ...
