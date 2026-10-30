from __future__ import annotations

import json
from pathlib import Path
import sys


SOURCE_NAME = "SOLN_Lab 2_1B - Power Analysis for Password Bypass.ipynb"
OUTPUT_NAME = "SOLN_Lab 2_1B - Power Analysis for Password Bypass - CWLITEARM.ipynb"
CONFIG_SOURCE = (
    'SCOPETYPE = "OPENADC"\n'
    'PLATFORM = "CWLITEARM"\n'
    'CRYPTO_TARGET = "NONE"\n'
    'SS_VER = "SS_VER_2_1"\n'
    'VERSION = "HARDWARE"'
)
KERNEL_NAME = "chipwhisperer-official-f303"
KERNEL_DISPLAY_NAME = "Python (Official ChipWhisperer, F303)"


def _cell_source(cell: dict[str, object]) -> str:
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else str(source)


def _is_ready(notebook: dict[str, object]) -> bool:
    cells = notebook.get("cells", [])
    config_ready = any(
        cell.get("cell_type") == "code" and _cell_source(cell).strip() == CONFIG_SOURCE
        for cell in cells
    )
    metadata = notebook.get("metadata", {})
    kernelspec = metadata.get("kernelspec", {}) if isinstance(metadata, dict) else {}
    return config_ready and kernelspec.get("name") == KERNEL_NAME


def prepare_notebook(official_root: Path) -> Path:
    course_dir = official_root / "jupyter" / "courses" / "sca101"
    source_path = course_dir / SOURCE_NAME
    output_path = course_dir / OUTPUT_NAME
    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    if output_path.exists():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        if not _is_ready(existing):
            raise RuntimeError(f"existing notebook has unexpected hardware settings: {output_path}")
        return output_path

    notebook = json.loads(source_path.read_text(encoding="utf-8"))
    matches = [
        cell
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
        and "SCOPETYPE" in _cell_source(cell)
        and "PLATFORM" in _cell_source(cell)
        and "VERSION" in _cell_source(cell)
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one hardware configuration cell, found {len(matches)}")
    matches[0]["source"] = CONFIG_SOURCE.splitlines(keepends=True)

    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["execution_count"] = None
            cell["outputs"] = []

    metadata = notebook.setdefault("metadata", {})
    metadata["kernelspec"] = {
        "display_name": KERNEL_DISPLAY_NAME,
        "language": "python",
        "name": KERNEL_NAME,
    }

    output_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare_official_f303.py <official-chipwhisperer-root>")
    print(prepare_notebook(Path(sys.argv[1]).resolve()))
