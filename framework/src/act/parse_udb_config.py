##################################
# parse_udb_config.py
#
# jcarlin@hmc.edu 6 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Parse UDB configuration file
##################################

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from rich import print as rprint
from ruamel.yaml import YAML

from act.build import build
from act.build_types import BuildTask, PythonAction
from act.dut_macros import generate_rvmodel_svh
from act.udb_resolver import (
    UdbError,
    find_spec_dir,
    generate_config_header,
    load_extension_defs,
    resolve_extension_closure,
    validate_config,
)

if TYPE_CHECKING:
    from act.config import Config


#: Extension definitions loaded once and shared across all configs in a run.
_ext_defs: dict[str, dict] | None = None


def _get_ext_defs() -> dict[str, dict]:
    global _ext_defs
    if _ext_defs is None:
        _ext_defs = load_extension_defs(find_spec_dir())
    return _ext_defs


def _load_config_yaml(udb_config_file: Path) -> dict:
    yaml = YAML(typ="safe", pure=True)
    return yaml.load(udb_config_file.read_text())


def validate_udb_config(udb_config_file: Path, marker: Path) -> None:
    """Validate the UDB config and touch a sentinel marker on success.

    The marker is the BuildTask's primary output — its mtime drives the
    DAG's staleness check, so the validate runs once whenever the UDB
    config has changed and is then reused as a dep by every UDB-derived
    task for that config.
    """
    try:
        config = _load_config_yaml(udb_config_file)
        validate_config(config, _get_ext_defs())
    except (UdbError, OSError, ValueError) as e:
        raise RuntimeError(f"UDB configuration validation failed for {udb_config_file.name}\n{e}") from e
    marker.touch()


def prepare_dut_outputs(configs: list[Config], workdir: Path, jobs: int, verbose: bool) -> None:
    """Generate every DUT-derived file (extensions.txt, rvtest_config.{h,svh},
    rvmodel_macros.svh) for every config, in parallel, using the same
    `build()` DAG executor as the main pipeline.

    Per config we emit:
      - a `validate` BuildTask whose output is a sentinel marker;
      - one BuildTask per UDB-derived file, with the marker in `deps` so
        validation must succeed before any UDB generator runs;
      - a BuildTask for `rvmodel_macros.svh`, which has no UDB dependency.

    Staleness, parallel scheduling, the transient progress widget and the
    failure-skips-dependents behaviour are all handled by `build()`.
    """
    if not configs:
        return

    # Ensure the UDB spec directory can be found up front so a misconfigured
    # environment fails fast rather than once per config.
    _get_ext_defs()

    tasks: list[BuildTask] = []
    for cfg in configs:
        config_dir = workdir / cfg.name
        src = cfg.udb_config
        marker = config_dir / ".validated"

        # Validate the UDB config once per config; every UDB-derived file
        # below depends on this marker so it runs first.
        tasks.append(
            BuildTask(
                outputs=(marker,),
                action=PythonAction(validate_udb_config, (src, marker)),
                extra_inputs=(src,),
                label=f"UDB config validation ({cfg.name})",
            )
        )

        # UDB-derived per-config files: one BuildTask each, all gated on
        # the validate marker and stale vs. the source UDB yaml.
        udb_outputs: list[tuple[Path, PythonAction]] = [
            (
                config_dir / "rvtest_config.h",
                PythonAction(_generate_one_dut_header, (src, config_dir / "rvtest_config.h", "cfg-c-header")),
            ),
            (
                config_dir / "rvtest_config.svh",
                PythonAction(_generate_one_dut_header, (src, config_dir / "rvtest_config.svh", "cfg-svh-header")),
            ),
            (config_dir / "extensions.txt", PythonAction(generate_extension_list, (src, config_dir))),
        ]
        for out, action in udb_outputs:
            tasks.append(BuildTask(outputs=(out,), action=action, extra_inputs=(src,), deps=(marker,)))

        # rvmodel_macros.svh derives from the DUT's rvmodel_macros.h, not
        # from UDB, so it has no validate dep.
        tasks.append(
            BuildTask(
                outputs=(config_dir / "rvmodel_macros.svh",),
                action=PythonAction(generate_rvmodel_svh, (cfg.dut_include_dir, config_dir)),
                extra_inputs=(cfg.dut_include_dir / "rvmodel_macros.h",),
            )
        )

    start = time.monotonic()
    result = build(tasks, jobs=jobs, cache_root=workdir, verbose=verbose, phase_label="Preparing DUT configs")
    elapsed = time.monotonic() - start

    if result.errors:
        rprint(f"[bold red]✗ DUT prep failed:[/] {result.failed} task(s)", file=sys.stderr)
        sys.exit(1)

    n = len(configs)
    suffix = "all up to date" if result.succeeded == 0 else f"in {elapsed:.1f}s"
    rprint(f"[bold green]✓ DUT configs prepared:[/] {n} config{'s' if n != 1 else ''} {suffix}")


def get_config_params(udb_config_file: Path) -> dict[str, int | bool | str | list[int | str | bool]]:
    udb_config = _load_config_yaml(udb_config_file)
    return udb_config["params"]


def generate_extension_list(udb_config_file: Path, output_dir: Path) -> None:
    extension_list_file = output_dir / "extensions.txt"
    config = _load_config_yaml(udb_config_file)
    closure = resolve_extension_closure(config, _get_ext_defs())
    extension_list_file.write_text("\n".join(sorted(closure)) + "\n")


def get_implemented_extensions(extension_list_file: Path) -> set[str]:
    return set(extension_list_file.read_text().splitlines())


def _generate_one_dut_header(udb_config_file: Path, output_file: Path, subcommand: str) -> None:
    """Generate a DUT config header (C or SystemVerilog) from the UDB config."""
    config = _load_config_yaml(udb_config_file)
    svh = subcommand == "cfg-svh-header"
    output_file.write_text(generate_config_header(config, _get_ext_defs(), svh=svh))


# TODO: Generate Sail config file from UDB
