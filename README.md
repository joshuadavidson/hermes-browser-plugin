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

The installer prompts for `KERNEL_API_KEY` and saves it to the active Hermes
profile's `.env` file. Then select Kernel as the browser provider:

```bash
hermes config set browser.cloud_provider kernel
```

Alternatively, run `hermes setup tools` and choose **Browser Automation →
Kernel**. Restart a running Hermes CLI or gateway after changing the provider.

Verify the plugin and configuration:

```bash
hermes plugins list
hermes config show
hermes doctor
```

## Configuration

Kernel settings are read from the active Hermes profile's `.env` file.

| Variable | Default | Purpose |
| --- | --- | --- |
| `KERNEL_API_KEY` | required | Authenticates requests to Kernel |
| `KERNEL_STEALTH` | `true` | Enables Kernel's stealth browser mode |
| `KERNEL_HEADLESS` | `true` | Set to `false` for a visible browser and live view |
| `KERNEL_TIMEOUT_SECONDS` | Kernel default | Browser inactivity timeout in seconds |
| `KERNEL_PROXY_ID` | unset | Attaches an existing Kernel proxy by ID |
| `KERNEL_PROFILE` | unset | Loads this profile and saves changes when the browser closes |
| `KERNEL_BASE_URL` | `https://api.onkernel.com` | Overrides the Kernel API URL |

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
