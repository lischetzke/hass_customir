"""Seed the bundled catalog with a small set of well-known devices.

This is a one-off script kept in-tree so the starter catalog can be regenerated
deterministically. Devices included:

* ``lg_tv_akb`` — LG TV (NEC ext, address 0xFB04) — built from
  ``infrared_protocols.codes.lg.tv``.
* ``lg_webos_55lb700v`` — LG webOS TV 55LB700V-ZG (2014, AKB73975701-style
  remote). Same NEC ext address 0xFB04 with the richer webOS button set.
* ``nedis_vmat3462at`` — Nedis HDMI switch — built from
  ``infrared_protocols.codes.nedis.vmat3462at``.
* ``sony_tv_sirc12`` — generic Sony TV using SIRC 12-bit (address 0x01).
* ``samsung_tv_samsung32`` — generic Samsung TV (Samsung32, address 0x07).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from encoders import encode_necext, encode_samsung32, encode_sirc  # noqa: E402
from infrared_protocols.codes.lg.tv import LGTVCode, make_command as make_lg_tv  # noqa: E402
from infrared_protocols.codes.nedis.vmat3462at import (  # noqa: E402
    NedisVMAT3462ATCode,
    make_command as make_nedis,
)

DEVICES_DIR = REPO_ROOT / "custom_components" / "hass_customir" / "catalog" / "devices"
DEVICES_DIR.mkdir(parents=True, exist_ok=True)


def _dump(device: dict) -> None:
    path = DEVICES_DIR / f"{device['key']}.json"
    payload = {
        "key": device["key"],
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model"),
        "type": device.get("type"),
        "source": device.get("source", {}),
        "commands": dict(sorted(device["commands"].items())),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(REPO_ROOT)}  ({len(device['commands'])} cmds)")


# --- LG TV -----------------------------------------------------------------
lg_commands: dict[str, dict] = {}
for code in LGTVCode:
    cmd = make_lg_tv(code)
    lg_commands[code.name.lower()] = {
        "modulation": cmd.modulation,
        "repeat_count": 0,
        "timings": cmd.get_raw_timings(),
    }
_dump(
    {
        "key": "lg_tv_akb",
        "manufacturer": "LG",
        "model": "AKB-series TV remote",
        "type": "tv",
        "source": {"db": "infrared_protocols", "module": "codes.lg.tv"},
        "commands": lg_commands,
    }
)

# --- LG webOS TV 55LB700V-ZG (2014) ---------------------------------------
# Same wire-level encoding as ``lg_tv_akb`` (LG NEC ext, address 0xFB04) but
# with the richer button set of the webOS-era AKB73975701 remote: extra
# webOS-specific keys (Smart Home, Q.Menu, T.OPT, AV Mode, AD, Simplink,
# coloured fast-keys, etc.).
LG_WEBOS_CMDS: dict[str, int] = {
    # Power
    "power": 0x08,
    "power_on": 0xC4,
    "power_off": 0xC5,
    # Volume / channel / source
    "volume_up": 0x02,
    "volume_down": 0x03,
    "mute": 0x09,
    "channel_up": 0x00,
    "channel_down": 0x01,
    "input": 0x0B,
    # HDMI direct-select
    "hdmi_1": 0xCE,
    "hdmi_2": 0xCC,
    "hdmi_3": 0xE9,
    "hdmi_4": 0xDA,
    # D-pad
    "nav_up": 0x40,
    "nav_down": 0x41,
    "nav_left": 0x07,
    "nav_right": 0x06,
    "ok": 0x44,
    "back": 0x28,
    "exit": 0x5B,
    "home": 0x7C,            # Smart Home
    # Information / guide / menus
    "info": 0xAA,
    "guide": 0xA9,
    "menu": 0x43,
    "q_menu": 0x45,
    "settings": 0x43,        # alias of menu on this remote
    "list": 0x53,            # channel list
    "q_view": 0x1A,          # flashback / last channel
    # Numerics
    "num_0": 0x10,
    "num_1": 0x11,
    "num_2": 0x12,
    "num_3": 0x13,
    "num_4": 0x14,
    "num_5": 0x15,
    "num_6": 0x16,
    "num_7": 0x17,
    "num_8": 0x18,
    "num_9": 0x19,
    # Coloured fast keys
    "red": 0x72,
    "green": 0x71,
    "yellow": 0x63,
    "blue": 0x61,
    # Media transport
    "play": 0xB0,
    "pause": 0xBA,
    "stop": 0xB1,
    "rewind": 0x8F,
    "fast_forward": 0x8E,
    "record": 0xBD,
    # webOS / TV-specific extras
    "subtitle": 0x39,
    "t_opt": 0x21,           # teletext options
    "av_mode": 0x30,
    "ratio": 0x79,           # aspect ratio
    "sleep": 0x0E,
    "energy_saving": 0x95,
    "ad": 0x91,              # audio description
    "simplink": 0x7E,
    "live_tv": 0xD1,
    "mark": 0x9F,
}
lg_webos_commands: dict[str, dict] = {
    name: {
        "modulation": 38000,
        "repeat_count": 0,
        "timings": encode_necext(address=0xFB04, command=value),
    }
    for name, value in LG_WEBOS_CMDS.items()
}
_dump(
    {
        "key": "lg_webos_55lb700v",
        "manufacturer": "LG",
        "model": "55LB700V-ZG (webOS, AKB73975701)",
        "type": "tv",
        "source": {
            "db": "builtin",
            "spec": "LG NEC ext, address 0xFB04 — webOS AKB73975701 button set",
            "notes": "Codes match the standard LG NEC scan codes. The 55LB700V-ZG also responds to the AN-MR400 Magic Remote over BLE; this device covers IR fallback only.",
        },
        "commands": lg_webos_commands,
    }
)

# --- Nedis VMAT3462AT HDMI switch -----------------------------------------
nedis_commands: dict[str, dict] = {}
for code in NedisVMAT3462ATCode:
    cmd = make_nedis(code)
    nedis_commands[code.name.lower()] = {
        "modulation": cmd.modulation,
        "repeat_count": 0,
        "timings": cmd.get_raw_timings(),
    }
_dump(
    {
        "key": "nedis_vmat3462at",
        "manufacturer": "Nedis",
        "model": "VMAT3462AT",
        "type": "hdmi_switch",
        "source": {"db": "infrared_protocols", "module": "codes.nedis.vmat3462at"},
        "commands": nedis_commands,
    }
)

# --- Sony TV (SIRC 12-bit, address 0x01) ----------------------------------
SONY_TV_CMDS = {
    "power": 0x15,
    "volume_up": 0x12,
    "volume_down": 0x13,
    "mute": 0x14,
    "channel_up": 0x10,
    "channel_down": 0x11,
    "input": 0x25,
    "num_0": 0x09,
    "num_1": 0x00,
    "num_2": 0x01,
    "num_3": 0x02,
    "num_4": 0x03,
    "num_5": 0x04,
    "num_6": 0x05,
    "num_7": 0x06,
    "num_8": 0x07,
    "num_9": 0x08,
}
sony_commands: dict[str, dict] = {
    name: {
        "modulation": 40000,
        "repeat_count": 2,  # Sony repeats each frame 3x by spec
        "timings": encode_sirc(address=0x01, command=value, bits=12),
    }
    for name, value in SONY_TV_CMDS.items()
}
_dump(
    {
        "key": "sony_tv_sirc12",
        "manufacturer": "Sony",
        "model": "Generic SIRC-12 TV",
        "type": "tv",
        "source": {"db": "builtin", "spec": "Sony SIRC 12-bit, addr 0x01"},
        "commands": sony_commands,
    }
)

# --- Samsung TV (Samsung32, address 0x07) ---------------------------------
SAMSUNG_TV_CMDS = {
    "power": 0x02,
    "volume_up": 0x07,
    "volume_down": 0x0B,
    "mute": 0x0F,
    "channel_up": 0x12,
    "channel_down": 0x10,
    "source": 0x01,
    "menu": 0x1A,
    "exit": 0x2D,
    "ok": 0x68,
    "up": 0x60,
    "down": 0x61,
    "left": 0x65,
    "right": 0x62,
    "num_0": 0x11,
    "num_1": 0x04,
    "num_2": 0x05,
    "num_3": 0x06,
    "num_4": 0x08,
    "num_5": 0x09,
    "num_6": 0x0A,
    "num_7": 0x0C,
    "num_8": 0x0D,
    "num_9": 0x0E,
}
samsung_commands: dict[str, dict] = {
    name: {
        "modulation": 38000,
        "repeat_count": 0,
        "timings": encode_samsung32(address=0x07, command=value),
    }
    for name, value in SAMSUNG_TV_CMDS.items()
}
_dump(
    {
        "key": "samsung_tv_samsung32",
        "manufacturer": "Samsung",
        "model": "Generic Samsung32 TV",
        "type": "tv",
        "source": {"db": "builtin", "spec": "Samsung32, addr 0x07"},
        "commands": samsung_commands,
    }
)
