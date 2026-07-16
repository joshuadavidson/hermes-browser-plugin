from __future__ import annotations

import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

import requests
from agent import browser_provider as hermes_browser_provider
from agent.browser_provider import BrowserProvider

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.onkernel.com"
_FALSE_VALUES = {"0", "false", "no", "off"}


def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in _FALSE_VALUES


def _optional_env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def _agent_browser_installed() -> bool:
    executable = shutil.which("agent-browser")
    if executable and Path(executable).exists():
        return True

    module_path = getattr(hermes_browser_provider, "__file__", None)
    if not module_path:
        return False
    project_root = Path(module_path).resolve().parent.parent
    return (project_root / "node_modules" / "agent-browser").is_dir()


class KernelBrowserProvider(BrowserProvider):
    @property
    def name(self) -> str:
        return "kernel"

    @property
    def display_name(self) -> str:
        return "Kernel"

    def is_available(self) -> bool:
        return bool(os.environ.get("KERNEL_API_KEY"))

    def _get_config(self) -> dict[str, str]:
        api_key = os.environ.get("KERNEL_API_KEY")
        if not api_key:
            raise ValueError(
                "Kernel requires KERNEL_API_KEY. Get an API key at "
                "https://dashboard.onkernel.com/api-keys"
            )
        return {
            "api_key": api_key,
            "base_url": os.environ.get("KERNEL_BASE_URL", _DEFAULT_BASE_URL).rstrip(
                "/"
            ),
        }

    @staticmethod
    def _headers(api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _resolve_proxy_id(self, config: dict[str, str]) -> str | None:
        proxy_id = _optional_env("KERNEL_PROXY_ID")
        if proxy_id:
            return proxy_id

        proxy_name = _optional_env("KERNEL_PROXY_NAME")
        if not proxy_name:
            return None

        try:
            response = requests.get(
                f"{config['base_url']}/proxies",
                headers=self._headers(config["api_key"]),
                params={"name": proxy_name, "limit": 2},
                timeout=10,
            )
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Failed to resolve Kernel proxy {proxy_name!r}: {exc}"
            ) from exc

        if not response.ok:
            raise RuntimeError(
                f"Failed to resolve Kernel proxy {proxy_name!r}: "
                f"{response.status_code} {response.text[:500]}"
            )

        try:
            proxies: list[dict[str, Any]] = response.json()
            proxy_ids = [proxy["id"] for proxy in proxies]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Kernel API returned an invalid proxy list") from exc

        if not proxy_ids:
            raise ValueError(f"No Kernel proxy named {proxy_name!r} was found")
        if len(proxy_ids) > 1:
            raise ValueError(
                f"Multiple Kernel proxies are named {proxy_name!r}; "
                "set KERNEL_PROXY_ID instead"
            )
        return str(proxy_ids[0])

    def create_session(self, task_id: str) -> dict[str, object]:
        config = self._get_config()
        stealth = _env_flag("KERNEL_STEALTH", True)
        headless = _env_flag("KERNEL_HEADLESS", True)
        proxy_id = self._resolve_proxy_id(config)
        profile_name = _optional_env("KERNEL_PROFILE_NAME") or _optional_env(
            "KERNEL_PROFILE"
        )
        session_name = f"hermes_{task_id}_{uuid.uuid4().hex[:8]}"

        body: dict[str, object] = {
            "stealth": stealth,
            "headless": headless,
            "name": session_name,
        }

        timeout_seconds = os.environ.get("KERNEL_TIMEOUT_SECONDS")
        if timeout_seconds:
            try:
                body["timeout_seconds"] = int(timeout_seconds)
            except ValueError:
                logger.warning(
                    "Ignoring invalid KERNEL_TIMEOUT_SECONDS value: %s",
                    timeout_seconds,
                )

        if proxy_id:
            body["proxy_id"] = proxy_id
        if profile_name:
            body["profile"] = {"name": profile_name, "save_changes": True}

        try:
            response = requests.post(
                f"{config['base_url']}/browsers",
                headers=self._headers(config["api_key"]),
                json=body,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Kernel API connection failed: {exc}") from exc

        if not response.ok:
            raise RuntimeError(
                "Failed to create Kernel browser: "
                f"{response.status_code} {response.text[:500]}"
            )

        try:
            data: dict[str, Any] = response.json()
            session_id = data["session_id"]
            cdp_url = data["cdp_ws_url"]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(
                "Kernel API returned an invalid browser payload"
            ) from exc

        live_view_url = data.get("browser_live_view_url")
        features: dict[str, object] = {
            "stealth": stealth,
            "headless": headless,
            "custom_timeout": "timeout_seconds" in body,
            "proxies": bool(proxy_id),
            "profile_persistence": bool(profile_name),
            "live_view": bool(live_view_url),
        }
        result: dict[str, object] = {
            "session_name": session_name,
            "bb_session_id": session_id,
            "cdp_url": cdp_url,
            "features": features,
        }
        if live_view_url:
            result["live_view_url"] = live_view_url
        return result

    def close_session(self, session_id: str) -> bool:
        try:
            config = self._get_config()
        except ValueError:
            logger.warning(
                "Cannot close Kernel browser %s without credentials", session_id
            )
            return False

        try:
            response = requests.delete(
                f"{config['base_url']}/browsers/{session_id}",
                headers=self._headers(config["api_key"]),
                timeout=10,
            )
        except requests.RequestException as exc:
            logger.warning("Failed to close Kernel browser %s: %s", session_id, exc)
            return False

        if response.status_code in {200, 201, 204}:
            return True

        logger.warning(
            "Failed to close Kernel browser %s: HTTP %s - %s",
            session_id,
            response.status_code,
            response.text[:200],
        )
        return False

    def emergency_cleanup(self, session_id: str) -> None:
        try:
            config = self._get_config()
            requests.delete(
                f"{config['base_url']}/browsers/{session_id}",
                headers=self._headers(config["api_key"]),
                timeout=5,
            )
        except Exception as exc:
            logger.debug("Emergency cleanup failed for %s: %s", session_id, exc)

    def get_setup_schema(self) -> dict[str, Any]:
        schema: dict[str, Any] = {
            "name": "Kernel",
            "badge": "paid",
            "tag": "Cloud browser with stealth, proxies, profiles, and live view",
            "env_vars": [
                {
                    "key": "KERNEL_API_KEY",
                    "prompt": "Kernel API key",
                    "url": "https://dashboard.onkernel.com/api-keys",
                    "secret": True,
                },
                {
                    "key": "KERNEL_PROXY_NAME",
                    "prompt": "Default Kernel proxy name (optional)",
                    "required": False,
                    "secret": False,
                },
                {
                    "key": "KERNEL_PROFILE_NAME",
                    "prompt": "Default Kernel profile name (optional)",
                    "required": False,
                    "secret": False,
                },
            ],
        }
        if not _agent_browser_installed():
            schema["post_setup"] = "agent_browser"
        return schema
