import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[1]
VALIDATOR = REPOSITORY_ROOT / "scripts" / "validate_bundle.py"


def create_bundle(directory: Path) -> Path:
    source = directory / "scenario" / "inputs.txt"
    source.parent.mkdir()
    source.write_text("test inputs\n", encoding="utf-8")

    archive = directory / "restart-scenario.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(source, arcname="scenario/inputs.txt")

    metadata = {
        "schema_version": "1.0",
        "owners": {"data_maintainer": "test-maintainer"},
        "bundle": {
            "release_version": "v1.0.0",
            "asset_name": archive.name,
            "format": "tar.gz",
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "size_bytes": archive.stat().st_size,
        },
        "file_inventory": [
            {
                "path": "scenario/inputs.txt",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "size_bytes": source.stat().st_size,
            }
        ],
        "provenance": {
            "source_description": "Generated test input.",
            "source_identifiers": ["test-fixture"],
        },
        "redistribution": {
            "status": "permitted",
            "license_or_terms": "MIT",
        },
        "generation": {
            "procedure": "tests/test_validate_bundle.py",
            "generator_revision": "test-fixture",
        },
        "intended_scenarios": [
            {
                "id": "restart",
                "description": "Restart workflow input.",
                "expected_behavior": ["The model can resume a run."],
            }
        ],
    }
    metadata_path = directory / "restart-scenario.metadata.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    return metadata_path


def validate(directory: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(directory)],
        check=False,
        text=True,
        capture_output=True,
    )


class ValidateBundleTests(unittest.TestCase):
    def test_accepts_a_complete_bundle_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            create_bundle(directory)

            result = validate(directory)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Bundle validation passed", result.stdout)

    def test_rejects_an_archive_that_does_not_match_its_declared_digest(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            metadata_path = create_bundle(directory)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["bundle"]["sha256"] = "0" * 64
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

            result = validate(directory)

        self.assertEqual(result.returncode, 1)
        self.assertIn("SHA-256", result.stderr)

    def test_rejects_metadata_without_a_data_maintainer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            metadata_path = create_bundle(directory)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            del metadata["owners"]
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

            result = validate(directory)

        self.assertEqual(result.returncode, 1)
        self.assertIn("owners", result.stderr)
