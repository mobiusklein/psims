# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog][Keep a Changelog] and this project adheres to [Semantic Versioning][Semantic Versioning].

## [v1.2.0] - 2022-07-29

### Changed
1. When giving a `Spectrum` an ID value which is just an integer, the writer will attempt to convert it into
   the appropriate nativeID format. To control the nativeID format, set `MzMLWriter.native_id_format` or include
   an appropriate `cvParam` term in the `MzMLWriter.file_description` parameters.

### Fixed
1. When a CV fails to import another CV, that failure will be noted and it won't attempt to download again.


## [v1.1.0] - 2022-07-29

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2022-02-23 | a397dc95d8d809acea44209818a0f77f |
| go.obo.gz | releases/2022-07-01 | 1b557078fdb541dbed5ee3fb1f51cbed |
| pato.obo.gz | releases/2022-07-21/pato.obo | 1b9d2d654020da497b0ebb5934451acb |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.95 | c9a6c38ae4ec451a839f2a200b7bf601 |
| unimod_tables.xml.gz | - | 523d0bb41eeb41bb1554fa405915e310 |
| unit.obo.gz | - | 1f6e1b5122ea4c2d3797bae72f140ab1 |

### Added
1. `OBOCache.load` wraps the resolve/fallback and `OBOParser` parsing steps in a single call to produce a
   `ControlledVocabulary` instance.

### Changed
1. `DocumentContext` objects are always truthy, regardless of whether they have any keys.
2. `ControlledVocabulary` instances will now also query their imports (restricted to OBO imports for now)
   when looking up missing terms.
3. `VocabularyResolver` instances now cache CVs loaded through them to avoid having multiple copies of
   the same CV for the same document. This applies to CVs imported indirectly as well.


### Deprecated

### Removed

### Fixed

### Security



## [v.1.1.0] - 2022-07-07

### Added
- Added `MzMLWriter.native_id_format` attribute that governs how integers are converted into strings for the
  spectrum id attribute. This will default to `MS:1000774` `multiple peak list nativeID format`. If `fileContents`
  includes a nativeID format term and it is not been explicitly specified, that format will be used. This has no
  effect when specifying a a spectrum id with a string.

### Changed

### Deprecated

### Removed

### Fixed

### Security


## [v1.0.0] - 2022-06-15

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2022-02-23 | a397dc95d8d809acea44209818a0f77f |
| go.obo.gz | releases/2022-05-16 | 3408f54d9b0e2c7a1e71322ee17fda55 |
| pato.obo.gz | releases/2019-09-05 | 443de10a418cba2b0a6f4a9c3b73c60c |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.91 | fd8c3970411f47d57ec47c470f5c2db2 |
| unimod_tables.xml.gz | - | 523d0bb41eeb41bb1554fa405915e310 |
| unit.obo.gz | releases/2020-03-10 | 4e45267605698d1fcda533c27853a8fc |

### Changed
1. **Breaking** The default behavior for all writer classes (`MzMLWriter`, `MzIdentMLWriter`, etc.) will now be to *close* files if they are closable. To preserve the
   previous behavior, explicitly pass `close=False`.


## [v0.1.47] - 2022-04-25

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2022-02-23 | a397dc95d8d809acea44209818a0f77f |
| go.obo.gz | releases/2022-03-22 | b24ea119f8b86d8ab7c680ec23047f56 |
| pato.obo.gz | releases/2019-09-05 | 443de10a418cba2b0a6f4a9c3b73c60c |
| psi-mod.obo.gz | - | 921a87531252fbb49b73c92e0b201ab2 |
| psi-ms.obo.gz | 4.1.84 | ace0024e6845eec1d375b6e81a3e90e0 |
| unimod_tables.xml.gz | - | 523d0bb41eeb41bb1554fa405915e310 |
| unit.obo.gz | releases/2020-03-10 | 4e45267605698d1fcda533c27853a8fc |

### Added
1. Added an option to test if the environment variable `PSIMS_NO_PYNUMPRESS` to prevent loading the `pynumpress`
   C extension library.


## [v0.1.46] - 2022-03-02

### CV Versions
| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2022-02-23 | a397dc95d8d809acea44209818a0f77f |
| go.obo.gz | releases/2022-01-13 | 122d68f6cf380a8cbb1abb4a74624416 |
| pato.obo.gz | releases/2019-09-05 | 443de10a418cba2b0a6f4a9c3b73c60c |
| psi-mod.obo.gz | - | 921a87531252fbb49b73c92e0b201ab2 |
| psi-ms.obo.gz | 4.1.72 | 593ed9190e0d657b0eb249efc9a12e77 |
| unimod_tables.xml.gz | - | 61ac665064dd806b536c609fcb775920 |
| unit.obo.gz | releases/2020-03-10 | 4e45267605698d1fcda533c27853a8fc |

### Changed
1. Properly use non-standard array `cvParam`, setting the `value` to the custom array name. Still also sets
   a `userParam`.

## [v0.1.45]

### CV Versions
| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 6e4b70ba06653e2944a7f4e73e30a42b |
| gno.obo.gz | 2021-08-13 | a0365da4060e84703aaec8baeae753d0 |
| go.obo.gz | releases/2021-11-16 | 1cc9921ed933b2de6231cdfa4a0acdf6 |
| pato.obo.gz | releases/2019-09-05 | 443de10a418cba2b0a6f4a9c3b73c60c |
| psi-mod.obo.gz | - | 0f6779b432281c47de1f6879262e394d |
| psi-ms.obo.gz | 4.1.64 | 162f1ab5e81bacd9bfce95088d1f4967 |
| unimod_tables.xml.gz | - | 61ac665064dd806b536c609fcb775920 |
| unit.obo.gz | releases/2020-03-10 | 4e45267605698d1fcda533c27853a8fc |


## [v0.1.44] - 2021-12-04

### CV Versions
| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 6e4b70ba06653e2944a7f4e73e30a42b |
| gno.obo.gz | 2021-08-13 | a0365da4060e84703aaec8baeae753d0 |
| go.obo.gz | releases/2021-11-16 | 1cc9921ed933b2de6231cdfa4a0acdf6 |
| pato.obo.gz | releases/2019-09-05 | 443de10a418cba2b0a6f4a9c3b73c60c |
| psi-mod.obo.gz | - | 0f6779b432281c47de1f6879262e394d |
| psi-ms.obo.gz | 4.1.64 | 162f1ab5e81bacd9bfce95088d1f4967 |
| unimod_tables.xml.gz | - | 61ac665064dd806b536c609fcb775920 |
| unit.obo.gz | releases/2020-03-10 | 4e45267605698d1fcda533c27853a8fc |

### Added
- Improved documentation of HDF5 compressors


## [v0.1.43] - 2021-08-06

### Added
1. Properly coerce negative numbers

### Fixed
1. Restored support for Py3.5

## [v0.1.42] - 2021-08-05

### Fixed
1. Made CV-param binding safe to use for Py2 again.

## [v0.1.41] - 2021-08-05

### Added
1. Re-wrote the `Entity.value_type` machinery to better take into account
   compound or vocabulary-defined types.
2. Modified the `Relationship` type to be able to dispatch to sub-classes for named
   relationship types.

### Changed
1. Updated vendor controlled vocabularies.

## [v0.1.39] - 2021-06-27

### Added
1. The data model for representing entities in OBO was revised to cover a wider range of cases.
2. `Entity` attributes are automatically type-coerced if their primitive types are recognizable. This
   does not apply to formula-like attributes as these are formatted in a controlled vocabulary-specific
   manner.

### Changed
1. Updated vendor controlled vocabularies.

### Deprecated

### Removed

### Fixed

### Security


## [v0.1.38] - 2021-05-24

### Changed
1. Updated vendor controlled vocabularies
2. Extended mzML writer's list of known arrays to match `psi-ms.obo` v4.1.53's new list
3. Added additional warnings for when users have `h5py` but not `hdf5plugin`


## [v0.1.37]

### Added
1. Added additional in-memory buffering of data arrays to reduce round-trips to HDF5 file when writing mzMLb.

### Changed
1. The `MzIdentMLTranslater` class was renamed `MzIdentMLTranslator` for the sake of the English language.
2. Overhauled large parts of the documentation.
3. Added clearer error message when attempting to use the mzMLb components without `h5py`.

### Deprecated

### Removed

### Fixed
1. Made the README mzML example actually work.
2. Allowed `Mapping` types to be used for `other_arrays` array names so that units may be specified. Previously, only
   hashable types were supported, though this was not the intent. Also corrected the documentation to indicate this
   expects a `list` of (name, array) pairs, not a `Mapping` of them.

### Security

## [v0.1.35]

### Added
1. Added a change log.
2. Added a `mzMLb` writer implementation.

### Changed
1. Improved write performance when writing `indexedMzML` by supporting `io.BufferedWriter`
   wrapping the whole write stack.
2. Vendored controlled vocabularies are now gzip-compressed so they use much less space on disk.

### Deprecated

### Removed

### Fixed

### Security

---

## [Released]

---

<!-- Links -->
[Keep a Changelog]: https://keepachangelog.com/
[Semantic Versioning]: https://semver.org/

<!-- Versions -->
[Unreleased]: https://github.com/mobiusklein/psims/compare/v1.1.0...HEAD
[Released]: https://github.com/mobiusklein/psims/releases
[v1.1.0]: https://github.com/mobiusklein/psims/releases/v1.1.0
[v1.0.0]: https://github.com/mobiusklein/psims/releases/v1.0.0
[v0.1.47]: https://github.com/mobiusklein/psims/releases/v0.1.47
[v0.1.46]: https://github.com/mobiusklein/psims/releases/v0.1.46
[v0.1.44]: https://github.com/mobiusklein/psims/releases/v0.1.44
[v0.1.43]: https://github.com/mobiusklein/psims/releases/v0.1.43
[v0.1.42]: https://github.com/mobiusklein/psims/releases/v0.1.42
[v0.1.41]: https://github.com/mobiusklein/psims/releases/v0.1.41
[v0.1.40]: https://github.com/mobiusklein/psims/releases/v0.1.40
[v0.1.39]: https://github.com/mobiusklein/psims/releases/v0.1.39
[v0.1.38]: https://github.com/mobiusklein/psims/releases/v0.1.38
[v0.1.37]: https://github.com/mobiusklein/psims/releases/v0.1.37
[v0.1.35]: https://github.com/mobiusklein/psims/releases/v0.1.35
[v0.1.34]: https://github.com/mobiusklein/psims/releases/v0.1.34