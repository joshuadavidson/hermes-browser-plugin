# Kernel browser provider installed

Set Kernel as Hermes's browser provider:

```bash
hermes config set browser.cloud_provider kernel
```

This command only selects the provider; it doesn't set `KERNEL_API_KEY`.

In Hermes Desktop, open **Capabilities → Tools → Browser Automation**, select
**Kernel**, run the one-time `agent_browser` setup, then use the three-dot menus
to set `KERNEL_API_KEY` and any optional defaults.

For CLI-only setups, add `KERNEL_API_KEY` to the active profile's `.env` file
(`hermes config env-path`) and run `hermes tools post-setup agent_browser` once.
