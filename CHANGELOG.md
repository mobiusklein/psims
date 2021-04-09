# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog][Keep a Changelog] and this project adheres to [Semantic Versioning][Semantic Versioning].

## [Unreleased]

### Added
1. Added additional in-memory buffering of data arrays to reduce round-trips to HDF5 file when writing mzMLb.

### Changed
1. The `MzIdentMLTranslater` class was renamed `MzIdentMLTranslator` for the sake of the English language.

### Deprecated

### Removed

### Fixed

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
[Unreleased]: https://github.com/mobiusklein/psims/compare/v0.1.35...HEAD
[Released]: https://github.com/mobiusklein/psims/releases
[v0.1.35]: https://github.com/mobiusklein/psims/releases/v0.1.35
[v0.1.34]: https://github.com/mobiusklein/psims/releases/v0.1.34