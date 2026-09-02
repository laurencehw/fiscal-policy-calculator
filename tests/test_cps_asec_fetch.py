"""
The CPS ASEC fetch-and-build path (owner Decision 4).

The raw extract is fetched by script at build time and never vendored, so
these tests pin the two things that make the build reproducible: the archive's
identity (URL, size, digest) and the builder's dependent age bands. Nothing
here touches the network — the download itself is exercised only through a
stubbed opener.
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from fiscal_model.data.cps_asec import DEPENDENT_COLUMNS, load_tax_microdata
from fiscal_model.microsim.data_builder import (
    OUTPUT_COLUMNS,
    _dependent_age_bands,
    write_provenance,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_fetch_module():
    path = PROJECT_ROOT / "scripts" / "fetch_cps_asec.py"
    spec = importlib.util.spec_from_file_location("fetch_cps_asec_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch = _load_fetch_module()


class TestArchiveIdentity:
    def test_url_points_at_the_census_2024_asec_archive(self):
        assert fetch.ASEC_2024_URL == (
            "https://www2.census.gov/programs-surveys/cps/datasets/2024/march/"
            "asecpub24csv.zip"
        )

    def test_digest_and_size_are_pinned(self):
        """A silently re-published archive must not change the microdata."""
        assert fetch.ASEC_2024_BYTES == 148_664_101
        assert fetch.ASEC_2024_SHA256 == (
            "cdb39cdac34bef99dd0940ab28e306f692404c2eea44d85dfd634214872a0a09"
        )
        assert len(fetch.ASEC_2024_SHA256) == 64

    def test_cache_dir_is_outside_the_repository(self):
        """Decision 4: the 148 MB archive never lands in the working tree."""
        cache = fetch.default_cache_dir().resolve()
        assert PROJECT_ROOT.resolve() not in cache.parents
        assert cache != PROJECT_ROOT.resolve()

    def test_cache_dir_honours_the_environment_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FPC_CACHE_DIR", str(tmp_path))
        assert fetch.default_cache_dir() == tmp_path / "cps_asec"

    def test_only_the_two_files_the_builder_reads_are_extracted(self):
        assert fetch.ASEC_2024_MEMBERS == ("pppub24.csv", "hhpub24.csv")


class TestChecksumEnforcement:
    def _archive(self, tmp_path: Path, payload: bytes) -> Path:
        archive = tmp_path / fetch.ASEC_2024_ARCHIVE
        archive.write_bytes(payload)
        return archive

    def test_wrong_size_is_refused(self, tmp_path):
        self._archive(tmp_path, b"not the census archive")
        with pytest.raises(RuntimeError, match=re.escape("expected 148,664,101")):
            fetch.fetch_archive(tmp_path)

    def test_mismatch_can_be_overridden_explicitly(self, tmp_path, capsys):
        self._archive(tmp_path, b"not the census archive")
        archive = fetch.fetch_archive(tmp_path, allow_checksum_mismatch=True)
        assert archive.exists()
        assert "SHA-256 mismatch" in capsys.readouterr().err

    def test_sha256_of_is_streaming_and_correct(self, tmp_path):
        import hashlib

        payload = b"x" * (3 * (1 << 20) + 17)
        path = tmp_path / "blob.bin"
        path.write_bytes(payload)
        assert fetch.sha256_of(path) == hashlib.sha256(payload).hexdigest()

    def test_extract_refuses_an_archive_missing_a_member(self, tmp_path):
        archive = tmp_path / "partial.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("pppub24.csv", "A_AGE\n1\n")
        with pytest.raises(RuntimeError, match="does not contain"):
            fetch.extract_members(archive)


class TestDependentAgeBands:
    def _people(self, ages_and_enrollment):
        return pd.DataFrame(
            [
                {"A_AGE": age, "A_ENRLW": enrolled}
                for age, enrolled in ages_and_enrollment
            ]
        )

    def test_bands_cut_at_the_statutory_boundaries(self):
        people = self._people(
            [(2, 0), (5, 0), (6, 0), (16, 0), (17, 0), (18, 0), (20, 1), (22, 2)]
        )
        bands = _dependent_age_bands(people)
        assert bands == {
            "dependents_under_6": 2,
            "dependents_6_to_16": 2,
            "dependents_age_17": 1,
            "dependents_age_18": 1,
            # 20 attends school; 22 does not, so only one counts.
            "dependents_19_to_23_student": 1,
        }

    def test_empty_unit_gives_zeros_for_every_band(self):
        bands = _dependent_age_bands(pd.DataFrame(columns=["A_AGE", "A_ENRLW"]))
        assert set(bands) == {
            "dependents_under_6",
            "dependents_6_to_16",
            "dependents_age_17",
            "dependents_age_18",
            "dependents_19_to_23_student",
        }
        assert all(value == 0 for value in bands.values())

    def test_every_band_is_an_output_column(self):
        for column in _dependent_age_bands(
            pd.DataFrame(columns=["A_AGE", "A_ENRLW"])
        ):
            assert column in OUTPUT_COLUMNS


class TestBundledFileCarriesDependentDetail:
    def test_loader_reports_dependent_ages_present(self):
        df, source = load_tax_microdata()
        assert source.has_dependent_ages is True
        for column in DEPENDENT_COLUMNS:
            assert column in df.columns

    def test_under_17_bands_reconcile_with_the_children_column(self):
        """The two under-17 bands must sum to the legacy ``children`` column.

        They are computed over different sets — the bands over the unit's
        dependents, ``children`` over all its members — so agreement is a real
        check on the tax-unit construction, not a tautology.
        """
        df, _ = load_tax_microdata()
        weighted_bands = (
            (df["dependents_under_6"] + df["dependents_6_to_16"]) * df["weight"]
        ).sum()
        weighted_children = (df["children"] * df["weight"]).sum()
        assert weighted_bands == pytest.approx(weighted_children, rel=1e-9)

    def test_eitc_qualifying_children_exceed_the_under_17_count(self):
        """Under-19s and student dependents are EITC children and were invisible."""
        df, _ = load_tax_microdata()
        qualifying = (
            df["dependents_under_6"]
            + df["dependents_6_to_16"]
            + df["dependents_age_17"]
            + df["dependents_age_18"]
            + df["dependents_19_to_23_student"]
        )
        weighted_qualifying = (qualifying * df["weight"]).sum() / 1e6
        weighted_children = (df["children"] * df["weight"]).sum() / 1e6
        assert weighted_children == pytest.approx(65.0, abs=0.5)
        assert weighted_qualifying == pytest.approx(79.7, abs=0.5)

    def test_provenance_sidecar_records_the_archive_digest(self):
        sidecar = (
            PROJECT_ROOT
            / "fiscal_model"
            / "microsim"
            / "tax_microdata_2024.provenance.json"
        )
        assert sidecar.exists(), "the bundled microdata must ship its provenance"
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        assert payload["archive_sha256"] == fetch.ASEC_2024_SHA256
        assert payload["archive_url"] == fetch.ASEC_2024_URL
        assert payload["builder"] == "fiscal_model.microsim.data_builder"
        assert set(payload["output_columns"]) == set(OUTPUT_COLUMNS)

    def test_csv_itself_has_no_comment_header(self):
        """A ``#`` line would break the bare ``read_csv`` several callers use."""
        path = PROJECT_ROOT / "fiscal_model" / "microsim" / "tax_microdata_2024.csv"
        with path.open("r", encoding="utf-8") as handle:
            first = handle.readline()
        assert not first.startswith("#")
        assert first.split(",")[0] == "id"


class TestProvenanceSidecar:
    def test_sidecar_is_written_next_to_the_csv(self, tmp_path):
        output = tmp_path / "tax_microdata_test.csv"
        output.write_text("id\n1\n", encoding="utf-8")
        sidecar = write_provenance(
            output,
            data_dir=str(tmp_path),
            summary={"records_created": 1.0},
            warnings=["a warning"],
        )
        assert sidecar == tmp_path / "tax_microdata_test.provenance.json"
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        assert payload["warnings"] == ["a warning"]
        assert payload["summary"]["records_created"] == 1.0
        # A machine-local cache path is not provenance and must not leak in.
        assert "extract_dir" not in payload

    def test_sidecar_is_valid_json_with_a_trailing_newline(self, tmp_path):
        output = tmp_path / "x.csv"
        output.write_text("id\n", encoding="utf-8")
        sidecar = write_provenance(
            output, data_dir=str(tmp_path), summary={}, warnings=[]
        )
        text = sidecar.read_text(encoding="utf-8")
        assert text.endswith("\n")
        json.loads(io.StringIO(text).read())
