# Copyright(C) 2026 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
"""``check_wheel_starter_skills.py`` fails a flagship wheel missing a starter skill."""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1] / "packaging" / "check_wheel_starter_skills.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("gaia_check_starter", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = _load()


@pytest.fixture
def skills_dir(tmp_path, monkeypatch):
    root = tmp_path / "skills"
    for name in ("alpha", "beta"):
        (root / name).mkdir(parents=True)
        (root / name / "SKILL.md").write_text("---\nname: x\n---\n")
    (root / "no-skill-md").mkdir()
    (root / "README.md").write_text("not a skill")
    monkeypatch.setattr(check, "STARTER_SKILLS", root)
    return root


def _wheel(tmp_path: Path, names: list[str]) -> Path:
    path = tmp_path / "gaia_agent_gaia-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("gaia_agent/__init__.py", "")
        archive.writestr("gaia_agent/skills/notes.txt", "")
        for name in names:
            archive.writestr(f"gaia_agent/skills/{name}/SKILL.md", "")
            archive.writestr(f"gaia_agent/skills/{name}/extra.md", "")
        archive.writestr("other/skills/ghost/SKILL.md", "")
    return path


def _run(monkeypatch, wheel: Path) -> int:
    monkeypatch.setattr(sys, "argv", ["check", str(wheel)])
    return check.main()


def test_starter_names_need_a_skill_md(skills_dir):
    assert check.starter_skill_names() == {"alpha", "beta"}


def test_missing_starter_dir_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(check, "STARTER_SKILLS", tmp_path / "absent")
    with pytest.raises(FileNotFoundError, match="starter skill directory"):
        check.starter_skill_names()


def test_wheel_names_only_read_gaia_agent_skills(tmp_path):
    assert check.wheel_skill_names(_wheel(tmp_path, ["alpha"])) == {"alpha"}


def test_complete_wheel_passes(skills_dir, tmp_path, monkeypatch, capsys):
    assert _run(monkeypatch, _wheel(tmp_path, ["alpha", "beta", "bonus"])) == 0
    assert "verified 2 starter skills" in capsys.readouterr().out


def test_wheel_missing_a_skill_fails_and_names_it(skills_dir, tmp_path, monkeypatch):
    with pytest.raises(SystemExit, match="missing starter skills: beta"):
        _run(monkeypatch, _wheel(tmp_path, ["alpha"]))


def test_checkout_has_starter_skills():
    assert check.starter_skill_names(), "hub/skills/ has no SKILL.md directories"
