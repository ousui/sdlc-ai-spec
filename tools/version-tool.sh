#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'USAGE'
Usage:
  tools/version-tool.sh sdlc.N
  tools/version-tool.sh X.Y.Z-sdlc.N
  tools/version-tool.sh --check

Examples:
  tools/version-tool.sh sdlc.3
  # Resolves the current locked upstream version and applies local revision 3.
USAGE
}

if [[ $# -ne 1 ]]; then
  usage >&2
  exit 2
fi

if [[ "$1" == "--check" ]]; then
  python3 - <<'PY'
import json, pathlib, re, sys
root = pathlib.Path('.')
lock = json.loads((root/'upstream.lock.json').read_text())
meta = json.loads((root/'plugin-metadata.json').read_text())
version = meta['version']
pat = re.compile(re.escape(str(lock['version'])) + r'-sdlc\.([1-9][0-9]*)\Z')
if not pat.fullmatch(version):
    raise SystemExit(f'ERROR: product version {version!r} does not align with upstream {lock["version"]!r}')
changelog = (root/'CHANGELOG.md').read_text()
releases = re.findall(r'^## ([0-9]+\.[0-9]+\.[0-9]+-sdlc\.[1-9][0-9]*) — ', changelog, re.M)
if not releases or releases[0] != version:
    raise SystemExit(f'ERROR: first released CHANGELOG version must be {version!r}')
checks = [
    ('dist/BUILD.json', 'product_version'),
    ('dist/UPSTREAM.json', 'port_version'),
]
for name, key in checks:
    data = json.loads((root/name).read_text())
    if data.get(key) != version:
        raise SystemExit(f'ERROR: {name}:{key} is {data.get(key)!r}, expected {version!r}')
for name in ('.claude-plugin/marketplace.json', '.cursor-plugin/marketplace.json'):
    data = json.loads((root/name).read_text())
    if data.get('metadata', {}).get('version') != version or data['plugins'][0].get('version') != version:
        raise SystemExit(f'ERROR: stale generated version in {name}')
print(version)
PY
  exit 0
fi

ARG="$1"
UPSTREAM_VERSION="$(python3 - <<'PY'
import json
print(json.load(open('upstream.lock.json'))['version'])
PY
)"

if [[ "$ARG" =~ ^sdlc\.([1-9][0-9]*)$ ]]; then
  TARGET="${UPSTREAM_VERSION}-${ARG}"
elif [[ "$ARG" =~ ^([0-9]+\.[0-9]+\.[0-9]+)-sdlc\.([1-9][0-9]*)$ ]]; then
  if [[ "${BASH_REMATCH[1]}" != "$UPSTREAM_VERSION" ]]; then
    echo "ERROR: target upstream ${BASH_REMATCH[1]} does not match upstream.lock.json version $UPSTREAM_VERSION" >&2
    exit 2
  fi
  TARGET="$ARG"
else
  usage >&2
  exit 2
fi

BACKUP="$(mktemp -d "${TMPDIR:-/tmp}/sdlc-version.XXXXXX")"
cleanup() { rm -rf "$BACKUP"; }
rollback() {
  set +e
  cp -a "$BACKUP/plugin-metadata.json" plugin-metadata.json
  cp -a "$BACKUP/CHANGELOG.md" CHANGELOG.md
  rm -rf dist
  cp -a "$BACKUP/dist" dist
  cp -a "$BACKUP/marketplace.agents.json" .agents/plugins/marketplace.json
  cp -a "$BACKUP/marketplace.claude.json" .claude-plugin/marketplace.json
  cp -a "$BACKUP/marketplace.cursor.json" .cursor-plugin/marketplace.json
  echo "ERROR: version update failed; touched version/build files were restored" >&2
  cleanup
}
trap rollback ERR INT TERM

cp -a plugin-metadata.json "$BACKUP/plugin-metadata.json"
cp -a CHANGELOG.md "$BACKUP/CHANGELOG.md"
cp -a dist "$BACKUP/dist"
cp -a .agents/plugins/marketplace.json "$BACKUP/marketplace.agents.json"
cp -a .claude-plugin/marketplace.json "$BACKUP/marketplace.claude.json"
cp -a .cursor-plugin/marketplace.json "$BACKUP/marketplace.cursor.json"

TARGET="$TARGET" python3 - <<'PY'
from datetime import datetime, timezone, timedelta
import json, os, pathlib, re
root = pathlib.Path('.')
target = os.environ['TARGET']
lock = json.loads((root/'upstream.lock.json').read_text())
meta_path = root/'plugin-metadata.json'
meta = json.loads(meta_path.read_text())
current = meta['version']
pat = re.compile(re.escape(str(lock['version'])) + r'-sdlc\.([1-9][0-9]*)\Z')
m_cur, m_new = pat.fullmatch(current), pat.fullmatch(target)
if not m_cur:
    raise SystemExit(f'ERROR: current product version {current!r} does not align with upstream {lock["version"]!r}')
if not m_new:
    raise SystemExit(f'ERROR: target product version {target!r} does not align with upstream {lock["version"]!r}')
cur_rev, new_rev = int(m_cur[1]), int(m_new[1])
changelog_path = root/'CHANGELOG.md'
changelog = changelog_path.read_text()
releases = re.findall(r'^## ([0-9]+\.[0-9]+\.[0-9]+-sdlc\.[1-9][0-9]*) — ', changelog, re.M)
if not releases or releases[0] != current:
    raise SystemExit(f'ERROR: first released CHANGELOG version must match current product version {current!r}')
if target == current:
    print(f'Version already set: {target}')
else:
    if new_rev <= cur_rev:
        raise SystemExit(f'ERROR: local revision must increase ({cur_rev} -> {new_rev})')
    if re.search(rf'^## {re.escape(target)} — ', changelog, re.M):
        raise SystemExit(f'ERROR: CHANGELOG already contains release {target}')
    match = re.search(r'(?ms)^## Unreleased\n(?P<body>.*?)(?=^## )', changelog)
    if not match:
        raise SystemExit('ERROR: CHANGELOG must contain an Unreleased section before released versions')
    body = match.group('body').strip()
    if not body or not re.search(r'(?m)^-\s+\S', body):
        raise SystemExit('ERROR: CHANGELOG Unreleased section has no release notes')
    now = datetime.now(timezone(timedelta(hours=8)))
    release_time = os.environ.get('SDLC_RELEASE_TIME') or now.strftime('%Y-%m-%d %H:%M:%S +08:00')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+08:00', release_time):
        raise SystemExit('ERROR: SDLC_RELEASE_TIME must use YYYY-MM-DD HH:MM:SS +08:00')
    release_date = release_time[:10]
    replacement = f'## Unreleased\n\n## {target} — {release_date}\n\n最后发版时间：{release_time}\n\n{body}\n\n'
    changelog = changelog[:match.start()] + replacement + changelog[match.end():]
    meta['version'] = target
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    changelog_path.write_text(changelog)
    print(f'Set product version: {current} -> {target}')
PY

uv sync --locked
uv run --locked python -B tools/build.py --marketplaces
uv run --locked python -B -m unittest tests.test_versioning tests.test_repository tests.test_distribution -v
./tools/version-tool.sh --check
git diff --check

trap - ERR INT TERM
cleanup
printf 'Version ready: %s\n' "$TARGET"
printf 'Run full verification before release: uv run --locked python -B -m unittest discover -s tests -v\n'
