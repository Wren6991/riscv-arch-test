# SPDX-License-Identifier: BSD-3-Clause
#
# Minimal Python reimplementation of the riscv-unified-db (UDB) operations
# that the ACT framework needs, replacing the `udb` and `udb-gen` Ruby gems:
#
#   * `udb validate cfg`     -> validate_config()
#   * `udb list extensions`  -> resolve_extension_closure()
#   * `udb-gen cfg-c-header` -> generate_config_header(svh=False)
#   * `udb-gen cfg-svh-header` -> generate_config_header(svh=True)
#
# Only the data files (extension definitions and their `requirements`) from
# the riscv-unified-db repository are needed.

from __future__ import annotations

import os
import re
from pathlib import Path

from ruamel.yaml import YAML


class UdbError(RuntimeError):
    pass


def _load_yaml(path: Path) -> dict:
    yaml = YAML(typ="safe", pure=True)
    with path.open() as f:
        return yaml.load(f)


def find_spec_dir() -> Path:
    """Locate the `spec/` directory of a riscv-unified-db checkout.

    Prefers the ``UDB_SPEC_DIR`` environment variable, then falls back to a
    sibling ``riscv-unified-db`` clone next to the repo root.
    """
    env = os.environ.get("UDB_SPEC_DIR")
    if env:
        return Path(env)

    here = Path(__file__).resolve()
    # framework/src/act/udb_resolver.py -> repo root is parents[3]
    sibling = here.parents[3].parent / "riscv-unified-db" / "spec"
    if sibling.is_dir():
        return sibling

    raise UdbError(
        "Unable to locate the riscv-unified-db spec directory. Set UDB_SPEC_DIR "
        "to the path of the `spec/` directory in a riscv-unified-db checkout."
    )


# ---------------------------------------------------------------------------
# Extension database
# ---------------------------------------------------------------------------


def load_extension_defs(spec_dir: Path) -> dict[str, dict]:
    defs: dict[str, dict] = {}
    ext_dir = spec_dir / "std" / "isa" / "ext"
    for path in sorted(ext_dir.glob("*.yaml")):
        data = _load_yaml(path)
        if data.get("kind") == "extension":
            defs[data["name"]] = data
    return defs


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------


def normalize_version(version: str) -> str:
    return re.sub(r"^\s*(?:>=|<=|~>|==|=|>|<)?\s*", "", str(version)).strip()


def _version_parts(version: str) -> tuple[int, int, int]:
    v = normalize_version(version).removesuffix("-pre")
    parts: list[int] = []
    for seg in v.split("."):
        seg = seg.strip()
        if not seg:
            continue
        match = re.match(r"\d+", seg)
        parts.append(int(match.group()) if match else 0)
    parts += [0] * (3 - len(parts))
    return (parts[0], parts[1], parts[2])


def versions_equal(a: str, b: str) -> bool:
    return _version_parts(a) == _version_parts(b)


def to_rvi_s(version: str) -> str:
    """Convert a version like '2.1' to the RVI string '2p1'."""
    v = normalize_version(version)
    pre = ""
    if v.endswith("-pre"):
        pre = "-pre"
        v = v[:-4]
    parts = [p for p in v.split(".") if p != ""]
    if not parts:
        return pre
    s = parts[0]
    if len(parts) >= 2:
        s += f"p{parts[1]}"
    if len(parts) >= 3:
        s += f"p{parts[2]}"
    return s + pre


def _first_version(ext_defs: dict[str, dict], name: str) -> str:
    ext = ext_defs.get(name)
    if ext:
        versions = ext.get("versions") or []
        if versions:
            return str(versions[0].get("version", "0"))
    return "0"


def _extension_requirements(ext: dict) -> list[object]:
    """Collect an extension's requirements from both the top level and any
    per-version `requirements` blocks (the DB uses both layouts)."""
    reqs: list[object] = []
    top = ext.get("requirements")
    if top is not None:
        reqs.append(top)
    for v in ext.get("versions") or []:
        r = v.get("requirements") if isinstance(v, dict) else None
        if r is not None:
            reqs.append(r)
    return reqs


# ---------------------------------------------------------------------------
# Extension closure
# ---------------------------------------------------------------------------


def _unconditional_extension_deps(req: object) -> list[tuple[str, str | None]]:
    """Extract (name, version) pairs unconditionally required by a condition.

    Only `extension` requirements reached through `allOf` (not `anyOf`,
    `oneOf`, or `not`) are unconditional and therefore implied.
    """
    deps: list[tuple[str, str | None]] = []
    if isinstance(req, dict):
        ext = req.get("extension")
        if isinstance(ext, dict):
            if "name" in ext:
                deps.append((str(ext["name"]), ext.get("version")))
            for e in ext.get("allOf") or []:
                if isinstance(e, dict) and "name" in e:
                    deps.append((str(e["name"]), e.get("version")))
        for sub in req.get("allOf") or []:
            deps.extend(_unconditional_extension_deps(sub))
    elif isinstance(req, list):
        for sub in req:
            deps.extend(_unconditional_extension_deps(sub))
    return deps


def resolve_extension_closure(config: dict, ext_defs: dict[str, dict]) -> dict[str, str]:
    """Return {extension_name: version} for every implemented extension,
    including those implied unconditionally by the implemented set.
    """
    result: dict[str, str] = {}
    queue: list[str] = []
    for e in config.get("implemented_extensions", []):
        name = str(e["name"])
        result[name] = normalize_version(str(e.get("version", "0")))
        queue.append(name)

    while queue:
        name = queue.pop(0)
        ext = ext_defs.get(name)
        if ext is None:
            continue
        for req in _extension_requirements(ext):
            for dep_name, dep_ver in _unconditional_extension_deps(req):
                if dep_name not in result:
                    result[dep_name] = (
                        normalize_version(str(dep_ver)) if dep_ver else _first_version(ext_defs, dep_name)
                    )
                    queue.append(dep_name)

    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _condition_satisfied(cond: object, implemented: set[str], mlen: int | None) -> bool:
    if isinstance(cond, list):
        return all(_condition_satisfied(c, implemented, mlen) for c in cond)
    if not isinstance(cond, dict):
        return True
    if "extension" in cond:
        ext = cond["extension"]
        if isinstance(ext, dict):
            if "name" in ext:
                return str(ext["name"]) in implemented
            if "allOf" in ext:
                return all(_condition_satisfied(c, implemented, mlen) for c in ext["allOf"])
        return True
    if "name" in cond:
        return str(cond["name"]) in implemented
    if "allOf" in cond:
        return all(_condition_satisfied(c, implemented, mlen) for c in cond["allOf"])
    if "anyOf" in cond:
        return any(_condition_satisfied(c, implemented, mlen) for c in cond["anyOf"])
    if "oneOf" in cond:
        return sum(1 for c in cond["oneOf"] if _condition_satisfied(c, implemented, mlen)) == 1
    if "not" in cond:
        return not _condition_satisfied(cond["not"], implemented, mlen)
    if "xlen" in cond:
        x = cond["xlen"]
        return mlen == int(x) if isinstance(x, (int, str)) else mlen in x
    return True


def validate_config(config: dict, ext_defs: dict[str, dict]) -> None:
    """Validate a fully-configured UDB config, raising UdbError on failure."""
    if config.get("type") != "fully configured":
        raise UdbError("Only 'fully configured' UDB configs are supported")

    for key in ("kind", "type", "name", "description", "implemented_extensions", "params"):
        if key not in config:
            raise UdbError(f"Config is missing required key: {key}")

    params = config.get("params") or {}
    mlen = params.get("MXLEN")
    implemented = {str(e["name"]) for e in config["implemented_extensions"]}

    for e in config["implemented_extensions"]:
        name = str(e["name"])
        if name not in ext_defs:
            raise UdbError(f"Unknown extension '{name}'")
        version = normalize_version(str(e["version"]))
        db_versions = [str(v.get("version", "")) for v in ext_defs[name].get("versions", [])]
        if db_versions and not any(versions_equal(version, dv) for dv in db_versions):
            raise UdbError(f"Extension '{name}' has no version {version} (known: {', '.join(db_versions)})")

    closure = set(resolve_extension_closure(config, ext_defs))
    for name in implemented:
        for req in _extension_requirements(ext_defs[name]):
            if not _condition_satisfied(req, closure, mlen):
                raise UdbError(f"Requirements for extension '{name}' are not satisfied by the config")


# ---------------------------------------------------------------------------
# Config header generation (mirrors udb-gen cfg-c-header / cfg-svh-header)
# ---------------------------------------------------------------------------


def _sanitize_identifier(value: str) -> str:
    out = "".join(c if c.isalnum() else "_" for c in value.upper())
    out = "_".join(p for p in out.split("_") if p)
    return out


def generate_config_header(config: dict, ext_defs: dict[str, dict], *, svh: bool) -> str:
    name = str(config["name"])
    closure = resolve_extension_closure(config, ext_defs)

    define = "`define" if svh else "#define"
    guard_suffix = "_SVH" if svh else "_H"
    guard = f"UDB_CFG_{_sanitize_identifier(name)}{guard_suffix}"

    lines: list[str] = []

    if svh:
        lines.append("// SPDX-License-Identifier: BSD-3-Clause-Clear")
        lines.append("//")
        lines.append("// Auto-generated by riscv-arch-test (replaces udb-gen cfg-svh-header)")
        lines.append(f"// Config: {name}")
        lines.append("//")
        lines.append("// Define conventions:")
        lines.append("//   Extensions:    `define NAME_SUPPORTED and `define NAMEverPver_SUPPORTED")
        lines.append("//   Boolean params: `define UDB_NAME (present when true)")
        lines.append("//   Integer params: `define UDB_NAME value and `define UDB_NAME_<value>")
        lines.append("//")
        lines.append(f"`ifndef {guard}")
        lines.append(f"`define {guard}")
    else:
        lines.append("/*")
        lines.append(" * SPDX-License-Identifier: BSD-3-Clause-Clear")
        lines.append(" *")
        lines.append(" * Auto-generated by riscv-arch-test (replaces udb-gen cfg-c-header)")
        lines.append(f" * Config: {name}")
        lines.append(" *")
        lines.append(" * Define conventions:")
        lines.append(" *   Extensions:    #define NAME_SUPPORTED and #define NAMEverPver_SUPPORTED")
        lines.append(" *   Boolean params: #define UDB_NAME (present when true)")
        lines.append(" *   Integer params: #define UDB_NAME value and #define UDB_NAME_<value>")
        lines.append(" */")
        lines.append("")
        lines.append(f"#ifndef {guard}")
        lines.append(f"#define {guard}")

    lines.append("")
    if svh:
        lines.append("// Implemented extensions")
    else:
        lines.append("/* Implemented extensions */")
    for ext_name in sorted(closure):
        version = closure[ext_name]
        lines.append(f"{define} {ext_name.upper()}_SUPPORTED")
        lines.append(f"{define} {ext_name.upper()}{to_rvi_s(version).upper()}_SUPPORTED")

    lines.append("")
    if svh:
        lines.append("// Configuration parameters")
    else:
        lines.append("/* Configuration parameters */")
    for param_name in sorted(config.get("params", {})):
        value = config["params"][param_name]
        lines.extend(_emit_param(define, param_name, value, svh))

    lines.append("")
    if svh:
        lines.append(f"`endif // {guard}")
    else:
        lines.append(f"#endif /* {guard} */")

    return "\n".join(lines) + "\n"


def _emit_param(define: str, name: str, value: object, svh: bool) -> list[str]:
    prefixed = f"UDB_{name}"
    lines: list[str] = []

    if value is True:
        lines.append(f"{define} {prefixed}")
    elif value is False:
        pass
    elif isinstance(value, int):
        lines.append(f"{define} {prefixed} {_fmt_int(value, svh)}")
        lines.append(f"{define} {prefixed}_{value}")
    elif isinstance(value, str):
        lines.append(f"{define} {prefixed}_{_sanitize_identifier(value)}")
    elif isinstance(value, list):
        if all(isinstance(v, bool) for v in value):
            for i, v in enumerate(value):
                if v:
                    lines.append(f"{define} {prefixed}_{i}")
        elif all(isinstance(v, int) for v in value):
            for v in sorted(set(value)):
                lines.append(f"{define} {prefixed}_{v}")
        elif all(isinstance(v, str) for v in value):
            for v in sorted({_sanitize_identifier(x) for x in value}):
                lines.append(f"{define} {prefixed}_{v}")

    return lines


def _fmt_int(value: int, svh: bool) -> str:
    if not svh:
        return str(value)
    width = max(32, ((value.bit_length() + 31) // 32) * 32)
    return f"{width}'h{value:X}"
