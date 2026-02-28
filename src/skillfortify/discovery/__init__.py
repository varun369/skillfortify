"""System auto-discovery for AI IDE and tool configurations.

Provides automated scanning of the user's home directory to find all
installed AI development tools (Claude Code, Cursor, VS Code, Windsurf,
etc.) and their associated MCP configs and skill directories.

Public API::

    from skillfortify.discovery import SystemScanner, SystemScanResult

    scanner = SystemScanner()
    result = scanner.scan_system()
    for ide in result.ides_found:
        print(f"{ide.profile.name}: {len(ide.mcp_configs)} MCP configs")
"""

from __future__ import annotations

from skillfortify.discovery.ide_registry import IDE_PROFILES, IDEProfile
from skillfortify.discovery.models import DiscoveredIDE, SystemScanResult
from skillfortify.discovery.system_scanner import SystemScanner

__all__ = [
    "DiscoveredIDE",
    "IDE_PROFILES",
    "IDEProfile",
    "SystemScanResult",
    "SystemScanner",
]
