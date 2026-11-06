# Standard Test-Data Release Contract

## Purpose and scope

This repository publishes the standard test-data tier used by dvm-dos-tem CI
and scientific sentinel scenarios. Its releases are data publications, not
software releases. No workflow in this repository may call, dispatch, or
otherwise trigger `dvm-dos-tem` binary or container release automation.

## Roles

The data-release maintainers are:

- Helene Genet
- Eugenie Euskirchen
- Tobey Carman
- Ruth Rutter

A release requires approval from at least one designated maintainer after data
and provenance review. A maintainer who assembled the bundle may request the
release but may not provide its sole approval. Repository administrators must
maintain branch protection or rulesets that require the release pull request
to be reviewed before merge.

Scientific baseline and tolerance changes remain governed by the scientific
review process in the `dvm-dos-tem` repository; approving a data release does
not approve such a change.

## Bundle and release requirements

Each release contains exactly versioned, immutable bundle assets and their
metadata sidecars. Use a release tag in `vMAJOR.MINOR.PATCH` form. A release
may contain more than one bundle only when every bundle has a distinct
metadata document.

Before publishing, the release pull request must provide:

1. A bundle archive and its metadata document, validated against
   `schemas/bundle-metadata.schema.json`.
2. A named data maintainer responsible for the bundle.
3. The release version, SHA-256 digest, byte size, archive format, and schema
   version for every bundle.
4. Data provenance, generation procedure, source revision or source-data
   identifiers, and the intended dvm-dos-tem scenarios.
5. An explicit license identifier or redistribution status. Restricted,
   unclear, or absent redistribution permission blocks publication.
6. Evidence that the archive extracts successfully and that its listed files
   match the metadata.
7. A maintainer approval documenting the data/provenance review.

Before opening the release pull request, stage the archive and exactly one
`*.metadata.json` sidecar in a directory and run:

```shell
conda run --no-capture-output -n dvmdostem-test-data \
  python scripts/validate_bundle.py /path/to/staged-bundle
```

The validator supports `tar.gz` and `zip` archives. It verifies the metadata
contract, data maintainer, archive digest and size, and complete file
inventory without extracting the archive.

The release notes link the merged release pull request and enumerate every
asset's digest, size, intended scenario, provenance summary, and license or
redistribution status.

## Immutability and correction

Published release tags and assets are immutable:

- Do not replace, delete, rename, or overwrite a published asset.
- Do not retag an existing version.
- Do not add a mutable `latest` release or version range as a consumer
  contract.
- Correct a published bundle only by publishing a new version with new
  metadata and digest.

If a serious publication problem is discovered, mark the release as withdrawn
in its notes and notify consumers. Keep the original assets and metadata
available for historical reproducibility. A later model-repository manifest
change must select a replacement release explicitly.

## Main-repository compatibility

Publishing a bundle has no automatic effect on `dvm-dos-tem`. A bundle becomes
eligible for CI only after a maintainer opens a separate, reviewable manifest
update in that repository. That update pins the exact release and executes the
mapped checks. Code that needs new data follows the same sequence: release
data first, then make the linked or combined model-repository change.
