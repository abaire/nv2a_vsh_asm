"""Custom build hook to generate parser using Antlr."""

# ruff: noqa: TRY002 Create your own exception
# ruff: noqa: T201 `print` found

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

# Import the tool function directly.
# This works because antlr4-tools is in your [build-system] requires.
from antlr4_tool_runner import tool
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

        print(f"Generating parser for {grammar_file}...")

        # Patch sys.argv because antlr4-tools reads from it by default.
        old_argv = sys.argv
        sys.argv = [
            "antlr4",
            "-o",
            str(output_dir),
            "-Xexact-output-dir",
            "-Dlanguage=Python3",
            "-visitor",
            "-package",
            "nv2a_vsh.grammar",
            str(grammar_file),
        ]

        try:
            tool()
        except SystemExit as e:
            if e.code != 0:
                msg = f"ANTLR4 generation failed with exit code {e.code}"
                raise Exception(msg) from None
        except Exception as e:
            msg = f"ANTLR4 generation failed: {e}"
            raise Exception(msg) from e
        finally:
            sys.argv = old_argv

        generated_files = list(output_dir.glob("*"))
        if not generated_files:
            msg = f"ANTLR4 completed but no files were generated in {output_dir}"
            raise Exception(msg)

        build_data["artifacts"].extend([str(file.relative_to(".")) for file in generated_files])
