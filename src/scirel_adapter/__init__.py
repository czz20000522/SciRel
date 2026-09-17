"""Framework-neutral adapter cores for SciRel consumers."""

from .mcp import ThinMcpAdapter, ThinMcpAdapterError


__all__ = ["ThinMcpAdapter", "ThinMcpAdapterError"]
