"""학생용 노트북에서 튜토리얼 저장소 루트를 찾는 작은 도우미."""

from __future__ import annotations

from pathlib import Path


def repository_root(start: str | Path | None = None) -> Path:
    current = Path(start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "firmware" / "prebuilt").is_dir():
            return candidate
    raise FileNotFoundError("ChipWhisperer tutorial 저장소 안에서 노트북을 실행하십시오.")
