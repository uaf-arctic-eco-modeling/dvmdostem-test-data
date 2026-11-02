# dvmdostem-test-data

Immutable test-data bundles for
[dvm-dos-tem](https://github.com/uaf-arctic-eco-modeling/dvm-dos-tem)
validation.

This public repository publishes the standard test-data tier as immutable
GitHub Release assets. It is intentionally separate from the model repository:
releasing test data cannot trigger the model's binary or container release
automation.

## Data tiers

| Tier | Location | Intended use |
| --- | --- | --- |
| Minimal | `dvm-dos-tem` repository | Offline, small tests |
| Standard | This repository's release assets | CI and scientific sentinels |
| Comprehensive | Separately managed optional data | Heavyweight developer and research validation |

Only standard bundles belong here. Do not commit released bundle contents to
Git history; publish them as release assets with their metadata sidecar.

## Consuming a bundle

The model repository pins an exact release version, asset URL, SHA-256 digest,
format version, intended scenario, and reference baseline in a reviewed
manifest. Consumers must verify the SHA-256 digest before extracting a bundle.
Do not consume mutable tags, branches, `latest`, or an unverified download.

## Publishing

Read [the release contract](docs/RELEASE_CONTRACT.md) before preparing a
bundle. Every release asset must have a companion metadata document valid
against [the bundle metadata schema](schemas/bundle-metadata.schema.json).

## Licensing

The MIT license in this repository applies to repository documentation and
automation only. Each data bundle declares its own license or redistribution
status in its metadata. A bundle without documented redistribution permission
must not be published here.
