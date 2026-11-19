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

### Validating a staged bundle

Create the repository's dedicated environment once:

```shell
conda env create --file environment.yml
```

Stage one archive and its `<name>.metadata.json` sidecar in an otherwise empty
directory, then validate them before opening the release pull request:

```shell
conda run --no-capture-output -n dvmdostem-test-data \
  python scripts/validate_bundle.py /path/to/staged-bundle
```

The command requires exactly one metadata sidecar and validates the metadata
schema contract, data maintainer, archive SHA-256 digest and size, and the
complete file inventory. It supports `tar.gz` and `zip` archives. It inspects
archives without extracting them.

Redistribution status may be `provisional`, `internal-only`, or `permitted`.
The first two statuses allow process validation but are not eligible for a
public release. Add `--require-public` when validating a release candidate:

```shell
conda run --no-capture-output -n dvmdostem-test-data \
  python scripts/validate_bundle.py --require-public /path/to/staged-bundle
```

### Creating a staged bundle

The repository does not require raw source inputs to be committed as a release
asset. Create a staging directory outside Git history from a ready-to-run
source tree:

```shell
conda run --no-capture-output -n dvmdostem-test-data \
  python scripts/create_bundle.py data /tmp/dvmdostem-bundle-v0.1.0 \
  --release-version v0.1.0 \
  --data-maintainer "Maintainer Name" \
  --scenario-id stage-run
```

The command creates a deterministic archive, a metadata template, and an
editable `/tmp/dvmdostem-bundle-v0.1.0/provenance/` directory containing
`<TODO: ...>` markers. Complete those records, then rebuild the archive:

```shell
conda run --no-capture-output -n dvmdostem-test-data \
  python scripts/create_bundle.py data /tmp/dvmdostem-bundle-v0.1.0 \
  --release-version v0.1.0 \
  --data-maintainer "Maintainer Name" \
  --scenario-id stage-run \
  --refresh
```

Finally, rename the metadata template from
`*.metadata.template.json` to `*.metadata.json`, complete all metadata TODOs,
and run the validator. The template is intentionally not release-valid until
the operator supplies provenance, scenario, and redistribution details.

Run the validator's test suite with:

```shell
conda run --no-capture-output -n dvmdostem-test-data \
  python -m unittest discover -s tests -v
```

## Licensing

The MIT license in this repository applies to repository documentation and
automation only. Each data bundle declares its own license or redistribution
status in its metadata. A bundle without documented redistribution permission
must not be published here.
