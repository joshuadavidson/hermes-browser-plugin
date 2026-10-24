from __future__ import annotations

from typing import Any

import pytest
import requests

import provider as provider_module
from provider import KernelBrowserProvider


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: Any = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self.payload = payload
        self.text = text

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self) -> Any:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


@pytest.fixture(autouse=True)
def clear_kernel_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "KERNEL_API_KEY",
        "KERNEL_BASE_URL",
        "KERNEL_STEALTH",
        "KERNEL_HEADLESS",
        "KERNEL_TIMEOUT_SECONDS",
        "KERNEL_PROXY_NAME",
        "KERNEL_PROFILE_NAME",
    ):
        monkeypatch.delenv(name, raising=False)


def test_is_available_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = KernelBrowserProvider()
    assert provider.is_available() is False

    monkeypatch.setenv("KERNEL_API_KEY", "kernel_test_key")
    assert provider.is_available() is True


def test_create_session_uses_default_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KERNEL_API_KEY", "kernel_test_key")
    monkeypatch.setenv("KERNEL_HEADLESS", "true")
    monkeypatch.setenv("KERNEL_TIMEOUT_SECONDS", "30")
    calls: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"url": url, **kwargs})
        return FakeResponse(
            payload={
                "session_id": "browser_123",
                "cdp_ws_url": "wss://example.test/cdp",
            }
        )

    monkeypatch.setattr(provider_module.requests, "post", fake_post)

    result = KernelBrowserProvider().create_session("qa")

    assert calls == [
        {
            "url": "https://api.onkernel.com/browsers",
            "headers": {
                "Authorization": "Bearer kernel_test_key",
                "Content-Type": "application/json",
            },
            "json": {
                "stealth": True,
                "headless": False,
                "name": result["session_name"],
                "timeout_seconds": 600,
            },
            "timeout": 30,
        }
    ]
    session_name = result["session_name"]
    assert isinstance(session_name, str)
    assert session_name.startswith("h_")
    assert len(session_name) == 10
    assert result["bb_session_id"] == "browser_123"
    assert result["cdp_url"] == "wss://example.test/cdp"
    assert result["features"] == {
        "stealth": True,
        "headless": False,
        "proxies": False,
        "profile_persistence": False,
        "live_view": False,
    }
    assert "live_view_url" not in result


def test_create_session_passes_optional_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KERNEL_API_KEY", "kernel_test_key")
    monkeypatch.setenv("KERNEL_BASE_URL", "https://kernel.example.test/")
    monkeypatch.setenv("KERNEL_STEALTH", "off")
    monkeypatch.setenv("KERNEL_PROXY_NAME", "qa-proxy")
    monkeypatch.setenv("KERNEL_PROFILE_NAME", "hermes-qa")
    calls: list[dict[str, Any]] = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"method": "get", "url": url, **kwargs})
        return FakeResponse(payload=[{"id": "proxy_123", "name": "qa-proxy"}])

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"method": "post", "url": url, **kwargs})
        return FakeResponse(
            payload={
                "session_id": "browser_456",
                "cdp_ws_url": "wss://example.test/cdp-456",
                "browser_live_view_url": "https://example.test/live",
            }
        )

    monkeypatch.setattr(provider_module.requests, "get", fake_get)
    monkeypatch.setattr(provider_module.requests, "post", fake_post)

    result = KernelBrowserProvider().create_session("qa")

    assert calls[0]["url"] == "https://kernel.example.test/proxies"
    assert calls[0]["params"] == {"name": "qa-proxy", "limit": 2}
    assert calls[1]["url"] == "https://kernel.example.test/browsers"
    assert calls[1]["json"] == {
        "stealth": False,
        "headless": False,
        "name": result["session_name"],
        "timeout_seconds": 600,
        "proxy_id": "proxy_123",
        "profile": {"name": "hermes-qa", "save_changes": True},
    }
    assert result["live_view_url"] == "https://example.test/live"
    assert result["features"] == {
        "stealth": False,
        "headless": False,
        "proxies": True,
        "profile_persistence": True,
        "live_view": True,
    }


def test_create_session_resolves_proxy_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KERNEL_API_KEY", "kernel_test_key")
    monkeypatch.setenv("KERNEL_PROXY_NAME", "qa-proxy")
    calls: list[dict[str, Any]] = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"method": "get", "url": url, **kwargs})
        return FakeResponse(payload=[{"id": "proxy_123", "name": "qa-proxy"}])

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"method": "post", "url": url, **kwargs})
        return FakeResponse(
            payload={"session_id": "browser_123", "cdp_ws_url": "wss://cdp"}
        )

    monkeypatch.setattr(provider_module.requests, "get", fake_get)
    monkeypatch.setattr(provider_module.requests, "post", fake_post)

    KernelBrowserProvider().create_session("qa")

    assert calls[0]["url"] == "https://api.onkernel.com/proxies"
    assert calls[0]["params"] == {"name": "qa-proxy", "limit": 2}
    assert calls[1]["json"]["proxy_id"] == "proxy_123"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "No Kernel proxy"),
        (
            [
                {"id": "proxy_1", "name": "qa-proxy"},
                {"id": "proxy_2", "name": "qa-proxy"},
            ],
            "Multiple Kernel proxies",
        ),
    ],
)
def test_proxy_name_must_resolve_uniquely(
    monkeypatch: pytest.MonkeyPatch,
    payload: list[dict[str, str]],
    message: str,
) -> None:
    monkeypatch.setenv("KERNEL_API_KEY", "kernel_test_key")
    monkeypatch.setenv("KERNEL_PROXY_NAME", "qa-proxy")
    monkeypatch.setattr(
        provider_module.requests,
        "get",
        lambda *_args, **_kwargs: FakeResponse(payload=payload),
    )

    with pytest.raises(ValueError, match=message):
        KernelBrowserProvider().create_session("qa")


def test_create_session_requires_credentials() -> None:
    with pytest.raises(ValueError, match="KERNEL_API_KEY"):
        KernelBrowserProvider().create_session("qa")


def test_create_session_wraps_connection_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KERNEL_API_KEY", "kernel_test_key")

    def fake_post(_url: str, **_kwargs: Any) -> FakeResponse:
        raise requests.ConnectionError("unreachable")

    monkeypatch.setattr(provider_module.requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="Kernel API connection failed"):
        KernelBrowserProvider().create_session("qa")


def test_create_session_reports_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KERNEL_API_KEY", "kernel_test_key")
    monkeypatch.setattr(
        provider_module.requests,
        "post",
        lambda *_args, **_kwargs: FakeResponse(status_code=403, text="forbidden"),
    )

    with pytest.raises(RuntimeError, match="403 forbidden"):
        KernelBrowserProvider().create_session("qa")


@pytest.mark.parametrize(
    "payload",
    [None, {}, {"session_id": "browser_123"}, ValueError("not json")],
)
def test_create_session_rejects_invalid_payloads(
    monkeypatch: pytest.MonkeyPatch,
    payload: Any,
) -> None:
    monkeypatch.setenv("KERNEL_API_KEY", "kernel_test_key")
    monkeypatch.setattr(
        provider_module.requests,
        "post",
        lambda *_args, **_kwargs: FakeResponse(payload=payload),
    )

    with pytest.raises(RuntimeError, match="invalid browser payload"):
        KernelBrowserProvider().create_session("qa")


@pytest.mark.parametrize("status_code", [200, 201, 204])
def test_close_session_accepts_success_statuses(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    monkeypatch.setenv("KERNEL_API_KEY", "kernel_test_key")
    calls: list[dict[str, Any]] = []

    def fake_delete(url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"url": url, **kwargs})
        return FakeResponse(status_code=status_code)

    monkeypatch.setattr(provider_module.requests, "delete", fake_delete)

    assert KernelBrowserProvider().close_session("browser_123") is True
    assert calls[0]["url"] == "https://api.onkernel.com/browsers/browser_123"
    assert calls[0]["timeout"] == 10


def test_close_session_returns_false_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KERNEL_API_KEY", "kernel_test_key")
    monkeypatch.setattr(
        provider_module.requests,
        "delete",
        lambda *_args, **_kwargs: FakeResponse(status_code=500, text="failed"),
    )

    assert KernelBrowserProvider().close_session("browser_123") is False


def test_close_session_returns_false_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KERNEL_API_KEY", "kernel_test_key")

    def fake_delete(_url: str, **_kwargs: Any) -> FakeResponse:
        raise requests.ConnectionError("unreachable")

    monkeypatch.setattr(provider_module.requests, "delete", fake_delete)

    assert KernelBrowserProvider().close_session("browser_123") is False


def test_emergency_cleanup_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KERNEL_API_KEY", "kernel_test_key")

    def fake_delete(_url: str, **_kwargs: Any) -> FakeResponse:
        raise requests.ConnectionError("unreachable")

    monkeypatch.setattr(provider_module.requests, "delete", fake_delete)

    KernelBrowserProvider().emergency_cleanup("browser_123")


def test_setup_schema_exposes_api_key_and_install_hook() -> None:
    schema = KernelBrowserProvider().get_setup_schema()

    assert schema["name"] == "Kernel"
    assert schema["env_vars"] == [
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
    ]
    assert schema["post_setup"] == "agent_browser"


def test_setup_schema_hides_post_setup_when_agent_browser_is_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(provider_module, "_agent_browser_installed", lambda: True)

    schema = KernelBrowserProvider().get_setup_schema()

    assert "post_setup" not in schema
