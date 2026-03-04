"""Compatibility helpers for module vs script execution in training code."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType


def import_local_module(module_name: str) -> ModuleType:
    """Import a sibling module for both package and script execution modes."""
    package = __package__
    if package:
        return import_module(f".{module_name}", package=package)
    return import_module(module_name)


def import_local_symbol(module_name: str, symbol_name: str):
    """Import one symbol from a sibling module in either execution mode."""
    module = import_local_module(module_name)
    return getattr(module, symbol_name)
