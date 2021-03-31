# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog][Keep a Changelog] and this project adheres to [Semantic Versioning][Semantic Versioning].

## [Unreleased]

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
[Unreleased]: https://github.com/mobiusklein/psims/compare/v0.1.34...HEAD
[Released]: https://github.com/mobiusklein/psims/releases
[v0.1.34]: https://github.com/mobiusklein/psims/releases/v0.1.34