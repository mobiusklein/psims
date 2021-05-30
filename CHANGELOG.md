# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog][Keep a Changelog] and this project adheres to [Semantic Versioning][Semantic Versioning].

## [Unreleased]

### Added

### Changed

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
[Unreleased]: https://github.com/mobiusklein/psims/compare/v0.1.38...HEAD
[Released]: https://github.com/mobiusklein/psims/releases
[v0.1.37]: https://github.com/mobiusklein/psims/releases/v0.1.38
[v0.1.37]: https://github.com/mobiusklein/psims/releases/v0.1.37
[v0.1.35]: https://github.com/mobiusklein/psims/releases/v0.1.35
[v0.1.34]: https://github.com/mobiusklein/psims/releases/v0.1.34