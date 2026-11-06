#!/usr/bin/env python3
"""Validate a staged dvm-dos-tem standard test-data bundle."""

import argparse
import hashlib
import json
import re
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO


SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
RELEASE_VERSION_PATTERN = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "owners",
    "bundle",
    "file_inventory",
    "provenance",
    "redistribution",
    "generation",
    "intended_scenarios",
}


class ValidationError(Exception):
    """Raised when a bundle does not meet the release contract."""


def require_mapping(value: Any, name: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be an object.")
    if set(value) != keys:
        raise ValidationError(f"{name} must contain exactly: {', '.join(sorted(keys))}.")
    return value


def require_nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{name} must be a non-empty string.")
    return value


def require_sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise ValidationError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def require_size(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValidationError(f"{name} must be an integer greater than zero.")
    return value


def require_relative_path(value: Any, name: str) -> str:
    path = PurePosixPath(require_nonempty_string(value, name))
    if path.is_absolute() or ".." in path.parts or path == PurePosixPath("."):
        raise ValidationError(f"{name} must be a safe relative path.")
    return path.as_posix()


def validate_metadata(metadata: Any) -> dict[str, Any]:
    metadata = require_mapping(metadata, "metadata", REQUIRED_TOP_LEVEL_KEYS)
    if metadata["schema_version"] != "1.0":
        raise ValidationError("schema_version must be 1.0.")

    owners = require_mapping(
        metadata["owners"], "owners", {"data_maintainer"}
    )
    require_nonempty_string(owners["data_maintainer"], "owners.data_maintainer")

    bundle = require_mapping(
        metadata["bundle"],
        "bundle",
        {"release_version", "asset_name", "format", "sha256", "size_bytes"},
    )
    release_version = require_nonempty_string(
        bundle["release_version"], "bundle.release_version"
    )
    if not RELEASE_VERSION_PATTERN.fullmatch(release_version):
        raise ValidationError(
            "bundle.release_version must use vMAJOR.MINOR.PATCH form."
        )
    asset_name = require_relative_path(bundle["asset_name"], "bundle.asset_name")
    if "/" in asset_name:
        raise ValidationError("bundle.asset_name must name an archive in the bundle directory.")
    archive_format = require_nonempty_string(bundle["format"], "bundle.format")
    if archive_format not in {"tar.gz", "zip"}:
        raise ValidationError("bundle.format must be tar.gz or zip.")
    require_sha256(bundle["sha256"], "bundle.sha256")
    require_size(bundle["size_bytes"], "bundle.size_bytes")

    inventory = metadata["file_inventory"]
    if not isinstance(inventory, list) or not inventory:
        raise ValidationError("file_inventory must be a non-empty array.")
    inventory_paths = set()
    for index, item in enumerate(inventory):
        item = require_mapping(
            item,
            f"file_inventory[{index}]",
            {"path", "sha256", "size_bytes"},
        )
        path = require_relative_path(item["path"], f"file_inventory[{index}].path")
        if path in inventory_paths:
            raise ValidationError(f"file_inventory contains duplicate path: {path}.")
        inventory_paths.add(path)
        require_sha256(item["sha256"], f"file_inventory[{index}].sha256")
        require_size(item["size_bytes"], f"file_inventory[{index}].size_bytes")

    provenance = require_mapping(
        metadata["provenance"],
        "provenance",
        {"source_description", "source_identifiers"},
    )
    require_nonempty_string(provenance["source_description"], "provenance.source_description")
    require_nonempty_strings(provenance["source_identifiers"], "provenance.source_identifiers")

    redistribution = require_mapping(
        metadata["redistribution"],
        "redistribution",
        {"status", "license_or_terms"},
    )
    if redistribution["status"] != "permitted":
        raise ValidationError("redistribution.status must be permitted.")
    require_nonempty_string(
        redistribution["license_or_terms"], "redistribution.license_or_terms"
    )

    generation = require_mapping(
        metadata["generation"],
        "generation",
        {"procedure", "generator_revision"},
    )
    require_nonempty_string(generation["procedure"], "generation.procedure")
    require_nonempty_string(
        generation["generator_revision"], "generation.generator_revision"
    )

    scenarios = metadata["intended_scenarios"]
    if not isinstance(scenarios, list) or not scenarios:
        raise ValidationError("intended_scenarios must be a non-empty array.")
    for index, scenario in enumerate(scenarios):
        scenario = require_mapping(
            scenario,
            f"intended_scenarios[{index}]",
            {"id", "description", "expected_behavior"},
        )
        require_nonempty_string(scenario["id"], f"intended_scenarios[{index}].id")
        require_nonempty_string(
            scenario["description"], f"intended_scenarios[{index}].description"
        )
        require_nonempty_strings(
            scenario["expected_behavior"],
            f"intended_scenarios[{index}].expected_behavior",
        )

    return metadata


def require_nonempty_strings(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValidationError(f"{name} must be a non-empty array.")
    for index, item in enumerate(value):
        require_nonempty_string(item, f"{name}[{index}]")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_members(archive: Path, archive_format: str) -> dict[str, tuple[str, int]]:
    if archive_format == "tar.gz":
        with tarfile.open(archive, "r:gz") as opened_archive:
            return {
                member.name: member_digest(opened_archive.extractfile(member), member.name)
                for member in opened_archive.getmembers()
                if member.isfile()
            }
    with zipfile.ZipFile(archive) as opened_archive:
        return {
            member.filename: member_digest(
                opened_archive.open(member), member.filename, member.file_size
            )
            for member in opened_archive.infolist()
            if not member.is_dir()
        }


def member_digest(
    stream: BinaryIO | None, path: str, expected_size: int | None = None
) -> tuple[str, int]:
    if stream is None:
        raise ValidationError(f"Could not read archive member: {path}.")
    digest = hashlib.sha256()
    size = 0
    with stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    if expected_size is not None and size != expected_size:
        raise ValidationError(f"Archive member size does not match: {path}.")
    return digest.hexdigest(), size


def validate_bundle(directory: Path) -> None:
    metadata_paths = sorted(directory.glob("*.metadata.json"))
    if len(metadata_paths) != 1:
        raise ValidationError(
            "Bundle directory must contain exactly one *.metadata.json file."
        )
    try:
        metadata = json.loads(metadata_paths[0].read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValidationError(f"Metadata is not valid JSON: {error.msg}.") from error
    metadata = validate_metadata(metadata)

    bundle = metadata["bundle"]
    archive = directory / bundle["asset_name"]
    if not archive.is_file():
        raise ValidationError(f"Bundle archive is missing: {bundle['asset_name']}.")
    if archive.stat().st_size != bundle["size_bytes"]:
        raise ValidationError("Bundle archive size does not match bundle.size_bytes.")
    if sha256_file(archive) != bundle["sha256"]:
        raise ValidationError("Bundle archive SHA-256 does not match bundle.sha256.")

    members = archive_members(archive, bundle["format"])
    inventory = {
        item["path"]: (item["sha256"], item["size_bytes"])
        for item in metadata["file_inventory"]
    }
    if members != inventory:
        raise ValidationError("Archive files do not match file_inventory.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a staged dvm-dos-tem test-data bundle directory."
    )
    parser.add_argument("bundle_directory", type=Path)
    arguments = parser.parse_args()
    try:
        validate_bundle(arguments.bundle_directory)
    except (OSError, tarfile.TarError, zipfile.BadZipFile, ValidationError) as error:
        print(f"Bundle validation failed: {error}", file=sys.stderr)
        return 1
    print("Bundle validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
