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
6. In a terminal, run `hermes config set browser.inactivity_timeout 600` so
   Hermes's cleanup timer matches the plugin's 10-minute Kernel timeout.
7. Restart any running Hermes chat or gateway so it reads the updated settings.

### Hermes CLI

Select Kernel as the browser provider:

```bash
hermes config set browser.cloud_provider kernel
hermes config set browser.inactivity_timeout 600
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
| `KERNEL_PROXY_NAME` | unset | Resolves and attaches a Kernel proxy by name |
| `KERNEL_PROFILE_NAME` | unset | Loads a Kernel profile by name |
| `KERNEL_BASE_URL` | `https://api.onkernel.com` | Overrides the Kernel API URL |

When `KERNEL_PROFILE_NAME` is set, the plugin launches the browser with
`save_changes: true`. Cookies, logins, and other profile changes are saved when
the browser ends.

## Timeouts and cleanup

The plugin always creates Kernel browsers with a 10-minute (`600` second)
inactivity timeout. There is no plugin setting to override it. Kernel enforces
this timeout remotely, so it still removes the browser if the Hermes process
crashes or loses its connection before cleanup runs.

Hermes also has a separate local inactivity timer. It defaults to 120 seconds,
updates whenever Hermes runs a `browser_*` tool for the session, and checks for
stale sessions every 30 seconds. When it finds one, Hermes closes its local
`agent-browser` connection, calls this plugin to delete the Kernel browser, and
removes the session from its in-memory registry. Normal Hermes process exit also
runs this cleanup immediately.

Because the timers are independent, Hermes normally deletes an unused browser
after roughly 2–2.5 minutes, before Kernel's 10-minute timeout. To align the
Hermes timer with the Kernel timeout, run:

```bash
hermes config set browser.inactivity_timeout 600
```

Restart Hermes after changing this setting.

Kernel standby incurs zero browser usage cost only when no CDP, WebDriver, live
view, or computer-controls client is connected. Hermes keeps an `agent-browser`
CDP session for each tracked browser, so increasing Hermes's cleanup timer can
also keep the Kernel browser active longer. The 10-minute setting improves
session continuity, but it doesn't guarantee ten minutes of zero-cost standby.

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
