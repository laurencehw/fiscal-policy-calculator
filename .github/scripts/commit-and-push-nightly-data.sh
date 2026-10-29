#!/usr/bin/env bash
# Commit the nightly bill-tracker artifacts and push them to main even if
# main moved while this job was generating them.
#
# Conflict strategy: do not merge. bills.db is a binary SQLite file and
# site_data/ is generated output; a textual rebase can corrupt the database
# or mix two exports. Snapshot this run's artifacts, reset to the latest
# origin/main, restore the snapshot, and commit. This run's generated files
# always win over concurrent edits to those paths. A rejected push is retried
# a few times with backoff; if it still fails the job fails loudly (never
# force-pushes).
set -euo pipefail

REMOTE="${NIGHTLY_REMOTE:-origin}"
BRANCH="${NIGHTLY_BRANCH:-main}"
MAX_ATTEMPTS="${NIGHTLY_MAX_ATTEMPTS:-5}"
SLEEP_SECONDS="${NIGHTLY_RETRY_SLEEP:-5}"
ARTIFACT_DIR="${NIGHTLY_ARTIFACT_DIR:-}"

if [[ -n "${NIGHTLY_PATHS:-}" ]]; then
  # shellcheck disable=SC2206
  PATHS=(${NIGHTLY_PATHS})
else
  PATHS=(fiscal_model/data_files/bills.db site_data)
fi

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git add -- "${PATHS[@]}"
if git diff --cached --quiet; then
  echo "No changes to ${PATHS[*]}, skipping commit."
  exit 0
fi

SNAPSHOT="$(mktemp -d)"
cleanup() {
  rm -rf "${SNAPSHOT}"
}
trap cleanup EXIT

snapshot_paths() {
  local dest="$1"
  rm -rf "${dest}"
  mkdir -p "${dest}"
  local p
  for p in "${PATHS[@]}"; do
    if [[ ! -e "${p}" ]]; then
      echo "error: expected generated path missing: ${p}" >&2
      exit 1
    fi
    mkdir -p "${dest}/$(dirname "${p}")"
    cp -a "${p}" "${dest}/${p}"
  done
}

restore_paths() {
  local src="$1"
  local p
  for p in "${PATHS[@]}"; do
    rm -rf "${p}"
    mkdir -p "$(dirname "${p}")"
    cp -a "${src}/${p}" "${p}"
  done
}

snapshot_paths "${SNAPSHOT}"
if [[ -n "${ARTIFACT_DIR}" ]]; then
  snapshot_paths "${ARTIFACT_DIR}"
fi

COMMIT_MSG="chore: nightly bill tracker update and static export $(date -u +%Y-%m-%d)"

for attempt in $(seq 1 "${MAX_ATTEMPTS}"); do
  echo "Push attempt ${attempt}/${MAX_ATTEMPTS}"
  git fetch "${REMOTE}" "+refs/heads/${BRANCH}:refs/remotes/${REMOTE}/${BRANCH}"
  git reset --hard "${REMOTE}/${BRANCH}"
  restore_paths "${SNAPSHOT}"
  git add -- "${PATHS[@]}"
  if git diff --cached --quiet; then
    echo "Latest ${REMOTE}/${BRANCH} already has these artifacts; nothing to push."
    exit 0
  fi
  git commit --no-gpg-sign -m "${COMMIT_MSG}"

  if git push "${REMOTE}" "HEAD:${BRANCH}"; then
    echo "Pushed nightly update."
    exit 0
  fi

  if [[ "${attempt}" -eq "${MAX_ATTEMPTS}" ]]; then
    break
  fi
  echo "Push rejected or failed; waiting ${SLEEP_SECONDS}s before retrying against latest ${REMOTE}/${BRANCH}."
  sleep "${SLEEP_SECONDS}"
  SLEEP_SECONDS=$((SLEEP_SECONDS * 2))
done

echo "::error::Failed to push nightly bill tracker update after ${MAX_ATTEMPTS} attempts. Generated bills.db and site_data were not force-pushed."
exit 1
