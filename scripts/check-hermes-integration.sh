#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 /path/to/hermes-agent" >&2
  exit 2
fi

plugin_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
hermes_dir="$(cd "$1" && pwd)"

if [[ ! -f "$hermes_dir/agent/browser_provider.py" ]]; then
  echo "not a Hermes Agent checkout: $hermes_dir" >&2
  exit 2
fi

hermes_home="$(mktemp -d)"
trap 'rm -rf "$hermes_home"' EXIT
mkdir -p "$hermes_home/plugins/browser-kernel"
cp \
  "$plugin_dir/__init__.py" \
  "$plugin_dir/plugin.yaml" \
  "$plugin_dir/provider.py" \
  "$hermes_home/plugins/browser-kernel/"

cat >"$hermes_home/config.yaml" <<'YAML'
plugins:
  enabled:
    - browser-kernel
browser:
  cloud_provider: kernel
YAML

cd "$hermes_dir"
HERMES_HOME="$hermes_home" KERNEL_API_KEY="integration-test-key" \
  uv run --extra dev python - <<'PY'
from agent.browser_registry import get_provider, list_providers
from hermes_cli.plugins import PluginManager

manager = PluginManager()
manager.discover_and_load()
loaded = manager._plugins["browser-kernel"]
provider = get_provider("kernel")

assert loaded.enabled, loaded.error
assert provider is not None
assert provider.get_setup_schema()["name"] == "Kernel"
assert "kernel" in {item.name for item in list_providers()}
print("Kernel browser provider registered successfully")
PY
