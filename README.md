# Kernel browser provider for Hermes Agent

Use [Kernel](https://kernel.sh) cloud browsers with the `browser_*` tools in
[Hermes Agent](https://github.com/NousResearch/hermes-agent). The plugin creates
a Kernel browser, gives Hermes its CDP endpoint, and deletes the browser when the
Hermes session ends or becomes inactive.

## Requirements

- A current Hermes Agent installation with the
  [`BrowserProvider`](https://github.com/NousResearch/hermes-agent/blob/main/agent/browser_provider.py)
  plugin API
- A [Kernel](https://kernel.sh) API key
- Node.js 20 or newer for Hermes's `agent-browser` dependency

## Install

```bash
hermes plugins install kernel/hermes-browser-plugin --enable
```

Some Hermes versions prompt for `KERNEL_API_KEY` during installation and some
don't. Running `hermes config set browser.cloud_provider kernel` only selects
the provider; it doesn't set the API key.

### Hermes Desktop

1. Open **Capabilities → Tools → Browser Automation**.
2. Select **Kernel**.
3. If `agent_browser` hasn't been installed, click **Run setup** and wait for the
   one-time installation to finish.
4. Open the three-dot menu next to `KERNEL_API_KEY` and enter an API key from the
   [Kernel Dashboard](https://dashboard.onkernel.com/api-keys).
5. Optionally set `KERNEL_PROXY_NAME` and `KERNEL_PROFILE_NAME` from their
   three-dot menus.
6. Restart any running Hermes chat or gateway so it reads the updated settings.

Hermes Desktop currently renders every browser-provider setting as a password
field, even when the plugin marks it as non-secret. `KERNEL_PROXY_NAME` and
`KERNEL_PROFILE_NAME` are ordinary configuration values; this display behavior
comes from Hermes Desktop.

### Hermes CLI

Select Kernel as the browser provider:

```bash
hermes config set browser.cloud_provider kernel
```

If installation didn't prompt for the API key, add `KERNEL_API_KEY` to the
active Hermes profile's `.env` file. `hermes config env-path` prints that file's
location. Install `agent_browser` once if needed:

```bash
hermes tools post-setup agent_browser
```

Verify the plugin and configuration:

```bash
hermes plugins list
hermes config show
hermes doctor
```

## Update

Pull the latest plugin version with:

```bash
hermes plugins update browser-kernel
```

Restart Hermes Desktop, a running chat, or the gateway after updating.

## Configuration

Kernel settings are read from the active Hermes profile's `.env` file.

| Variable | Default | Purpose |
| --- | --- | --- |
| `KERNEL_API_KEY` | required | Authenticates requests to Kernel |
| `KERNEL_STEALTH` | `true` | Enables Kernel's stealth browser mode |
| `KERNEL_HEADLESS` | `true` | Set to `false` for a visible browser and live view |
| `KERNEL_TIMEOUT_SECONDS` | Kernel default | Browser inactivity timeout in seconds |
| `KERNEL_PROXY_NAME` | unset | Resolves and attaches a Kernel proxy by name |
| `KERNEL_PROXY_ID` | unset | Attaches a proxy by ID and takes precedence over `KERNEL_PROXY_NAME` |
| `KERNEL_PROFILE_NAME` | unset | Loads a Kernel profile by name |
| `KERNEL_PROFILE` | unset | Legacy alias for `KERNEL_PROFILE_NAME` |
| `KERNEL_BASE_URL` | `https://api.onkernel.com` | Overrides the Kernel API URL |

When `KERNEL_PROFILE_NAME` or `KERNEL_PROFILE` is set, the plugin launches the
browser with `save_changes: true`. Cookies, logins, and other profile changes are
saved when the browser ends.

Proxy names aren't required to be unique in Kernel. If more than one proxy has
the configured name, the plugin stops with an ambiguity error; set
`KERNEL_PROXY_ID` to select one explicitly.

Boolean variables accept `0`, `false`, `no`, and `off` as false values.

## QA smoke test

Run Hermes interactively so the browser remains available while you inspect it
in the Kernel dashboard:

```bash
hermes chat --verbose --toolsets browser
```

Then ask:

> Use `browser_navigate`, not web search, to open https://example.com. Call
> `browser_snapshot`, report the exact title and `stealth_features`, and tell me
> whether any cloud fallback warning occurred.

A passing run has all of these properties:

1. The title is `Example Domain`.
2. `stealth_features` includes `stealth`.
3. There is no `fallback_warning`.
4. A matching browser appears in the Kernel dashboard.
5. Exiting Hermes or waiting for inactivity cleanup removes the browser.

Hermes can fall back to local Chromium when a cloud provider fails. A successful
navigation alone does not prove Kernel was used; check both the tool result and
the Kernel dashboard.

## Development

Install [uv](https://docs.astral.sh/uv/), then run:

```bash
uv run pytest -q
uv run ruff check .
```

To check registration against a Hermes source checkout:

```bash
scripts/check-hermes-integration.sh /path/to/hermes-agent
```

The integration check installs a temporary copy of the plugin, enables it, and
verifies that Hermes registers `kernel` alongside its bundled browser providers.
It does not create a live Kernel browser.

## Uninstall

```bash
hermes plugins remove browser-kernel
```

If Kernel was the active browser provider, select another provider with
`hermes setup tools` or set local mode:

```bash
hermes config set browser.cloud_provider local
```

## License

MIT
