#!/usr/bin/env python
"""
Fetch the raw CPS ASEC extract the microdata builder reads, by script.

Owner Decision 4 (``planning/MODELING_IMPROVEMENT.md`` §6, accepted
2026-09-01): the raw CPS ASEC person and household files are **fetched at
build time and never vendored**. Only the derived tax-unit file
(``fiscal_model/microsim/tax_microdata_2024.csv``, 7 MB) is under version
control; the source archive is 148 MB and lives in a cache outside the
repository.

What this script does
---------------------
1. Downloads the Census Bureau's ASEC public-use archive to a cache directory
   (default ``~/.cache/fiscal-policy-calculator/cps_asec``, overridable with
   ``--cache-dir`` or ``$FPC_CACHE_DIR``). An archive already in the cache is
   reused rather than re-downloaded.
2. Verifies its SHA-256 against :data:`ASEC_2024_SHA256`, so a silently
   re-published file cannot change the derived microdata without anyone
   noticing. ``--allow-checksum-mismatch`` records the observed digest and
   continues, for the case where Census reissues the year.
3. Extracts ``pppub24.csv`` and ``hhpub24.csv`` next to the archive and prints
   the directory ``fiscal_model.microsim.data_builder`` should be pointed at.

Usage
-----
::

    python scripts/fetch_cps_asec.py                 # fetch + extract
    python scripts/fetch_cps_asec.py --print-dir     # where would it go?
    python -m fiscal_model.microsim.data_builder --fetch   # fetch, then build

Provenance
----------
U.S. Census Bureau, *Current Population Survey, Annual Social and Economic
Supplement (ASEC), March 2024*, public-use microdata, CSV distribution.
Landing page: https://www.census.gov/data/datasets/2024/demo/cps/cps-asec-2024.html
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

#: Census Bureau URL for the 2024 ASEC public-use CSV archive.
ASEC_2024_URL = (
    "https://www2.census.gov/programs-surveys/cps/datasets/2024/march/"
    "asecpub24csv.zip"
)

#: Archive filename inside the cache directory.
ASEC_2024_ARCHIVE = "asecpub24csv.zip"

#: SHA-256 of the archive as published (Last-Modified 2024-09-10,
#: Content-Length 148,664,101), verified 2026-09-02.
ASEC_2024_SHA256 = "cdb39cdac34bef99dd0940ab28e306f692404c2eea44d85dfd634214872a0a09"

#: Expected size in bytes, checked before the (slower) hash.
ASEC_2024_BYTES = 148_664_101

#: The two members the builder actually reads. ``ffpub24.csv`` (family) and
#: the replicate-weight file are not extracted: nothing in this repository
#: reads them, and they are another 200 MB on disk.
ASEC_2024_MEMBERS = ("pppub24.csv", "hhpub24.csv")

#: Chunk size for the streaming download and the streaming hash.
_CHUNK = 1 << 20


def default_cache_dir() -> Path:
    """Cache root for raw survey extracts — deliberately outside the repo."""
    override = os.environ.get("FPC_CACHE_DIR")
    root = Path(override) if override else Path.home() / ".cache" / "fiscal-policy-calculator"
    return root / "cps_asec"


def sha256_of(path: Path) -> str:
    """Streaming SHA-256, so a 148 MB archive never lands in memory whole."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path, *, quiet: bool = False) -> Path:
    """Stream ``url`` to ``destination``, writing through a ``.part`` file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    if not quiet:
        print(f"Downloading {url}")
    with urllib.request.urlopen(url) as response, partial.open("wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        seen = 0
        while True:
            block = response.read(_CHUNK)
            if not block:
                break
            handle.write(block)
            seen += len(block)
            if not quiet and total:
                pct = 100.0 * seen / total
                print(f"\r  {seen / 1e6:,.0f} MB / {total / 1e6:,.0f} MB ({pct:.0f}%)", end="")
    if not quiet:
        print()
    partial.replace(destination)
    return destination


def fetch_archive(
    cache_dir: Path | None = None,
    *,
    force: bool = False,
    allow_checksum_mismatch: bool = False,
    quiet: bool = False,
) -> Path:
    """Return a verified local copy of the ASEC archive, downloading if needed."""
    cache_dir = cache_dir or default_cache_dir()
    archive = cache_dir / ASEC_2024_ARCHIVE

    if force and archive.exists():
        archive.unlink()

    if not archive.exists():
        download(ASEC_2024_URL, archive, quiet=quiet)

    size = archive.stat().st_size
    if size != ASEC_2024_BYTES and not allow_checksum_mismatch:
        raise RuntimeError(
            f"{archive} is {size:,} bytes, expected {ASEC_2024_BYTES:,}. "
            "Delete it and re-run, or pass --allow-checksum-mismatch."
        )

    digest = sha256_of(archive)
    if digest != ASEC_2024_SHA256:
        message = (
            f"SHA-256 mismatch for {archive}\n"
            f"  expected {ASEC_2024_SHA256}\n"
            f"  observed {digest}\n"
            "Census may have reissued the file. Record the new digest in "
            "scripts/fetch_cps_asec.py before trusting a rebuild."
        )
        if not allow_checksum_mismatch:
            raise RuntimeError(message)
        print(f"WARNING: {message}", file=sys.stderr)
    elif not quiet:
        print(f"SHA-256 verified: {digest}")

    return archive


def extract_members(
    archive: Path,
    *,
    members: tuple[str, ...] = ASEC_2024_MEMBERS,
    force: bool = False,
    quiet: bool = False,
) -> Path:
    """Extract ``members`` beside ``archive`` and return the directory."""
    target = archive.parent / "extracted"
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        available = {info.filename for info in zf.infolist()}
        missing = [name for name in members if name not in available]
        if missing:
            raise RuntimeError(f"{archive} does not contain {missing}")
        for name in members:
            destination = target / name
            if destination.exists() and not force:
                if not quiet:
                    print(f"  {name} already extracted")
                continue
            if not quiet:
                print(f"  extracting {name}")
            with zf.open(name) as source, destination.open("wb") as handle:
                shutil.copyfileobj(source, handle, length=_CHUNK)
    return target


def ensure_cps_asec(
    cache_dir: Path | None = None,
    *,
    force: bool = False,
    allow_checksum_mismatch: bool = False,
    quiet: bool = False,
) -> Path:
    """Fetch, verify and extract in one call; returns the extracted directory.

    This is what ``fiscal_model.microsim.data_builder --fetch`` calls.
    """
    archive = fetch_archive(
        cache_dir,
        force=force,
        allow_checksum_mismatch=allow_checksum_mismatch,
        quiet=quiet,
    )
    return extract_members(archive, force=force, quiet=quiet)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help=f"Cache root (default {default_cache_dir()}).",
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-download and re-extract."
    )
    parser.add_argument(
        "--allow-checksum-mismatch",
        action="store_true",
        help="Warn instead of failing when the archive digest has changed.",
    )
    parser.add_argument(
        "--print-dir",
        action="store_true",
        help="Print the extraction directory and exit without fetching.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")
    args = parser.parse_args(argv)

    cache_dir = args.cache_dir or default_cache_dir()
    if args.print_dir:
        print(cache_dir / "extracted")
        return 0

    target = ensure_cps_asec(
        cache_dir,
        force=args.force,
        allow_checksum_mismatch=args.allow_checksum_mismatch,
        quiet=args.quiet,
    )
    if not args.quiet:
        print(f"\nCPS ASEC 2024 ready at {target}")
        print("Build the tax-unit file with:")
        print(f"  python -m fiscal_model.microsim.data_builder --data-dir {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
