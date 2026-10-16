"""La rueda instalada lleva los datos del paquete (``trawlkit/data``) y la CLI funciona sin el
checkout. Lento (construye la rueda y crea un entorno virtual): sólo corre con
``TRAWLKIT_PACKAGING_TEST=1``."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        os.environ.get("TRAWLKIT_PACKAGING_TEST") != "1",
        reason="test de empaquetado: definir TRAWLKIT_PACKAGING_TEST=1",
    ),
]


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"VIRTUAL_ENV", "PYTHONPATH"}}
    return subprocess.run(
        args, cwd=cwd, env=env, capture_output=True, text=True, check=False, timeout=600
    )


def test_wheel_installs_and_runs(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    assert uv, "hace falta uv en el PATH"
    dist = tmp_path / "dist"
    res = _run([uv, "build", "--wheel", "--out-dir", str(dist)], cwd=ROOT)
    assert res.returncode == 0, res.stderr
    (wheel,) = dist.glob("trawlkit-*.whl")

    venv = tmp_path / "venv"
    res = _run([uv, "venv", "--python", sys.executable, str(venv)], cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    bindir = venv / ("Scripts" if os.name == "nt" else "bin")
    python = next(bindir.glob("python*"))
    res = _run([uv, "pip", "install", "--python", str(python), str(wheel)], cwd=tmp_path)
    assert res.returncode == 0, res.stderr

    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    res = _run([str(bindir / "trawlkit"), "run", "fao_a3_standard"], cwd=cwd)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "Lima" in res.stdout
    # Los datos salen de la rueda instalada, no del checkout.
    res = _run([str(python), "-c", "from trawlkit.io import DATA_DIR; print(DATA_DIR)"], cwd=cwd)
    assert res.returncode == 0, res.stderr
    data_dir = Path(res.stdout.strip())
    assert (data_dir / "fao_a3_standard.yaml").is_file()
    assert (data_dir / "reference" / "catenary.csv").is_file()
    assert ROOT not in data_dir.parents
