#!/usr/bin/env python3
"""Create a deterministic staged test-data bundle and provenance templates."""

import argparse
import gzip
import hashlib
import json
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


PROVENANCE_FILES = {
    "README.md": """# Bundle provenance

Complete every `<TODO: ...>` marker before publishing this bundle.

This directory records how the ready-to-run inputs were produced. It is
included in the bundle archive so the operational artifact and its provenance
travel together.
""",
    "generation-command.txt": "<TODO: exact TEMdownscale command and configuration path>\n",
    "input-production-revision.txt": (
        "<TODO: repository URL, commit SHA, branch/tag, and clean/dirty status>\n"
    ),
    "input-production.patch": (
        "<TODO: replace with the exact patch, or state that the worktree was clean>\n"
    ),
    "source-data-checksums.txt": (
        "<TODO: source dataset identifiers, URLs/catalog paths, versions, and SHA-256 digests>\n"
    ),
    "environment.yml": (
        "# TODO: record the environment used by Input_production/TEMdownscale\n"
        "name: <TODO>\n"
        "dependencies:\n"
        "  - <TODO>\n"
    ),
    "run-selection.txt": (
        "<TODO: describe the grid window, active run-mask cells, and intended "
        "eq -> sp -> tr -> sc stage sequence>\n"
    ),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not supported: {path}")
        if path.is_file():
            files.append(path.relative_to(root))
    return sorted(files, key=lambda path: path.as_posix())


def write_provenance(root: Path) -> Path:
    provenance = root / "provenance"
    provenance.mkdir()
    for relative_path, content in PROVENANCE_FILES.items():
        path = provenance / relative_path
        path.write_text(content, encoding="utf-8")
    return provenance


def make_tar(source_root: Path, archive: Path) -> None:
    with archive.open("wb") as output:
        with gzip.GzipFile(fileobj=output, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as tar:
                for relative_path in relative_files(source_root):
                    source = source_root / relative_path
                    archive_path = PurePosixPath(relative_path.as_posix())
                    info = tar.gettarinfo(str(source), arcname=str(archive_path))
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    info.mode = 0o644
                    with source.open("rb") as file:
                        tar.addfile(info, file)


def inventory(archive_root: Path) -> list[dict[str, int | str]]:
    entries = []
    for relative_path in relative_files(archive_root):
        path = archive_root / relative_path
        entries.append(
            {
                "path": relative_path.as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return entries


def create_metadata_template(
    output: Path,
    archive: Path,
    archive_root: Path,
    release_version: str,
    data_maintainer: str,
    scenario_id: str,
) -> Path:
    metadata = {
        "schema_version": "1.0",
        "owners": {"data_maintainer": data_maintainer},
        "bundle": {
            "release_version": release_version,
            "asset_name": archive.name,
            "format": "tar.gz",
            "sha256": sha256_file(archive),
            "size_bytes": archive.stat().st_size,
        },
        "file_inventory": inventory(archive_root),
        "provenance": {
            "source_description": "<TODO: describe the source data>",
            "source_identifiers": [
                "<TODO: identify the source datasets and revisions>"
            ],
        },
        "redistribution": {
            "status": "provisional",
            "license_or_terms": (
                "Redistribution review pending; do not publish publicly."
            ),
        },
        "generation": {
            "procedure": "provenance/generation-command.txt",
            "generator_revision": (
                "<TODO: Input_production/TEMdownscale repository and revision>"
            ),
        },
        "intended_scenarios": [
            {
                "id": scenario_id,
                "description": "<TODO: describe the model scenario>",
                "expected_behavior": [
                    "<TODO: describe the operational behavior this bundle supports>"
                ],
            }
        ],
    }
    archive_stem = archive.name.removesuffix(".tar.gz")
    metadata_path = output / f"{archive_stem}.metadata.template.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata_path


def create_bundle(
    source: Path,
    output: Path,
    release_version: str,
    data_maintainer: str,
    scenario_id: str,
    refresh: bool,
) -> tuple[Path, Path]:
    if not source.is_dir():
        raise ValueError(f"Source directory does not exist: {source}")
    if output.exists() and any(output.iterdir()) and not refresh:
        raise ValueError(f"Output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    provenance = output / "provenance"
    if refresh:
        if not provenance.is_dir():
            raise ValueError(f"Missing provenance directory: {provenance}")
    else:
        write_provenance(output)

    with tempfile.TemporaryDirectory() as temporary_directory:
        archive_root = Path(temporary_directory) / source.name
        shutil.copytree(source, archive_root)
        shutil.copytree(provenance, Path(temporary_directory) / "provenance")
        archive = output / f"dvmdostem-standard-{release_version}.tar.gz"
        make_tar(Path(temporary_directory), archive)
        metadata = create_metadata_template(
            output,
            archive,
            Path(temporary_directory),
            release_version,
            data_maintainer,
            scenario_id,
        )
    return archive, metadata


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a deterministic staged dvm-dos-tem test-data bundle."
    )
    parser.add_argument("source_directory", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--release-version", required=True)
    parser.add_argument(
        "--data-maintainer",
        default="<TODO: name the data maintainer>",
    )
    parser.add_argument(
        "--scenario-id",
        default="<TODO: scenario id>",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Rebuild an existing output directory using its edited provenance.",
    )
    arguments = parser.parse_args()
    try:
        archive, metadata = create_bundle(
            arguments.source_directory,
            arguments.output_directory,
            arguments.release_version,
            arguments.data_maintainer,
            arguments.scenario_id,
            arguments.refresh,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Created archive: {archive}")
    print(f"Created metadata template: {metadata}")
    print("Complete provenance and metadata TODOs before validation or publication.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
