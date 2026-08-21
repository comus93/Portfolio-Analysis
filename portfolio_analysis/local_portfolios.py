"""Local persistence for named portfolio presets and the last UI session."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

SCHEMA_VERSION = 1
APP_DIRECTORY = "Portfolio-Analysis"
STORE_FILENAME = "portfolios.json"
ASSET_FIELDS = ("Code", "Name", "Type", "Market", "Weight")


class LocalPortfolioStoreError(Exception):
    """Raised when the local portfolio file cannot be read or written safely."""


def default_store_path() -> Path:
    """Return an OS-local data path outside the project and virtual environment."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base_directory = Path(local_app_data)
    else:
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        base_directory = (
            Path(xdg_data_home)
            if xdg_data_home
            else Path.home() / ".local" / "share"
        )
    return base_directory / APP_DIRECTORY / STORE_FILENAME


def empty_store() -> dict[str, Any]:
    """Create an empty store document."""
    return {
        "version": SCHEMA_VERSION,
        "presets": {},
        "last_session": {"portfolio": [], "benchmark": []},
    }


def make_asset_records(
    assets: list[dict[str, Any]], weights: list[float]
) -> list[dict[str, Any]]:
    """Combine current UI metadata with fractional weights for persistence."""
    if len(assets) != len(weights):
        raise ValueError("종목 수와 비중 수가 일치하지 않습니다.")

    records = []
    for asset, weight in zip(assets, weights):
        records.append(
            {
                "Code": str(asset.get("Code", "")).strip().upper(),
                "Name": str(asset.get("Name", "")),
                "Type": str(asset.get("Type", "")),
                "Market": str(asset.get("Market", "")),
                "Weight": float(weight) * 100.0,
            }
        )
    return records


def split_asset_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[float]]:
    """Return independent UI metadata and fractional weights from stored records."""
    assets = [
        {
            field: (
                str(record[field]).strip().upper()
                if field == "Code"
                else str(record[field])
            )
            for field in ASSET_FIELDS
            if field != "Weight"
        }
        for record in records
    ]
    weights = [float(record["Weight"]) / 100.0 for record in records]
    return assets, weights


class LocalPortfolioStore:
    """Read and atomically update the user's local portfolio JSON document."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_store_path()

    def load(self) -> dict[str, Any]:
        """Load and validate the store; a missing file is a normal first run."""
        if not self.path.exists():
            return empty_store()
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                document = json.load(handle)
            self._validate_document(document)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise LocalPortfolioStoreError(
                f"로컬 Portfolio 저장 파일을 읽을 수 없습니다: {self.path}. "
                "빈 상태로 계속 실행합니다."
            ) from exc
        return deepcopy(document)

    def save_preset(self, name: str, records: list[dict[str, Any]]) -> None:
        """Create or overwrite a named preset."""
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Preset 이름을 입력하세요.")
        self._validate_records(records, require_total=True)
        document = self.load()
        document["presets"][normalized_name] = deepcopy(records)
        self._write(document)

    def delete_preset(self, name: str) -> bool:
        """Delete a named preset, returning whether it existed."""
        document = self.load()
        existed = name in document["presets"]
        if existed:
            del document["presets"][name]
            self._write(document)
        return existed

    def save_last_session(
        self,
        portfolio: list[dict[str, Any]],
        benchmark: list[dict[str, Any]],
    ) -> None:
        """Persist the current editable workspace without changing presets."""
        self._validate_records(portfolio, require_total=False)
        self._validate_records(benchmark, require_total=False)
        document = self.load()
        document["last_session"] = {
            "portfolio": deepcopy(portfolio),
            "benchmark": deepcopy(benchmark),
        }
        self._write(document)

    def _write(self, document: dict[str, Any]) -> None:
        self._validate_document(document)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                temporary_path = Path(handle.name)
            os.replace(temporary_path, self.path)
        except OSError as exc:
            if "temporary_path" in locals():
                temporary_path.unlink(missing_ok=True)
            raise LocalPortfolioStoreError(
                f"로컬 Portfolio 저장 파일을 쓸 수 없습니다: {self.path}"
            ) from exc

    @classmethod
    def _validate_document(cls, document: Any) -> None:
        if not isinstance(document, dict) or document.get("version") != SCHEMA_VERSION:
            raise ValueError("지원하지 않는 로컬 Portfolio 저장 형식입니다.")
        presets = document.get("presets")
        last_session = document.get("last_session")
        if not isinstance(presets, dict) or not isinstance(last_session, dict):
            raise ValueError("로컬 Portfolio 저장 구조가 올바르지 않습니다.")
        if set(last_session) != {"portfolio", "benchmark"}:
            raise ValueError("Last Session 저장 구조가 올바르지 않습니다.")
        for name, records in presets.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Preset 이름이 올바르지 않습니다.")
            cls._validate_records(records, require_total=True)
        cls._validate_records(last_session["portfolio"], require_total=False)
        cls._validate_records(last_session["benchmark"], require_total=False)

    @staticmethod
    def _validate_records(records: Any, require_total: bool) -> None:
        if not isinstance(records, list):
            raise ValueError("종목 구성은 목록이어야 합니다.")
        codes = []
        for record in records:
            if not isinstance(record, dict) or set(record) != set(ASSET_FIELDS):
                raise ValueError("저장된 종목 정보가 올바르지 않습니다.")
            code = record["Code"]
            if not isinstance(code, str) or not code:
                raise ValueError("저장된 종목코드가 올바르지 않습니다.")
            if any(not isinstance(record[field], str) for field in ASSET_FIELDS[:-1]):
                raise ValueError("저장된 종목 메타데이터가 올바르지 않습니다.")
            try:
                weight = float(record["Weight"])
            except (TypeError, ValueError) as exc:
                raise ValueError("저장된 비중이 숫자가 아닙니다.") from exc
            if not 0.0 <= weight <= 100.0:
                raise ValueError("저장된 비중은 0% 이상 100% 이하여야 합니다.")
            codes.append(code)
        if len(codes) != len(set(codes)):
            raise ValueError("동일한 종목코드를 중복 저장할 수 없습니다.")
        total = sum(float(record["Weight"]) for record in records)
        if require_total and (not records or abs(total - 100.0) > 1e-6):
            raise ValueError("Preset 비중 합계는 100%여야 합니다.")
