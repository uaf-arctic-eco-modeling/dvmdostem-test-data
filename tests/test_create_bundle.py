import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[1]
CREATOR = REPOSITORY_ROOT / "scripts" / "create_bundle.py"


class CreateBundleTests(unittest.TestCase):
    def run_creator(
        self, source: Path, output: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(CREATOR),
                str(source),
                str(output),
                "--release-version",
                "v0.1.0",
                "--data-maintainer",
                "Test Maintainer",
                "--scenario-id",
                "stage-run",
            ],
            check=False,
            text=True,
            capture_output=True,
        )

    def test_creates_deterministic_archive_and_provenance_template(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "data"
            source.mkdir()
            (source / "input.txt").write_text("input\n", encoding="utf-8")
            output_one = root / "bundle-one"
            output_two = root / "bundle-two"

            first = self.run_creator(source, output_one)
            second = self.run_creator(source, output_two)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            archive_one = output_one / "dvmdostem-standard-v0.1.0.tar.gz"
            archive_two = output_two / "dvmdostem-standard-v0.1.0.tar.gz"
            self.assertEqual(
                hashlib.sha256(archive_one.read_bytes()).digest(),
                hashlib.sha256(archive_two.read_bytes()).digest(),
            )
            self.assertTrue((output_one / "provenance/generation-command.txt").is_file())
            with tarfile.open(archive_one, "r:gz") as archive:
                self.assertEqual(
                    sorted(archive.getnames()),
                    sorted(
                        [
                        "data/input.txt",
                        "provenance/README.md",
                        "provenance/environment.yml",
                        "provenance/generation-command.txt",
                        "provenance/input-production.patch",
                        "provenance/input-production-revision.txt",
                        "provenance/run-selection.txt",
                        "provenance/source-data-checksums.txt",
                        ]
                    ),
                )
            template = output_one / "dvmdostem-standard-v0.1.0.metadata.template.json"
            metadata = json.loads(template.read_text(encoding="utf-8"))
            self.assertEqual(metadata["bundle"]["release_version"], "v0.1.0")
            self.assertIn("<TODO:", metadata["provenance"]["source_description"])

    def test_refresh_includes_completed_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "data"
            source.mkdir()
            (source / "input.txt").write_text("input\n", encoding="utf-8")
            output = root / "bundle"

            first = self.run_creator(source, output)
            self.assertEqual(first.returncode, 0, first.stderr)
            provenance_file = output / "provenance/generation-command.txt"
            provenance_file.write_text("temdownscale --config config.json\n")
            refreshed = subprocess.run(
                [
                    sys.executable,
                    str(CREATOR),
                    str(source),
                    str(output),
                    "--release-version",
                    "v0.1.0",
                    "--refresh",
                ],
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            with tarfile.open(
                output / "dvmdostem-standard-v0.1.0.tar.gz", "r:gz"
            ) as archive:
                command = archive.extractfile(
                    "provenance/generation-command.txt"
                ).read()
            self.assertEqual(command, b"temdownscale --config config.json\n")

    def test_rejects_nonempty_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "data"
            source.mkdir()
            (source / "input.txt").write_text("input\n", encoding="utf-8")
            output = root / "bundle"
            output.mkdir()
            (output / "existing").write_text("do not overwrite\n", encoding="utf-8")

            result = self.run_creator(source, output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not empty", result.stderr)
