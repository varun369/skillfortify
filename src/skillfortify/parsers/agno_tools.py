"""Parser for Agno (formerly Phidata) agent and toolkit definitions."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser

_URL_RE = re.compile(r"https?://[^\s\"'`)\]>]+")
_ENV_RE = re.compile(
    r"(?:\$\{?([A-Z][A-Z0-9_]{1,})\}?"
    r"|os\.environ\[[\"']([A-Z][A-Z0-9_]{1,})[\"']\]"
    r"|os\.getenv\([\"']([A-Z][A-Z0-9_]{1,})[\"']\))",
    re.MULTILINE,
)
_SHELL_RE = re.compile(
    r"(?:subprocess\.(?:run|call|check_call|check_output|Popen)"
    r"|os\.(?:system|popen))\s*\(\s*[\"']([^\"']+)[\"']",
)
_IMPORT_MARKERS = ("from agno", "import agno", "from phi", "import phi")
_TOOL_DIRS = ("tools", "agents", "agno_agents", "phi_agents")
_BUILTIN_IMPORT_RE = re.compile(r"from\s+(?:agno|phi)\.tools\.\w+\s+import\s+(.+)")
FORMAT_NAME = "agno"


def _extract_urls(text: str) -> list[str]:
    return _URL_RE.findall(text)

def _extract_env_vars(text: str) -> list[str]:
    found: set[str] = set()
    for m in _ENV_RE.finditer(text):
        for g in m.groups():
            if g:
                found.add(g)
    return sorted(found)

def _extract_shell_commands(text: str) -> list[str]:
    return _SHELL_RE.findall(text)


def _extract_imports(text: str) -> list[str]:
    imports: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        for line in text.splitlines():
            s = line.strip()
            if s.startswith(("import ", "from ")):
                p = s.split()
                if len(p) >= 2:
                    imports.append(p[1].split(".")[0])
        return sorted(set(imports))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module.split(".")[0])
    return sorted(set(imports))

def _has_agno_imports(text: str) -> bool:
    return any(m in text for m in _IMPORT_MARKERS)


def _build_skill(
    name: str, desc: str, body: str, path: Path, source: str,
    caps: list[str] | None = None,
) -> ParsedSkill:
    return ParsedSkill(
        name=name, version="unknown", source_path=path, format=FORMAT_NAME,
        description=desc, declared_capabilities=caps or [],
        code_blocks=[body] if body else [], urls=_extract_urls(body),
        env_vars_referenced=_extract_env_vars(source),
        shell_commands=_extract_shell_commands(body),
        dependencies=_extract_imports(source), raw_content=source,
    )

def _is_agent_call(call: ast.Call) -> bool:
    f = call.func
    return (isinstance(f, ast.Name) and f.id == "Agent") or (
        isinstance(f, ast.Attribute) and f.attr == "Agent")

def _kwarg_str(call: ast.Call, key: str) -> str:
    for kw in call.keywords:
        if kw.arg == key and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return ""

def _kwarg_list_strings(call: ast.Call, key: str) -> list[str]:
    for kw in call.keywords:
        if kw.arg == key and isinstance(kw.value, ast.List):
            return [
                str(e.value) for e in kw.value.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)
            ]
    return []

def _list_element_names(lst: ast.List) -> list[str]:
    names: list[str] = []
    for elt in lst.elts:
        if isinstance(elt, ast.Name):
            names.append(elt.id)
        elif isinstance(elt, ast.Attribute):
            names.append(elt.attr)
        elif isinstance(elt, ast.Call):
            f = elt.func
            if isinstance(f, ast.Name):
                names.append(f.id)
            elif isinstance(f, ast.Attribute):
                names.append(f.attr)
    return names

def _agent_tool_names(call: ast.Call) -> list[str]:
    for kw in call.keywords:
        if kw.arg == "tools" and isinstance(kw.value, ast.List):
            return _list_element_names(kw.value)
    return []

def _builtin_tool_imports(source: str) -> list[str]:
    tools: list[str] = []
    for m in _BUILTIN_IMPORT_RE.finditer(source):
        for name in m.group(1).split(","):
            n = name.strip().split(" as ")[0].strip()
            if n:
                tools.append(n)
    return tools

def _tools_to_caps(tool_names: list[str], builtins: list[str]) -> list[str]:
    bs = {t.lower() for t in builtins}
    return [
        f"builtin:{t}" if t in builtins or t.lower() in bs else f"tool:{t}"
        for t in tool_names
    ]

def _parse_agent_call(call: ast.Call, source: str, fpath: Path) -> ParsedSkill:
    name = _kwarg_str(call, "name") or "unnamed_agent"
    instr_list = _kwarg_list_strings(call, "instructions")
    instr_str = _kwarg_str(call, "instructions")
    desc = "; ".join(instr_list) if instr_list else instr_str
    if not desc:
        model = _kwarg_str(call, "model")
        desc = f"Agno agent (model={model})" if model else ""
    tools = _agent_tool_names(call)
    caps = _tools_to_caps(tools, _builtin_tool_imports(source))
    body = ast.get_source_segment(source, call) or ""
    return _build_skill(name, desc, body, fpath, source, caps)


def _parse_toolkit_class(node: ast.ClassDef, source: str, fpath: Path) -> ParsedSkill | None:
    is_tk = any(
        (isinstance(b, ast.Name) and b.id == "Toolkit")
        or (isinstance(b, ast.Attribute) and b.attr == "Toolkit")
        for b in node.bases)
    if not is_tk:
        return None
    names: list[str] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        f = child.func
        if not (isinstance(f, ast.Attribute) and f.attr == "register"):
            continue
        for arg in child.args:
            if not isinstance(arg, ast.Call):
                continue
            af = arg.func
            if (isinstance(af, ast.Name) and af.id == "Function") or (
                isinstance(af, ast.Attribute) and af.attr == "Function"):
                for kw in arg.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                        names.append(str(kw.value.value))
    caps = [f"function:{fn}" for fn in names]
    body = ast.get_source_segment(source, node) or ""
    return _build_skill(node.name, "", body, fpath, source, caps)

def _parse_agno_file(fpath: Path) -> list[ParsedSkill]:
    try:
        source = fpath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _regex_fallback(source, fpath)
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_agent_call(node):
            results.append(_parse_agent_call(node, source, fpath))
        elif isinstance(node, ast.ClassDef):
            sk = _parse_toolkit_class(node, source, fpath)
            if sk is not None:
                results.append(sk)
    return results

def _regex_fallback(source: str, fpath: Path) -> list[ParsedSkill]:
    results: list[ParsedSkill] = []
    for m in re.finditer(r'Agent\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']', source, re.DOTALL):
        results.append(_build_skill(m.group(1), "", source, fpath, source))
    for m in re.finditer(r"class\s+(\w+)\s*\(\s*Toolkit\s*\)", source):
        results.append(_build_skill(m.group(1), "", source, fpath, source))
    return results


class AgnoParser(SkillParser):
    """Parser for Agno (formerly Phidata) agent and toolkit definitions."""

    def can_parse(self, path: Path) -> bool:
        return bool(self._find_tool_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        results: list[ParsedSkill] = []
        for py_file in self._find_tool_files(path):
            results.extend(_parse_agno_file(py_file))
        return results

    def _find_tool_files(self, path: Path) -> list[Path]:
        candidates: list[Path] = []
        search_dirs = [path]
        for dn in _TOOL_DIRS:
            sub = path / dn
            if sub.is_dir():
                search_dirs.append(sub)
        for sd in search_dirs:
            for pf in sorted(sd.glob("*.py")):
                try:
                    head = pf.read_text(encoding="utf-8")[:4096]
                except (OSError, UnicodeDecodeError):
                    continue
                if _has_agno_imports(head):
                    candidates.append(pf)
        return candidates
