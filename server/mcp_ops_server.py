import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[1]
OPS_DIR = ROOT / "ops"

mcp = FastMCP("OPS-over-MCP Demo (stdio)")


# ----------------------------
# OPS: loader + ref resolution
# ----------------------------

@dataclass(frozen=True)
class OpsRef:
    id: str
    version_selector: str  # e.g. "1.2.0" or "1.x"

def parse_ref(ref: str) -> OpsRef:
    # "ops.lead_outreach@1.x"
    if "@" not in ref:
        raise ValueError("OPS ref must include '@', e.g. ops.lead_outreach@1.x")
    _id, ver = ref.split("@", 1)
    return OpsRef(id=_id.strip(), version_selector=ver.strip())

def version_key(v: str) -> Tuple[int, int, int]:
    parts = v.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))

def match_version(selector: str, v: str) -> bool:
    # supports "1.x" and exact "1.2.3"
    if selector.endswith(".x"):
        major = selector.split(".")[0]
        return v.split(".")[0] == major
    return selector == v

def load_all_ops_packages() -> List[Dict[str, Any]]:
    pkgs: List[Dict[str, Any]] = []
    for fp in OPS_DIR.glob("*.ops.json"):
        with fp.open("r", encoding="utf-8") as f:
            obj = json.load(f)
            obj["_file"] = str(fp)
            pkgs.append(obj)
    return pkgs

ALL_PKGS = load_all_ops_packages()

def resolve_ops_ref(ref: str) -> Dict[str, Any]:
    r = parse_ref(ref)
    candidates = [p for p in ALL_PKGS if p.get("id") == r.id]
    if not candidates:
        raise ValueError(f"OPS package not found: {r.id}")

    matched = [p for p in candidates if match_version(r.version_selector, p.get("version", ""))]
    if not matched:
        raise ValueError(f"No version match for {ref}. Available: {[p.get('version') for p in candidates]}")

    # choose highest version
    matched.sort(key=lambda p: version_key(p["version"]), reverse=True)
    return matched[0]

def deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merge b into a (dicts merged recursively, lists concatenated, scalars overwritten)."""
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        elif k in out and isinstance(out[k], list) and isinstance(v, list):
            out[k] = out[k] + v
        else:
            out[k] = v
    return out

def resolve_with_imports(pkg: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    lineage: List[str] = []
    merged: Dict[str, Any] = {}

    # imports first (so main pkg overrides)
    for imp in pkg.get("imports", []) or []:
        imp_ref = imp.get("ref")
        if not imp_ref:
            continue
        imp_pkg = resolve_ops_ref(imp_ref)
        imp_merged, imp_lineage = resolve_with_imports(imp_pkg)
        merged = deep_merge(merged, imp_merged)
        lineage.extend(imp_lineage)
        lineage.append(f"{imp_pkg['id']}@{imp_pkg['version']}")

    merged = deep_merge(merged, pkg)
    lineage.append(f"{pkg['id']}@{pkg['version']}")
    return merged, lineage


# ----------------------------
# OPS: policy + optimization
# ----------------------------

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\b(\+?\d[\d\s().-]{7,}\d)\b")
ADDRESS_RE = re.compile(r"\b\d{1,5}\s+\w+(\s+\w+){1,5}\b")

def apply_redactions(text: str, redactions: List[str]) -> str:
    out = text
    if "EMAIL" in redactions:
        out = EMAIL_RE.sub("[REDACTED_EMAIL]", out)
    if "PHONE" in redactions:
        out = PHONE_RE.sub("[REDACTED_PHONE]", out)
    if "ADDRESS" in redactions:
        out = ADDRESS_RE.sub("[REDACTED_ADDRESS]", out)
    return out

def approx_tokens(text: str) -> int:
    # very rough: ~4 chars/token (varies by language)
    return max(1, len(text) // 4)

def truncate_to_budget(lines: List[str], budget_tokens: int) -> Tuple[List[str], bool]:
    joined = "\n".join(lines)
    if approx_tokens(joined) <= budget_tokens:
        return lines, False

    # naive truncation: drop from end until within budget
    trimmed = list(lines)
    while trimmed and approx_tokens("\n".join(trimmed)) > budget_tokens:
        trimmed.pop()
    return trimmed, True


# ----------------------------
# OPS: template rendering
# ----------------------------

VAR_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")
EACH_RE = re.compile(r"{{#each\s+([a-zA-Z0-9_]+)\s*}}(.*?){{/each}}", re.DOTALL)

def render_template(template: str, variables: Dict[str, Any]) -> str:
    # handle {{#each arr}}...{{this}}...{{/each}}
    def each_sub(m: re.Match) -> str:
        arr_name = m.group(1)
        block = m.group(2)
        arr = variables.get(arr_name, []) or []
        out_parts: List[str] = []
        for item in arr:
            s = block.replace("{{this}}", str(item))
            out_parts.append(s)
        return "".join(out_parts)

    out = EACH_RE.sub(each_sub, template)

    # handle {{var}}
    def var_sub(m: re.Match) -> str:
        key = m.group(1)
        return str(variables.get(key, ""))

    out = VAR_RE.sub(var_sub, out)
    return out


# ----------------------------
# MCP Tools
# ----------------------------

@mcp.tool()
def ops_list() -> Dict[str, Any]:
    """List available OPS packages."""
    pkgs = []
    for p in ALL_PKGS:
        pkgs.append(
            {
                "ref": f"{p.get('id')}@{p.get('version')}",
                "title": p.get("title"),
                "tags": p.get("tags", []),
                "description": p.get("description", ""),
            }
        )
    pkgs.sort(key=lambda x: x["ref"])
    return {"packages": pkgs}


@mcp.tool()
def ops_get(ref: str) -> Dict[str, Any]:
    """Fetch an OPS package metadata and variable schema."""
    pkg = resolve_ops_ref(ref)
    return {
        "ref_resolved": f"{pkg['id']}@{pkg['version']}",
        "id": pkg.get("id"),
        "version": pkg.get("version"),
        "title": pkg.get("title"),
        "description": pkg.get("description"),
        "imports": [i.get("ref") for i in (pkg.get("imports") or [])],
        "variables_schema": pkg.get("variables_schema", {}),
        "policy": pkg.get("policy", {}),
        "templates": list((pkg.get("templates") or {}).keys()),
    }


@mcp.tool()
def ops_render(
    ref: str,
    variables: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Resolve imports, apply policy, optimize context, and render prompt messages.
    options: { token_budget:int, format:"messages"|"text", redact:bool, include_lineage:bool }
    """
    options = options or {}
    fmt = options.get("format", "messages")
    redact = bool(options.get("redact", True))
    include_lineage = bool(options.get("include_lineage", True))

    base_pkg = resolve_ops_ref(ref)
    merged, lineage = resolve_with_imports(base_pkg)

    # policy (merged)
    policy = merged.get("policy", {}) or {}
    redactions = policy.get("redactions", []) or []

    # templates (merged)
    templates = merged.get("templates", {}) or {}
    system_t = templates.get("system", "")
    developer_t = templates.get("developer", "")
    user_t = templates.get("user", "")

    # user can be string or list[str]
    if isinstance(user_t, list):
        user_lines = [render_template(s, variables) for s in user_t]
    else:
        user_lines = [render_template(str(user_t), variables)]

    # optimization budget
    token_budget = options.get("token_budget")
    if token_budget is None:
        token_budget = int((merged.get("optimization", {}) or {}).get("token_budget_default", 900))

    # budget only applied to user block in this demo
    user_lines_opt, compressed = truncate_to_budget(user_lines, budget_tokens=max(64, int(token_budget)))

    system_s = render_template(system_t, variables)
    developer_s = render_template(developer_t, variables)
    user_s = "\n".join(user_lines_opt)

    if redact:
        system_s = apply_redactions(system_s, redactions)
        developer_s = apply_redactions(developer_s, redactions)
        user_s = apply_redactions(user_s, redactions)

    rendered_messages = [
        {"role": "system", "content": system_s},
        {"role": "developer", "content": developer_s},
        {"role": "user", "content": user_s},
    ]

    payload: Dict[str, Any] = {
        "ref_resolved": f"{base_pkg['id']}@{base_pkg['version']}",
        "rendered": {"format": fmt, "messages": rendered_messages} if fmt == "messages" else {"format": "text", "text": "\n\n".join([system_s, developer_s, user_s])},
        "telemetry": {
            "token_budget": token_budget,
            "estimated_tokens": approx_tokens(system_s + developer_s + user_s),
            "compression_applied": compressed,
        },
    }

    if include_lineage:
        payload["lineage"] = {"imports_and_self": lineage, "policy_applied": {"redactions": redactions}}

    return payload


def main() -> None:
    # FastMCP auto-detects transport; for Claude Desktop you typically run via command in config (stdio).
    mcp.run()


if __name__ == "__main__":
    main()
