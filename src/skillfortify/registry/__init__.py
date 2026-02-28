"""Marketplace and registry scanning for agent skill supply chains.

Provides abstract and concrete scanners for remote agent skill registries
(MCP, PyPI, npm) enabling supply chain analysis without local installation.

Public API::

    from skillfortify.registry import RegistryScanner, RegistryStats, RegistryEntry
    from skillfortify.registry.mcp_registry import MCPRegistryScanner
    from skillfortify.registry.pypi_scanner import PyPIScanner
    from skillfortify.registry.npm_scanner import NpmScanner
"""

from __future__ import annotations

from skillfortify.registry.base import RegistryEntry, RegistryScanner, RegistryStats

__all__ = [
    "RegistryEntry",
    "RegistryScanner",
    "RegistryStats",
]
