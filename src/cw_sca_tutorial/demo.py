"""학생용 노트북이 검증된 실측 run을 찾는 작은 도우미."""

from __future__ import annotations

import json
from pathlib import Path


def repository_root(start: str | Path | None = None) -> Path:
    current = Path(start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "data" / "demo_runs.json").is_file():
            return candidate
    raise FileNotFoundError("data/demo_runs.json을 찾지 못했습니다. 저장소 안에서 노트북을 실행하십시오.")


def demo_run(name: str, start: str | Path | None = None) -> Path:
    root = repository_root(start)
    manifest = json.loads((root / "data" / "demo_runs.json").read_text(encoding="utf-8"))
    if name not in manifest:
        raise KeyError(f"demo run 이름이 없습니다: {name}")
    run = root / manifest[name]
    metadata_path = run / "metadata.json"
    traces_path = run / "traces.npz"
    if not metadata_path.is_file() or not traces_path.is_file():
        raise FileNotFoundError(f"실측 run 파일이 없습니다: {run}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("state") != "complete":
        raise RuntimeError(f"완료되지 않은 run입니다: {run}")
    return run
