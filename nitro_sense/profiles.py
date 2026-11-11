"""Versioned, validated user profiles. Importing a profile never changes hardware."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re

DEFAULT_PROFILE = {'version': 1, 'name': 'Default', 'fan': {'cpu': 0, 'gpu': 0},
                   'lighting': {'type': 'static', 'colors': ['FF0000'] * 4,
                                'brightness': 100, 'mode': 1, 'speed': 5,
                                'direction': 1, 'color': 'FF0000'}}


def validate_profile(value):
    if not isinstance(value, dict) or type(value.get('version')) is not int or value.get('version') != 1:
        raise ValueError('Expected a version 1 NitroSense profile')
    name = value.get('name')
    if not isinstance(name, str) or not name.strip() or len(name) > 80:
        raise ValueError('Profile name must contain 1–80 characters')
    fan = value.get('fan', {})
    lighting = value.get('lighting', {})
    if not isinstance(fan, dict) or not isinstance(lighting, dict):
        raise ValueError('Fan and lighting settings must be objects')
    def integer(container, key, low, high):
        val = container.get(key)
        if type(val) is not int or not low <= val <= high:
            raise ValueError(f'{key} must be an integer from {low} to {high}')
        return val
    def color(val):
        if not isinstance(val, str) or not re.fullmatch(r'[0-9a-fA-F]{6}', val):
            raise ValueError('Colors must be six hexadecimal digits')
        return val.upper()
    colors = lighting.get('colors')
    if not isinstance(colors, list) or len(colors) != 4:
        raise ValueError('Four zone colors are required')
    kind = lighting.get('type')
    if kind not in ('static', 'dynamic'):
        raise ValueError('Lighting type must be static or dynamic')
    mode = integer(lighting, 'mode', 0, 5)
    direction = integer(lighting, 'direction', 0, 2)
    if kind == 'dynamic' and mode == 0:
        raise ValueError('Dynamic lighting requires an effect from 1 to 5')
    if kind == 'dynamic' and mode in (3, 4) and direction not in (1, 2):
        raise ValueError('Wave and Shifting require direction 1 or 2')
    enabled = lighting.get('zone_enabled', [isinstance(v, str) and v.upper() != '000000' for v in colors])
    if not isinstance(enabled, list) or len(enabled) != 4 or any(type(v) is not bool for v in enabled):
        raise ValueError('Four boolean zone enabled states are required')
    effects = lighting.get('effect_settings', {})
    if not isinstance(effects, dict) or len(effects) > 5:
        raise ValueError('Effect settings must contain at most five effects')
    normalized_effects = {}
    for key, settings in effects.items():
        if key not in ('1', '2', '3', '4', '5') or not isinstance(settings, dict):
            raise ValueError('Unsupported saved lighting effect')
        saved_speed = integer(settings, 'speed', 1, 9)
        saved_direction = integer(settings, 'direction', 0, 2)
        if key in ('3', '4') and saved_direction not in (1, 2):
            raise ValueError('Wave and Shifting require direction 1 or 2')
        normalized_effects[key] = {'speed': saved_speed, 'direction': saved_direction}
    return {'version': 1, 'name': name.strip(),
            'fan': {k: integer(fan, k, 0, 100) for k in ('cpu', 'gpu')},
            'lighting': {'type': kind, 'colors': [color(v) for v in colors], 'zone_enabled': enabled, 'effect_settings': normalized_effects,
                         'brightness': integer(lighting, 'brightness', 0, 100),
                         'mode': mode,
                         'speed': integer(lighting, 'speed', 0, 9),
                         'direction': direction,
                         'color': color(lighting.get('color'))}}


class ProfileStore:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'nitro-sense-linux'
        self.path = self.directory / 'profiles.json'
        self.profiles = [validate_profile(DEFAULT_PROFILE)]
        self.preferences = {'minimize_to_tray': False, 'temperature_unit': 'C'}
        self.error = None
        try:
            if self.path.exists():
                if self.path.stat().st_size > 1024 * 1024:
                    raise ValueError('Profile database is too large')
                data = json.loads(self.path.read_text())
                if not isinstance(data, dict):
                    raise ValueError('Profile database must be an object')
                values = data.get('profiles', [])
                if not isinstance(values, list) or len(values) > 100:
                    raise ValueError('Expected at most 100 profiles')
                self.profiles = [validate_profile(v) for v in values] or self.profiles
                prefs = data.get('preferences', {})
                if not isinstance(prefs, dict):
                    raise ValueError('Preferences must be an object')
                if type(prefs.get('minimize_to_tray')) is bool:
                    self.preferences['minimize_to_tray'] = prefs['minimize_to_tray']
                if prefs.get('temperature_unit') in ('C', 'F'):
                    self.preferences['temperature_unit'] = prefs['temperature_unit']
                recent = prefs.get('recent_colors', [])
                if not isinstance(recent, list) or len(recent) > 9 or any(not isinstance(c, str) or not re.fullmatch(r'[0-9a-fA-F]{6}', c) for c in recent):
                    raise ValueError('Recent colors must contain at most nine RGB values')
                self.preferences['recent_colors'] = [c.upper() for c in recent]
                custom = prefs.get('original_custom', {})
                if not isinstance(custom, dict):
                    raise ValueError('Original custom fan preferences must be an object')
                validated_custom = {}
                for key in ('cpu', 'gpu'):
                    value = custom.get(key, 50)
                    auto = custom.get(key + '_auto', True)
                    if type(value) is not int or not 0 <= value <= 100 or value % 10 or type(auto) is not bool:
                        raise ValueError('Custom fans require 10% steps and boolean Auto flags')
                    validated_custom[key] = value
                    validated_custom[key + '_auto'] = auto
                self.preferences['original_custom'] = validated_custom
        except (OSError, ValueError, TypeError) as exc:
            self.error = str(exc)

    def save(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'profiles': self.profiles, 'preferences': self.preferences}, indent=2) + '\n')
        temporary.replace(self.path)

    def put(self, value):
        profile = validate_profile(value)
        self.profiles = [v for v in self.profiles if v['name'] != profile['name']]
        self.profiles.append(profile)
        self.save()
        return profile

    def import_file(self, path):
        path = Path(path)
        if path.stat().st_size > 65536:
            raise ValueError('Profile file must be smaller than 64 KiB')
        return self.put(json.loads(path.read_text()))

    def export_file(self, value, path):
        Path(path).write_text(json.dumps(validate_profile(value), indent=2) + '\n')
