def register(ctx) -> None:
    from .provider import KernelBrowserProvider

    ctx.register_browser_provider(KernelBrowserProvider())


__all__ = ["register"]
