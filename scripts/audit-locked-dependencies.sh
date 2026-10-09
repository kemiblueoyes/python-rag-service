#!/usr/bin/env bash
# Audit the locked Python and npm dependency sets.
# The checks read uv.lock and package-lock.json. They do not resolve newer
# package versions, and they fail when an advisory is confirmed or a scan
# cannot be completed.

set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

command -v uv >/dev/null
command -v npm >/dev/null
command -v python3 >/dev/null

uv sync --locked --group audit

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

status=0

normalize_requirements() {
  python3 - "$1" "$2" <<'PY'
import sys
from pathlib import Path

source, dest = sys.argv[1:]
lines = []
for raw in Path(source).read_text().splitlines():
    line = raw.split(";", 1)[0].strip()
    if not line or line.startswith("#"):
        continue
    if "==" not in line:
        raise SystemExit(f"Unlocked requirement in audit input: {line}")
    lines.append(line)
if not lines:
    raise SystemExit(f"Locked requirements export was empty: {source}")
Path(dest).write_text("\n".join(lines) + "\n")
PY
}

audit_python_scope() {
  local name="$1"
  shift
  local exported="$tmpdir/${name}.txt"
  local normalized="$tmpdir/${name}-audit.txt"

  echo "Auditing locked Python ${name} dependencies"
  uv export \
    --frozen \
    --no-emit-project \
    --no-hashes \
    --no-annotate \
    --no-header \
    "$@" \
    -o "$exported" \
    >/dev/null
  normalize_requirements "$exported" "$normalized"
  if ! uv run --frozen --group audit pip-audit \
    --requirement "$normalized" \
    --no-deps \
    --disable-pip \
    --strict \
    --progress-spinner off
  then
    status=1
  fi
}

audit_python_scope runtime --no-dev
audit_python_scope development --only-dev
audit_python_scope "audit-tool" --only-group audit --no-dev

echo "Auditing locked npm packages, including development dependencies"
if ! npm audit --package-lock-only
then
  status=1
fi

exit "$status"
