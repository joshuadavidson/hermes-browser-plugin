from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from agent.browser_provider import BrowserProvider as BrowserProvider
except ImportError:
    agent_module = types.ModuleType("agent")
    browser_provider_module = types.ModuleType("agent.browser_provider")

    class BrowserProvider:
        pass

    browser_provider_module.BrowserProvider = BrowserProvider
    agent_module.browser_provider = browser_provider_module
    sys.modules["agent"] = agent_module
    sys.modules["agent.browser_provider"] = browser_provider_module
