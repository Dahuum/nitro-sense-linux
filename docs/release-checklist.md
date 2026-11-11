# Release validation

Version 0.1.0 targets the observed AN515-45 and the explicitly documented feature
matrix. A release does not imply complete Acer Windows parity.

- Unit and native Qt interaction tests use fixture hardware, not real writes.
- Default fallback skin must render without extracted Acer files.
- Installation into an isolated environment must launch the console entry point.
- Source archive includes driver source/license/provenance, setup/removal,
  docs, tests and website; no downloaded vendor binaries, artwork, fonts,
  decompiled code, credentials, build tools or machine-specific kernel binary.
- Wheel metadata resolves PySide6 and exposes both native app and artwork importer.
- Source tar and wheel checksums are attached to the GitHub release.
- Hardware tests restore Auto fans and prior lighting/power/device settings.
- GitHub Actions checks and Pages deployment must finish successfully.
- Website download/source/docs links refer to actual published assets.
- Root driver setup is separate from normal-user daily GUI operation.
- Visible lighting and controlled Windows-runtime parity remain open validations.
