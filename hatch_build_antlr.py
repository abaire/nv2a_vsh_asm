"""Custom build hook to generate parser using Antlr."""

# ruff: noqa: S607 Starting a process with a partial executable path
# ruff: noqa: TRY002 Create your own exception

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class GenerateParserBuildHook(BuildHookInterface):
    """Hatchling plugin to generate the VSH parser using Antlr"""

    PLUGIN_NAME = "generateparser"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Generate ANTLR4 parsers."""

        del version

        grammar_file = Path("src", "grammar/Vsh.g4")
        output_dir = Path("src", "nv2a_vsh", "grammar", "vsh")
        shutil.rmtree(output_dir, ignore_errors=True)

        result = subprocess.run(
            [
                "antlr4",
                "-o",
                str(output_dir),
                "-Xexact-output-dir",
                "-Dlanguage=Python3",
                "-visitor",  # Optional, if you use visitors
                str(grammar_file),
                "-package",
                "nv2a_vsh.grammar",
            ],
            check=False,
            capture_output=True,
            encoding="utf-8",
        )

        if result.returncode != 0:
            print(result.stdout)  # noqa: T201 `print` found
            print(result.stderr)  # noqa: T201 `print` found
            msg = f"ANTLR4 generation failed with return code {result.returncode}"
            raise Exception(msg)

        build_data["artifacts"].extend([str(file.relative_to(".")) for file in output_dir.glob("*")])
