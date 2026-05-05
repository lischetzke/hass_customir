# Changelog

All notable changes to **Custom IR** are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-05-05

### Added

- **Two-step searchable wizard**: pick the manufacturer first, then the
  model. Both dropdowns use `SelectSelector(mode=DROPDOWN)` so they support
  type-ahead search; splitting by manufacturer keeps the second list short.
  Live counts (devices/manufacturers/commands) are surfaced in the form
  descriptions.
- **Options Flow** with a *Legacy timing pairs (compatibility)* toggle for
  emitter integrations still on the pre-2.0 `infrared-protocols` API.
- **`LegacyRawCommand`** — emits objects exposing `.high_us` / `.low_us`
  (with `__int__` / `__index__` shims) instead of the modern signed-µs
  ints. Mirrors the API removed in
  [home-assistant-libs/infrared-protocols#19](https://github.com/home-assistant-libs/infrared-protocols/pull/19).
- **Automatic legacy fallback**: on the first `AttributeError` mentioning
  `high_us`, the integration logs a warning, persists
  `legacy_timings=True` to the entry's options, and retries with
  `LegacyRawCommand`. Subsequent presses skip straight to the legacy
  shape, so you don't need to flip the toggle yourself.
- **LG webOS TV 55LB700V-ZG** added to the bundled catalog (58 commands —
  the AKB73975701 button set, including SimpLink, Q.Menu, Q.View, AD,
  T.OPT, AV mode, ratio, sleep timer, energy saving, the four colour
  fast-keys, and the rest).
- **Entity name translations** for all 73 catalog command names in both
  `en` and `de` locales (e.g. `volume_up` → "Volume up" / "Lauter").
  Missing keys fall back to the title-cased command name.
- **Project icon** — `icon.svg`, top-level `icon.png` (512×512), and
  per-integration `icon.png` / `icon@2x.png` (256×256 / 512×512). The
  generator script lives at `tools/generate_icon.py` so the icon can be
  regenerated deterministically.
- **README**: wizard walkthrough, expanded *Adding your own device*
  section with a "where to get timings" table (Flipper `.ir`, irdb,
  Pronto, raw captures, NEC/RC5/RC6/SIRC/Samsung32 encoders), and a
  *Troubleshooting* section covering the
  `'int' object has no attribute 'high_us'` error.

### Changed

- `manifest.json` version bumped from `0.1.0` to `0.2.0`.

## [0.1.0] — 2026-05-04

Initial scaffold.

### Added

- Core integration (`button` + `remote` platforms) backed by Home
  Assistant 2026.4's new IR proxy entity platform.
- Catalog loader supporting bundled JSON + user-supplied YAML/JSON files
  in `<config>/customir_devices/`.
- Bundled catalog with four starter devices: LG TV (`lg_tv_akb`),
  Nedis VMAT3462AT HDMI switch, generic Sony SIRC-12 TV, generic
  Samsung32 TV.
- Dev-time migrators for [probonopd/irdb](https://github.com/probonopd/irdb)
  (CSV) and [Lucaslhm/Flipper-IRDB](https://github.com/Lucaslhm/Flipper-IRDB)
  (`.ir`).
- Encoders for NEC1, NEC ext, RC5, RC6 Mode 0, Sony SIRC 12/15/20,
  Samsung 32-bit, and Pronto hex.
- `tools/validate_catalog.py` schema-validates every bundled device
  JSON and rebuilds `index.json`.
- HACS metadata (`hacs.json`) and MIT licence.

[0.2.0]: https://github.com/lischetzke/hass_customir/releases/tag/v0.2.0
[0.1.0]: https://github.com/lischetzke/hass_customir/releases/tag/v0.1.0
