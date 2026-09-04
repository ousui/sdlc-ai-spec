#!/usr/bin/env bash

set -euo pipefail

IMP_SHA="207a4a16bea8979faee0474cc43cb642cef1f655"
EXPECTED_BRANCH="internal/imp-v2-evidence-207a4a16"
SOURCE_DIR="/private/tmp"

REPO_ROOT="$(git rev-parse --show-toplevel)"
CURRENT_BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"
REMOTE_IMP_SHA="$(git -C "$REPO_ROOT" rev-parse refs/remotes/origin/impl/imp-v2)"
DST_REL="docs/plugin-development/work-items/sdlc-400-imp/evidence/$IMP_SHA"
DST="$REPO_ROOT/$DST_REL"

if [[ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]]; then
  printf 'error: expected branch %s, got %s\n' "$EXPECTED_BRANCH" "$CURRENT_BRANCH" >&2
  exit 1
fi

if ! git -C "$REPO_ROOT" merge-base --is-ancestor "$IMP_SHA" HEAD; then
  printf 'error: IMP commit %s is not an ancestor of HEAD\n' "$IMP_SHA" >&2
  exit 1
fi

if [[ "$REMOTE_IMP_SHA" != "$IMP_SHA" ]]; then
  printf 'error: origin/impl/imp-v2 is %s, expected %s\n' "$REMOTE_IMP_SHA" "$IMP_SHA" >&2
  exit 1
fi

FILES=(
  imp-v2-full-regression.log
  imp-v2-design-review.md
  imp-v2-real-projects.json
  imp-v2-final-attestation.log
  imp-v2-final-attest-projects.json
  impl-imp-v2-handoff.md
  impl-imp-v2-final-result.json
  impl-imp-v2-evidence.sha256
)

for file in "${FILES[@]}"; do
  if [[ ! -f "$SOURCE_DIR/$file" ]]; then
    printf 'error: missing source file %s/%s\n' "$SOURCE_DIR" "$file" >&2
    exit 1
  fi
done

# Verify the original five-file manifest before copying any evidence.
shasum -a 256 -c "$SOURCE_DIR/impl-imp-v2-evidence.sha256"

mkdir -p "$DST"
for file in "${FILES[@]}"; do
  cp "$SOURCE_DIR/$file" "$DST/$file"
done

# Preserve the original manifest and add a self-contained repository manifest.
(
  cd "$DST"
  shasum -a 256 "${FILES[@]}" > impl-imp-v2-repository.sha256
  shasum -a 256 -c impl-imp-v2-repository.sha256
)

# The repository ignores *.log globally, so evidence logs must be added explicitly.
git -C "$REPO_ROOT" add -f -- "$DST_REL"
git -C "$REPO_ROOT" add -- tools/collect_imp_v2_evidence.sh
git -C "$REPO_ROOT" diff --cached --check

printf 'staged IMP evidence under %s\n' "$DST_REL"
