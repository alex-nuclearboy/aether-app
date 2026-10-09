"""Sphinx configuration for the Aether documentation."""

# Sphinx configuration variables intentionally follow Sphinx naming conventions.
# pylint: disable=invalid-name,redefined-builtin

import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject_file:
    project_metadata = tomllib.load(pyproject_file)["project"]

project = "Aether"
author = "Aether"
copyright = "2026, Aether"
release = str(project_metadata["version"])
version = release

extensions: list[str] = []
root_doc = "index"

language = "en"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
nitpicky = True

html_theme = "alabaster"
html_title = f"{project} documentation"
