"""Linux telemetry and validated Linuwu-Sense sysfs controls.

Only the inspected Acer AN515-45 is allowed hardware writes. Commands use explicit
argument arrays and timeouts; driver success is never a claim of visible effects.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
import platform
import re
import subprocess
import threading
import time


class Backend:
    SWITCHES = {'coolboost': (0, 1), 'backlight_timeout': (0, 1), 'battery_limiter': (0, 1),
                'usb_charging': (0, 10, 20, 30)}
    MODES = {0: 'Static', 1: 'Breathing', 2: 'Neon', 3: 'Wave', 4: 'Shifting', 5: 'Zoom'}

    def __init__(self, root: Path = Path('/sys'), *, allow_control: bool = False,
                 proc_root: Path = Path('/proc'), runner=None):
        self.root = Path(root)
        self.proc_root = Path(proc_root)
        self.allow_control = allow_control
        self._lock = threading.RLock()
        self._owns_fans = False
        self._last_cpu = None
        self._runner = runner or self._run
        self._host_commands = runner is not None or self.root == Path('/sys')
        self._command_cache = {}

    @staticmethod
    def _run(args):
        return subprocess.run(args, capture_output=True, text=True, timeout=2, check=True).stdout.strip()

    @staticmethod
    def _read(path: Path, default=None):
        try:
            return path.read_text().strip()
        except (OSError, UnicodeError):
            return default

    @staticmethod
    def _int(value, low, high, name):
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'{name} must be an integer from {low} to {high}.')
        return value

    def _driver_base(self):
        if self._read(self.root / 'class/dmi/id/product_name') != 'Nitro AN515-45':
            return None
        if self._read(self.root / 'class/dmi/id/sys_vendor') != 'Acer':
            return None
        if not (self.root / 'module/linuwu_sense').is_dir():
            return None
        candidates = list((self.root / 'devices/platform').glob('*/nitro_sense/fan_speed'))
        return candidates[0].parent.parent if len(candidates) == 1 else None

    def _fan_path(self):
        base = self._driver_base()
        return base / 'nitro_sense/fan_speed' if base is not None else None

    def _control_path(self, relative):
        base = self._driver_base()
        path = base / relative if base else None
        if not self.allow_control:
            raise RuntimeError('Hardware control is disabled; start with --enable-control.')
        if path is None or not path.is_file() or not os.access(path, os.W_OK):
            raise RuntimeError(f'Compatible writable driver interface is unavailable: {relative}')
        return path

    def _cached_command(self, key, args, lifetime=3):
        if not self._host_commands:
            return None
        now = time.monotonic()
        previous = self._command_cache.get(key)
        if previous and now - previous[0] < lifetime:
            return previous[1]
        try:
            value = self._runner(args)
        except (OSError, subprocess.SubprocessError, ValueError):
            value = None
        self._command_cache[key] = (now, value)
        return value

    def _power(self):
        active = self._cached_command('power-active', ['powerprofilesctl', 'get'])
        listing = self._cached_command('power-list', ['powerprofilesctl', 'list'], 30)
        choices = re.findall(r'^\s*\*?\s*(performance|balanced|power-saver):\s*$', listing or '', re.M)
        usable = active in choices and bool(choices)
        return {'available': self.allow_control and usable, 'profiles': choices if usable else [],
                'active': active if usable else None,
                'reason': ('Power Profiles Daemon available.' if self.allow_control else 'Control is disabled; start with --enable-control.')
                if usable else 'Power Profiles Daemon is unavailable or did not report valid profiles.'}

    def _usage(self):
        cpu = None
        stat = self._read(self.proc_root / 'stat', '')
        try:
            first = stat.splitlines()[0].split()
            if first[0] != 'cpu':
                raise ValueError('CPU counters unavailable')
            values = list(map(int, first[1:]))
            total, idle = sum(values[:8]), sum(values[3:5])
            previous = self._last_cpu
            self._last_cpu = total, idle
            if previous and total > previous[0]:
                cpu = max(0.0, min(100.0, 100 * (1 - (idle - previous[1]) / (total - previous[0]))))
        except (IndexError, ValueError):
            pass
        memory = {'total_bytes': None, 'used_bytes': None, 'percent': None}
        try:
            fields = {line.split(':')[0]: int(line.split()[1]) * 1024
                      for line in self._read(self.proc_root / 'meminfo', '').splitlines()
                      if line.split(':')[0] in ('MemTotal', 'MemAvailable')}
            total = fields['MemTotal']
            available = fields['MemAvailable']
            if total > 0 and 0 <= available <= total:
                memory = {'total_bytes': total, 'used_bytes': total - available,
                          'percent': (total - available) / total * 100}
        except (KeyError, IndexError, ValueError):
            pass
        return cpu, memory

    def _gpu(self):
        raw = self._cached_command('nvidia', ['nvidia-smi',
            '--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total',
            '--format=csv,noheader,nounits'])
        if not raw:
            return None
        try:
            row = next(csv.reader(raw.splitlines()))
            def number(index):
                try:
                    return float(row[index].strip())
                except (ValueError, IndexError):
                    return None
            return {'name': row[0].strip(), 'temperature_c': number(1),
                    'utilization_percent': number(2), 'memory_used_mib': number(3),
                    'memory_total_mib': number(4), 'source': 'nvidia-smi'}
        except (StopIteration, csv.Error, IndexError):
            return None

    def _lighting(self, base):
        result = {'dynamic': None, 'zones': None}
        if base is None:
            return result
        dynamic = self._read(base / 'four_zoned_kb/four_zone_mode')
        zones = self._read(base / 'four_zoned_kb/per_zone_mode')
        try:
            parts = list(map(int, dynamic.split(',')))
            if len(parts) == 7:
                result['dynamic'] = dict(zip(('mode', 'speed', 'brightness', 'direction', 'red', 'green', 'blue'), parts))
        except (AttributeError, ValueError):
            pass
        try:
            parts = zones.split(',')
            if len(parts) == 5 and all(re.fullmatch(r'[0-9a-fA-F]{6}', p) for p in parts[:4]):
                result['zones'] = {'colors': ['#' + p.upper() for p in parts[:4]], 'brightness': int(parts[4])}
        except (AttributeError, ValueError):
            pass
        return result

    def _ac_online(self):
        online = []
        for supply in (self.root / 'class/power_supply').glob('*'):
            if self._read(supply / 'type') in ('Mains', 'USB', 'USB_C'):
                value = self._read(supply / 'online')
                if value in ('0', '1'):
                    online.append(value == '1')
        return any(online) if online else None

    def snapshot(self):
        temperatures, fans = [], []
        for device in sorted((self.root / 'class/hwmon').glob('hwmon*')):
            driver = self._read(device / 'name', device.name)
            for sensor in sorted(device.glob('temp*_input')):
                try:
                    celsius = int(sensor.read_text().strip()) / 1000
                except (OSError, ValueError):
                    continue
                if not -50 <= celsius <= 150:
                    continue
                label = self._read(sensor.with_name(sensor.name.replace('_input', '_label')), sensor.stem)
                temperatures.append({'name': f'{driver} / {label}', 'celsius': celsius})
            for sensor in sorted(device.glob('fan*_input')):
                try:
                    rpm = int(sensor.read_text().strip())
                except (OSError, ValueError):
                    continue
                if rpm < 0:
                    continue
                label = self._read(sensor.with_name(sensor.name.replace('_input', '_label')), sensor.stem)
                fans.append({'name': f'{driver} / {label}', 'rpm': rpm})
        base, path = self._driver_base(), self._fan_path()
        writable = path is not None and os.access(path, os.W_OK)
        enabled = self.allow_control and writable
        reason = ('Fan control ready through Linuwu-Sense.' if enabled else
                  'Fan control requires --enable-control and write access.' if writable else
                  'Compatible Linuwu-Sense control interface is not available or writable.')
        lighting = self._lighting(base)
        lighting_paths = [base / 'four_zoned_kb' / name for name in ('four_zone_mode', 'per_zone_mode')] if base else []
        lighting_enabled = self.allow_control and len(lighting_paths) == 2 and all(p.is_file() and os.access(p, os.W_OK) for p in lighting_paths)
        switches = {}
        for name, choices in self.SWITCHES.items():
            switch_path = base / 'nitro_sense' / name if base else None
            try:
                value = int(self._read(switch_path)) if switch_path else None
            except (TypeError, ValueError):
                value = None
            readable = value in choices
            available = self.allow_control and readable and os.access(switch_path, os.W_OK)
            switches[name] = {'available': bool(available), 'readable': readable, 'value': value if readable else None,
                              'choices': list(choices), 'reason': 'Ready.' if available else
                              'Current hardware state is unknown.' if not readable else 'Control disabled or permission denied.'}
        fan_request = None
        try:
            values = [int(v) for v in self._read(path, '').split(',')] if path else []
            if len(values) == 2 and all(0 <= v <= 100 for v in values):
                fan_request = dict(zip(('cpu', 'gpu'), values))
        except ValueError:
            pass
        cpu, memory = self._usage()
        gpu = self._gpu()
        if gpu and gpu['temperature_c'] is not None:
            temperatures.append({'name': gpu['name'] + ' / discrete GPU', 'celsius': gpu['temperature_c']})
        power = self._power()
        return {'model': self._read(self.root / 'class/dmi/id/product_name', platform.machine()),
                'temperatures': temperatures, 'fans': fans, 'fan_request': fan_request, 'ac_online': self._ac_online(),
                'fan_control_available': enabled, 'lighting_available': lighting_enabled,
                'reason': reason, 'lighting_reason': ('Driver interface available; visible effects require user verification.'
                     if lighting_enabled else 'Compatible writable lighting interfaces are unavailable or control is disabled.'),
                'lighting': lighting, 'switches': switches, 'power': power,
                'cpu_usage_percent': cpu, 'memory': memory, 'gpu': gpu,
                'capabilities': {'fans': enabled, 'lighting': lighting_enabled, 'coolboost': switches['coolboost']['available'],
                                 'power_profiles': power['available'], 'battery_calibration': False},
                'coolboost_reason': switches['coolboost']['reason']}

    def set_fans(self, cpu: int, gpu: int):
        self._int(cpu, 0, 100, 'CPU fan speed')
        self._int(gpu, 0, 100, 'GPU fan speed')
        with self._lock:
            path = self._control_path('nitro_sense/fan_speed')
            # A failed sysfs transaction may have applied an early WMI step.
            # Keep restoration armed until an automatic request succeeds.
            self._owns_fans = True
            try:
                path.write_text(f'{cpu},{gpu}\n')
            except OSError as error:
                try:
                    path.write_text('0,0\n')
                except OSError as restore_error:
                    raise RuntimeError(f'Fan write failed; automatic restoration also failed: {restore_error}') from error
                self._owns_fans = False
                raise RuntimeError('Fan write failed; requested firmware automatic control.') from error
            self._owns_fans = (cpu, gpu) != (0, 0)
            return {'requested_cpu_percent': cpu, 'requested_gpu_percent': gpu}

    @staticmethod
    def _color(value):
        if not isinstance(value, str) or not re.fullmatch(r'#?[0-9a-fA-F]{6}', value):
            raise ValueError('Colors must be six hexadecimal RGB digits, optionally prefixed with #.')
        return value.removeprefix('#').upper()

    def set_lighting_static(self, colors, brightness=100):
        if not isinstance(colors, (list, tuple)) or len(colors) != 4:
            raise ValueError('Exactly four zone colors are required.')
        values = [self._color(v) for v in colors]
        self._int(brightness, 0, 100, 'Brightness')
        payload = ','.join(values + [str(brightness)]) + '\n'
        enable = f'0,0,{brightness},0,0,0,0\n'
        with self._lock:
            self._control_path('four_zoned_kb/per_zone_mode').write_text(payload)
            self._control_path('four_zoned_kb/four_zone_mode').write_text(enable)
        return {'requested_colors': ['#' + c for c in values], 'requested_brightness': brightness,
                'verified_visible': False}

    def set_zone_colors(self, colors, brightness=100):
        return self.set_lighting_static(colors, brightness)

    def set_lighting_dynamic(self, mode, speed=0, brightness=100, direction=0, color='#FF0000'):
        self._int(mode, 0, 5, 'Lighting mode')
        self._int(speed, 0, 9, 'Animation speed')
        self._int(brightness, 0, 100, 'Brightness')
        self._int(direction, 0, 2, 'Direction')
        if mode in (3, 4) and direction == 0:
            raise ValueError('Wave and Shifting require direction 1 or 2.')
        rgb = self._color(color)
        red, green, blue = (int(rgb[i:i+2], 16) for i in (0, 2, 4))
        # Match inspected driver transformations instead of promising ignored parameters.
        if mode == 0:
            speed = 0
        if mode in (0, 1, 2, 5):
            direction = 0
        if mode in (2, 3):
            red = green = blue = 0
        values = (mode, speed, brightness, direction, red, green, blue)
        per_zone_color = rgb if mode not in (2, 3) else '000000'
        per_zone_payload = ','.join([per_zone_color] * 4 + [str(brightness)]) + '\n'
        dynamic_payload = ','.join(map(str, values)) + '\n'
        with self._lock:
            # The backlight is not enabled by the dynamic command alone on this
            # model; set per-zone colors first, then the dynamic mode command.
            self._control_path('four_zoned_kb/per_zone_mode').write_text(per_zone_payload)
            self._control_path('four_zoned_kb/four_zone_mode').write_text(dynamic_payload)
        return {'requested': dict(zip(('mode', 'speed', 'brightness', 'direction', 'red', 'green', 'blue'), values)),
                'verified_visible': False}

    def set_lighting(self, mode, speed=0, brightness=100, direction=0, red=255, green=0, blue=0):
        for name, value in (('Red', red), ('Green', green), ('Blue', blue)):
            self._int(value, 0, 255, name)
        return self.set_lighting_dynamic(mode, speed, brightness, direction, f'#{red:02X}{green:02X}{blue:02X}')

    def set_switch(self, name, value):
        if name not in self.SWITCHES:
            raise ValueError('Unknown hardware setting.')
        if type(value) is bool and name != 'usb_charging':
            value = int(value)
        if type(value) is not int or value not in self.SWITCHES[name]:
            raise ValueError(f'{name} must be one of {self.SWITCHES[name]}.')
        with self._lock:
            path = self._control_path('nitro_sense/' + name)
            current = self._read(path)
            if current not in {str(v) for v in self.SWITCHES[name]}:
                raise RuntimeError('Current hardware state is unknown; setting was not changed.')
            path.write_text(str(value) + '\n')
            readback = self._read(path)
            if readback != str(value):
                raise RuntimeError(f'Driver accepted the request but readback is {readback!r}, not {value}.')
        return {'requested': value, 'readback': value}

    def set_coolboost(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('CoolBoost enabled must be boolean.')
        return self.set_switch('coolboost', enabled)

    def set_power_profile(self, profile):
        with self._lock:
            power = self._power()
            if not power['available']:
                raise RuntimeError(power['reason'])
            if profile not in power['profiles']:
                raise ValueError('Unsupported power profile.')
            try:
                self._runner(['powerprofilesctl', 'set', profile])
                readback = self._runner(['powerprofilesctl', 'get'])
            except (OSError, subprocess.SubprocessError) as error:
                raise RuntimeError(f'Power profile request failed: {error}') from error
            self._command_cache.pop('power-active', None)
            if readback != profile:
                raise RuntimeError(f'Power profile readback differs from request: {readback!r}.')
            return {'requested': profile, 'readback': readback}

    def close(self):
        with self._lock:
            if self._owns_fans:
                path = self._fan_path()
                if path is None:
                    raise RuntimeError('Fan backend disappeared before automatic control could be restored.')
                path.write_text('0,0\n')
                self._owns_fans = False
