from __future__ import annotations
import sys, asyncio
from typing import Callable, TypeVar

T = TypeVar("T")

def _set_selector():
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

def _set_proactor():
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

def run_playwright(fn: Callable[[], T]) -> T:
    """On Windows, try Proactor then Selector; elsewhere just run fn()."""
    if not sys.platform.startswith("win"):
        return fn()
    _set_proactor()
    try:
        return fn()
    except NotImplementedError:
        _set_selector()
        return fn()
