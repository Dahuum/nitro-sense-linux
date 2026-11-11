import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nitro_sense.backend import Backend


class FeatureBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sys = self.root / 'sys'
        self.base = self.sys / 'devices/platform/acer-wmi'
        self.put('sys/class/dmi/id/product_name', 'Nitro AN515-45')
        self.put('sys/class/dmi/id/sys_vendor', 'Acer')
        (self.sys / 'module/linuwu_sense').mkdir(parents=True)
        self.put('sys/devices/platform/acer-wmi/nitro_sense/fan_speed', '0,0\n')
        self.dynamic = self.put('sys/devices/platform/acer-wmi/four_zoned_kb/four_zone_mode', '0,0,100,0,0,0,0\n')
        self.zones = self.put('sys/devices/platform/acer-wmi/four_zoned_kb/per_zone_mode', 'ff0000,00ff00,0000ff,ffffff,100\n')
        self.backend = Backend(self.sys, allow_control=True, proc_root=self.root / 'proc')

    def put(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def test_lighting_state_and_normalized_dynamic_request(self):
        self.assertTrue(self.backend.snapshot()['lighting_available'])
        self.assertEqual(self.backend.snapshot()['lighting']['zones']['colors'][0], '#FF0000')
        result = self.backend.set_lighting_dynamic(3, speed=5, brightness=50, direction=2, color='#abcdef')
        self.assertEqual(self.dynamic.read_text(), '3,5,50,2,0,0,0\n')
        self.assertFalse(result['verified_visible'])
        self.backend.set_lighting_dynamic(1, speed=9, direction=2, color='#abcdef')
        self.assertEqual(self.dynamic.read_text(), '1,9,100,0,171,205,239\n')

    def test_invalid_lighting_inputs_never_write(self):
        baseline = self.dynamic.read_text()
        for kwargs in ({'mode': 3}, {'mode': 4, 'direction': 0}, {'mode': 6},
                       {'mode': 0, 'speed': 10}, {'mode': True}, {'mode': 0, 'color': '#12345G'},
                       {'mode': 0, 'brightness': -1}):
            with self.assertRaises(ValueError):
                self.backend.set_lighting_dynamic(**kwargs)
        self.assertEqual(self.dynamic.read_text(), baseline)
        for colors in ([], ['ffffff'] * 3, ['invalid'] * 4, '123456'):
            with self.assertRaises(ValueError):
                self.backend.set_lighting_static(colors)

    def test_exact_four_zone_payload_and_control_gate(self):
        result = self.backend.set_lighting_static(['#ff0000', '00ff00', '0000ff', 'ffffff'], 50)
        self.assertEqual(self.zones.read_text(), 'FF0000,00FF00,0000FF,FFFFFF,50\n')
        self.assertFalse(result['verified_visible'])
        self.backend.allow_control = False
        with self.assertRaises(RuntimeError):
            self.backend.set_lighting_static(['000000'] * 4)

    def test_unknown_switch_is_not_changed_and_usb_is_not_boolean(self):
        path = self.put('sys/devices/platform/acer-wmi/nitro_sense/backlight_timeout', '-1\n')
        self.assertFalse(self.backend.snapshot()['switches']['backlight_timeout']['available'])
        with self.assertRaises(RuntimeError):
            self.backend.set_switch('backlight_timeout', 0)
        self.assertEqual(path.read_text(), '-1\n')
        usb = self.put('sys/devices/platform/acer-wmi/nitro_sense/usb_charging', '30\n')
        with self.assertRaises(ValueError):
            self.backend.set_switch('usb_charging', True)
        with self.assertRaises(ValueError):
            self.backend.set_switch('usb_charging', 1)
        self.backend.set_switch('usb_charging', 20)
        self.assertEqual(usb.read_text(), '20\n')
        with self.assertRaises(ValueError):
            self.backend.set_switch('battery_calibration', 1)

    def test_coolboost_requires_known_state_and_verifies_readback(self):
        path = self.put('sys/devices/platform/acer-wmi/nitro_sense/coolboost', '0\n')
        self.assertTrue(self.backend.snapshot()['capabilities']['coolboost'])
        result = self.backend.set_coolboost(True)
        self.assertEqual(path.read_text(), '1\n')
        self.assertEqual(result['readback'], 1)
        path.write_text('-1\n')
        self.assertFalse(self.backend.snapshot()['capabilities']['coolboost'])
        with self.assertRaises(RuntimeError):
            self.backend.set_coolboost(False)
        with self.assertRaises(ValueError):
            self.backend.set_coolboost(1)

    def test_cpu_delta_and_memory_units(self):
        stat = self.put('proc/stat', 'cpu 100 0 100 800 0 0 0 0\n')
        self.put('proc/meminfo', 'MemTotal: 1000 kB\nMemAvailable: 400 kB\n')
        a = self.backend.snapshot()
        self.assertIsNone(a['cpu_usage_percent'])
        self.assertEqual(a['memory']['total_bytes'], 1024000)
        self.assertEqual(a['memory']['used_bytes'], 614400)
        stat.write_text('cpu 150 0 150 900 0 0 0 0\n')
        self.assertEqual(self.backend.snapshot()['cpu_usage_percent'], 50)

    def test_power_profiles_use_argument_arrays_and_readback(self):
        state = {'profile': 'balanced'}
        commands = []
        def runner(args):
            commands.append(args)
            if args == ['powerprofilesctl', 'get']:
                return state['profile']
            if args == ['powerprofilesctl', 'list']:
                return '* balanced:\n  performance:\n  power-saver:\n'
            if args[:2] == ['powerprofilesctl', 'set']:
                state['profile'] = args[2]
                return ''
            raise FileNotFoundError()
        b = Backend(self.sys, allow_control=True, runner=runner, proc_root=self.root / 'proc')
        self.assertTrue(b.snapshot()['power']['available'])
        b.set_power_profile('power-saver')
        self.assertEqual(state['profile'], 'power-saver')
        with self.assertRaises(ValueError):
            b.set_power_profile('balanced; rm -rf /')
        self.assertIn(['powerprofilesctl', 'set', 'power-saver'], commands)

    def test_command_timeouts_produce_unavailable_capability(self):
        def runner(args):
            raise subprocess.TimeoutExpired(args, 2)
        b = Backend(self.sys, allow_control=True, runner=runner)
        state = b.snapshot()
        self.assertFalse(state['power']['available'])
        self.assertIsNone(state['gpu'])

    def test_failed_fan_restore_remains_armed_for_close_retry(self):
        real_write = Path.write_text
        path = self.base / 'nitro_sense/fan_speed'
        def fail_write(p, value, *args, **kwargs):
            if p == path:
                raise OSError('device transaction failed')
            return real_write(p, value, *args, **kwargs)
        with patch.object(Path, 'write_text', fail_write):
            with self.assertRaisesRegex(RuntimeError, 'restoration also failed'):
                self.backend.set_fans(80, 80)
            self.assertTrue(self.backend._owns_fans)
        path.write_text('80,80\n')
        self.backend.close()
        self.assertEqual(path.read_text(), '0,0\n')


if __name__ == '__main__':
    unittest.main()
