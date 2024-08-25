# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog][Keep a Changelog] and this project adheres to [Semantic Versioning][Semantic Versioning].

## [v1.3.4] - 2024-08-25

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 20422ebfdf25d53d9287eea52f1f925d |
| gno.obo.gz | 2024-05-21 | 5f5db5832b92c6ef3e036e3e80da608f |
| go.obo.gz | releases/2024-06-17 | 7fa7ade5e3e26eab3959a7e4bc89ad4f |
| pato.obo.gz | releases/2024-03-28/pato.obo | 1d9a7fb3423ef79f18f54eea352d09c8 |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.172 | e5defa3b8c03ed1f43a04fd7c8d1819e |
| unimod_tables.xml.gz | - | 50ca5b540cea270e91df3f555483d1e6 |
| unit.obo.gz | releases/2023-05-25 | 5a04e9d871730a1ee04764055e841785 |

### Fixed
- Make XSD value type parsing and formatting separate concepts and properly re-format date-like types

## [v1.3.3] - 2024-01-25

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2023-12-11 | ec47a2eb0af631bca7a40d85a4832ab4 |
| go.obo.gz | releases/2024-01-17 | 7e6b9974184dda306e6e07631f1783af |
| pato.obo.gz | releases/2023-05-18/pato.obo | 8a14f0e3b3318c13d029d84d693a01e3 |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.139 | a7254eb76da9e38c85b9dad624c9f77e |
| unimod_tables.xml.gz | - | efc94f333458012a77203d09a64d7d38 |
| unit.obo.gz | releases/2023-05-25 | 5a04e9d871730a1ee04764055e841785 |

### Changed
1. The `Unimod` object now uses a thread-safe database session abstraction

## [v1.3.2] - 2023-12-02

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2023-11-09 | 078de92750ee4956b705684253a66f97 |
| go.obo.gz | releases/2023-11-15 | 1130d315870d82c1624f87b37305777b |
| pato.obo.gz | releases/2023-05-18/pato.obo | 8a14f0e3b3318c13d029d84d693a01e3 |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.136 | 1d5aa08ea57762000d00a9300734a78c |
| unimod_tables.xml.gz | - | efc94f333458012a77203d09a64d7d38 |
| unit.obo.gz | releases/2023-05-25 | 5a04e9d871730a1ee04764055e841785 |

### Added
1. Add `by_id` method to `Unimod` for parity with `pyteomics`

## [v1.3.1]

### Changed
1. Replaced the global import of `pkg_resources` in `psims.validation.validator` with `importlib.resources`

## [v1.3.0] - 2023-11-03

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2023-08-09 | 6178d787e38a8a1b5d7506e3c1a880d0 |
| go.obo.gz | releases/2023-10-09 | a827a54e43185170c973afe1add92941 |
| pato.obo.gz | releases/2023-05-18/pato.obo | 8a14f0e3b3318c13d029d84d693a01e3 |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.135 | 3f58f845ef728dc3225a5a2df32fff3a |
| unimod_tables.xml.gz | - | efc94f333458012a77203d09a64d7d38 |
| unit.obo.gz | releases/2023-05-25 | 5a04e9d871730a1ee04764055e841785 |

### Changed
1. The default compressor for `mzMLb` has been reverted to zlib/gzip for compatibility with the forthcoming
   ProteoWizard release.
2. The `mzMLb version` attribute is now stored as a fixed-length string in HDF5 (for spec compatibility),
   which `h5py` unilaterally reads as a `bytes` object, requiring the reader to decode it themselves.


## [v1.2.9] - 2023-10-26

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2023-08-09 | 6178d787e38a8a1b5d7506e3c1a880d0 |
| go.obo.gz | releases/2023-10-09 | a827a54e43185170c973afe1add92941 |
| pato.obo.gz | releases/2023-05-18/pato.obo | 8a14f0e3b3318c13d029d84d693a01e3 |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.134 | d3eea6067a44a85dc72fef90acafbfb5 |
| unimod_tables.xml.gz | - | efc94f333458012a77203d09a64d7d38 |
| unit.obo.gz | releases/2023-05-25 | 5a04e9d871730a1ee04764055e841785 |

### Changed
1. The `compression` parameter for mzML and mzMLb `spectrum` and `chromatogram` writing methods may now be a
   `Mapping`-like object mapping array name to compressor name. This supports using Numpress on m/z arrays and
   zlib on intensity arrays, for example, or two different Numpress compressors as the linear compression Numpress
   proposes for m/z isn't appropriate for intensity.
2. The mzMLb writer will now detect when a compressor has occluded the data type of an array and mark that array as
   opaque so that the future reading HDF5 library doesn't try to cast that array to its "real" data type. This leaves
   it up to the caller to properly decode the opaque bytes back into their proper representation.


## [v1.2.8] - 2023-10-13

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2023-08-09 | 6178d787e38a8a1b5d7506e3c1a880d0 |
| go.obo.gz | releases/2023-10-09 | a827a54e43185170c973afe1add92941 |
| pato.obo.gz | releases/2023-05-18/pato.obo | 8a14f0e3b3318c13d029d84d693a01e3 |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.134 | d3eea6067a44a85dc72fef90acafbfb5 |
| unimod_tables.xml.gz | - | efc94f333458012a77203d09a64d7d38 |
| unit.obo.gz | releases/2023-05-25 | 5a04e9d871730a1ee04764055e841785 |

### Changed
1. `load_unimod` now uses the automatic caching and vendored CV fallback mechanism that
   all other `load_*` methods use.


## [v1.2.7] - 2023-08-27

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2023-08-09 | 6178d787e38a8a1b5d7506e3c1a880d0 |
| go.obo.gz | releases/2023-07-27 | 326bc165ad57ee38d87a380098e49ca7 |
| pato.obo.gz | releases/2023-05-18/pato.obo | 8a14f0e3b3318c13d029d84d693a01e3 |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.132 | e5520f1823470c3c05b9eb94b0cdd06b |
| unimod_tables.xml.gz | - | 7e6f1cffe9ad27fecbf5b394103b9836 |
| unit.obo.gz | releases/2023-05-25 | 5a04e9d871730a1ee04764055e841785 |

### Added
1. Added a translation cache to `ControlledVocabulary` objects to avoid repeatedly resolving the same names
   over and over again.


## [v1.2.5] - 2023-05-25

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2023-05-08 | 40808f9d7b3b2589ec272f2d36db80c8 |
| go.obo.gz | releases/2023-05-10 | e9845499eadaef2418f464cd7e9ac92e |
| pato.obo.gz | releases/2023-05-18/pato.obo | 8a14f0e3b3318c13d029d84d693a01e3 |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.121 | 851867a39838c846425fbc96f408506f |
| unimod_tables.xml.gz | - | 7e6f1cffe9ad27fecbf5b394103b9836 |
| unit.obo.gz | releases/2023-05-25 | 5a04e9d871730a1ee04764055e841785 |

### Fixed
1. `Entity` objects now compare as equal if their ids are equal instead of doing a deep comparison.

## [v1.2.4] - 2023-04-30

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2022-12-20 | 2af78cbf0e6256586a5499babe3f59b9 |
| go.obo.gz | releases/2023-04-01 | 299355f7feb050cab4edab556f2e5c7e |
| pato.obo.gz | releases/2023-02-17/pato.obo | 3b9bc35244bbb8e9ba9c4952d80980dd |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.119 | f646e5364d10e6bac37b43e31debe99a |
| unimod_tables.xml.gz | - | 7e6f1cffe9ad27fecbf5b394103b9836 |
| unit.obo.gz | - | c7d0dedfdc0223d42a9cf66ffb03f2a2 |

### Fixed
- The SQLAlchemy dependency should no longer issue deprecation warnings when used with SQLAlchemy v2+.
- More docstrings are formatted properly and cleaned up.

## [v1.2.3] - 2023-01-07

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2022-12-20 | 2af78cbf0e6256586a5499babe3f59b9 |
| go.obo.gz | releases/2023-01-01 | f2a0667c060b688fa4c4afa59f7a783a |
| pato.obo.gz | releases/2022-12-15/pato.obo | 5c67369f32b06e41e9e146d1c768df6d |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.109 | afa2e3eab46c82354615595d8ecedf55 |
| unimod_tables.xml.gz | - | 7e6f1cffe9ad27fecbf5b394103b9836 |
| unit.obo.gz | - | 1616553109ee3ebc85ffc978d8e39ce8 |

## [v1.2.2] - 2022-11-21

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2022-02-23 | a397dc95d8d809acea44209818a0f77f |
| go.obo.gz | releases/2022-11-03 | 704f04eb6308c28cb2139a9803b7da3a |
| pato.obo.gz | releases/2022-11-09/pato.obo | 1b269eb54e4848c56885fa2d66b83b9b |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.108 | 9e5ffabe9c045ad2078f1bcc49a5214e |
| unimod_tables.xml.gz | - | 7e6f1cffe9ad27fecbf5b394103b9836 |
| unit.obo.gz | - | 1616553109ee3ebc85ffc978d8e39ce8 |

### Added
- Added more documentation for mzIdentML writing.
- `MzMLTransformer` now coerces `cvParam` and `userParam` from key-value pairs without requiring `cvstr` instances for keys.

### Changed

### Deprecated

### Removed

### Fixed

### Security


## [v1.2.1]

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2022-02-23 | a397dc95d8d809acea44209818a0f77f |
| go.obo.gz | releases/2022-09-19 | 8f0f6557c8140bc68af67ac57239236d |
| pato.obo.gz | releases/2022-08-31/pato.obo | f84ce80b421e6f693a6e8031a70fe95f |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.104 | 6b5051c9a66b3c15cf0334920099bac1 |
| unimod_tables.xml.gz | - | 523d0bb41eeb41bb1554fa405915e310 |
| unit.obo.gz | - | 1f6e1b5122ea4c2d3797bae72f140ab1 |

### Added
1. Controlled vocabularies fail to resolve, a more descriptive error message will be
   used in the error. If failing to import a CV fails, it is not treated as an error.
2. Wrapped component classes on writer types now expose a `register` method which is
   shorthand for `writer.register("component type name", identifier)`.


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

## [v1.2.6] - 2023-07-15

| Name | Version | Checksum |
|  :---: |  :---: |  :---: |
| XLMOD.obo.gz | release/2019-10-28 | 4e577044551d277e4bbd62753fa15e08 |
| gno.obo.gz | 2023-05-08 | 40808f9d7b3b2589ec272f2d36db80c8 |
| go.obo.gz | releases/2023-06-11 | b4aafb08e95a7c5c5852872e3d4a8959 |
| pato.obo.gz | releases/2023-05-18/pato.obo | 8a14f0e3b3318c13d029d84d693a01e3 |
| psi-mod.obo.gz | - | 713e6dd17632d0388802f1b0e06800f0 |
| psi-ms.obo.gz | 4.1.130 | 693097be4d0d1d16ed1162c4313cb9f5 |
| unimod_tables.xml.gz | - | 7e6f1cffe9ad27fecbf5b394103b9836 |
| unit.obo.gz | releases/2023-05-25 | 5a04e9d871730a1ee04764055e841785 |

### Fixed
1. Actually implement parameter-less version of bound `Component.write()` (GH #20)
2. Actually implement bound `Component.register()` (GH #19)


## [v1.1.0] - 2022-07-07

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
[Unreleased]: https://github.com/mobiusklein/psims/compare/v1.3.4...HEAD
[Released]: https://github.com/mobiusklein/psims/releases
[v1.3.4]: https://github.com/mobiusklein/psims/releases/v1.3.4
[v1.3.3]: https://github.com/mobiusklein/psims/releases/v1.3.3
[v1.3.2]: https://github.com/mobiusklein/psims/releases/v1.3.2
[v1.3.1]: https://github.com/mobiusklein/psims/releases/v1.3.1
[v1.3.0]: https://github.com/mobiusklein/psims/releases/v1.3.0
[v1.2.9]: https://github.com/mobiusklein/psims/releases/v1.2.9
[v1.2.8]: https://github.com/mobiusklein/psims/releases/v1.2.8
[v1.2.7]: https://github.com/mobiusklein/psims/releases/v1.2.7
[v1.2.6]: https://github.com/mobiusklein/psims/releases/v1.2.6
[v1.2.5]: https://github.com/mobiusklein/psims/releases/v1.2.5
[v1.2.4]: https://github.com/mobiusklein/psims/releases/v1.2.4
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