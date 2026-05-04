# Custom IR — maintainer tools

These scripts are **not** loaded by Home Assistant. They run on a maintainer's
machine to convert open-source IR databases into the bundled catalog under
`custom_components/hass_customir/catalog/`. The resulting JSON is what the
runtime integration consumes.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate     # or .venv\Scripts\activate on Windows
pip install -r tools/requirements-dev.txt
```

## Encoders supported

| Protocol               | irdb names accepted                | Source                     |
| ---------------------- | ---------------------------------- | -------------------------- |
| NEC1 (8-bit)           | `NEC`, `NEC1`, `NEC2`              | `infrared_protocols.NECCommand` |
| NEC extended (16-bit)  | `NECx1`, `NECx2`, `NECext`         | `infrared_protocols.NECCommand` |
| Philips RC5            | `RC5`                              | `tools/encoders/rc5.py`    |
| Philips RC6 Mode 0     | `RC6`, `RC6-0-16`                  | `tools/encoders/rc6.py`    |
| Sony SIRC 12/15/20-bit | `Sony12`, `Sony15`, `Sony20`       | `tools/encoders/sirc.py`   |
| Samsung 32-bit         | `Samsung`, `Samsung32`, `Samsung36`| `tools/encoders/samsung.py`|
| Pronto hex             | (used by Flipper raw + manual)     | `tools/encoders/pronto.py` |

Anything outside that list is skipped with a logged warning. Add encoders by
implementing `encode_<protocol>(...)` and dispatching from
`tools/encoders/__init__.py`.

## Importing from probonopd/irdb

```bash
git clone https://github.com/probonopd/irdb tools/_irdb
python tools/migrate_irdb.py --src tools/_irdb --manufacturer LG --device-type TV
```

Filters are optional — omit `--manufacturer` / `--device-type` to import
everything (warning: that will produce thousands of devices).

## Importing from Flipper-IRDB

```bash
git clone https://github.com/Lucaslhm/Flipper-IRDB tools/_flipper
python tools/migrate_flipper.py --src tools/_flipper/TVs/LG
```

## Re-validating the catalog

```bash
python tools/validate_catalog.py
```

This re-parses every JSON in `custom_components/hass_customir/catalog/devices/`
against the schema and rebuilds `index.json`. CI should run this on every PR.
