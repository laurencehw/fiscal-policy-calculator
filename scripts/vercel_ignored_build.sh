#!/usr/bin/env bash
# Vercel "Ignored Build Step" for the two projects built from this repository.
#
#   fiscal-engine       Root Directory engine/  ->  bash ../scripts/vercel_ignored_build.sh engine
#   fiscal-calculator   Root Directory web/     ->  bash ../scripts/vercel_ignored_build.sh web
#
# Both projects' vercel.json set this as `ignoreCommand`, which overrides the
# dashboard setting, so nothing needs changing there.
#
# Vercel's convention: exit 0 skips the build, exit 1 builds. Anything this
# script cannot work out (no previous commit, unknown project) builds, so a
# mistake here costs a build, never a missed deploy.
#
# Before this (22 Nov 2026) both projects built every one of the cycle's 163
# commits: every push built twice, though most change only one side.
set -u

project="${1:-}"
case "$project" in
  # The engine bundle: engine/build.py copies api.py, fiscal_model/ and
  # classroom/ in from the repository root (see engine/build.py).
  engine) paths=(engine api.py fiscal_model classroom scripts/vercel_ignored_build.sh) ;;
  # The site: web/ plus ../site_data, which its pages read at build time
  # (web/lib/data.ts, web/next.config.ts).
  web) paths=(web site_data scripts/vercel_ignored_build.sh) ;;
  *) echo "unknown project '$project': building"; exit 1 ;;
esac

# Only main deploys automatically. Any other branch can be deployed by hand.
ref="${VERCEL_GIT_COMMIT_REF:-}"
if [ -n "$ref" ] && [ "$ref" != "main" ]; then
  echo "branch '$ref' is not main: skipping (deploy by hand if a preview is needed)"
  exit 0
fi

cd "$(git rev-parse --show-toplevel)" || { echo "not a git checkout: building"; exit 1; }

# Compare with the commit this project last deployed when Vercel provides it
# (that covers a push of several commits at once), else with the parent.
base="${VERCEL_GIT_PREVIOUS_SHA:-}"
if [ -z "$base" ] || ! git cat-file -e "${base}^{commit}" 2>/dev/null; then
  base="HEAD^"
  if ! git cat-file -e "HEAD^{commit}" 2>/dev/null || ! git rev-parse -q --verify HEAD^ >/dev/null; then
    echo "no earlier commit to compare with: building"
    exit 1
  fi
fi

if git diff --quiet "$base" HEAD -- "${paths[@]}"; then
  echo "$project: nothing in ${paths[*]} changed since $base: skipping"
  exit 0
fi
echo "$project: changes since $base in ${paths[*]}: building"
exit 1
