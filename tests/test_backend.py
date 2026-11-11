import tempfile
import unittest
from pathlib import Path
from nitro_sense.backend import Backend


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.backend = Backend(self.root)

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
        return path

    def driver(self):
        self.put('class/dmi/id/product_name', 'Nitro AN515-45\n')
        self.put('class/dmi/id/sys_vendor', 'Acer\n')
        (self.root / 'module/linuwu_sense').mkdir(parents=True)
        return self.put('devices/platform/acer-wmi/nitro_sense/fan_speed', '0,0\n')

    def test_missing_hardware_is_unavailable_not_zero(self):
        data = self.backend.snapshot()
        self.assertEqual(data['fans'], [])
        self.assertEqual(data['temperatures'], [])
        self.assertFalse(data['fan_control_available'])
        self.assertFalse(data['lighting_available'])

    def test_real_units_and_zero_rpm_with_sensor_identity(self):
        self.put('class/hwmon/hwmon0/name', 'amdgpu\n')
        self.put('class/hwmon/hwmon0/temp1_input', '47250\n')
        self.put('class/hwmon/hwmon0/temp1_label', 'edge\n')
        self.put('class/hwmon/hwmon0/fan1_input', '0\n')
        self.put('class/hwmon/hwmon0/temp2_input', 'malformed\n')
        data = self.backend.snapshot()
        self.assertEqual(data['temperatures'], [{'name': 'amdgpu / edge', 'celsius': 47.25}])
        self.assertEqual(data['fans'][0]['rpm'], 0)

    def test_control_requires_opt_in_and_exact_model(self):
        path = self.driver()
        with self.assertRaises(RuntimeError):
            self.backend.set_fans(100, 100)
        self.assertEqual(path.read_text(), '0,0\n')
        self.backend.allow_control = True
        self.put('class/dmi/id/product_name', 'Unknown model')
        with self.assertRaises(RuntimeError):
            self.backend.set_fans(100, 100)

    def test_auto_restoration_after_manual_change(self):
        path = self.driver()
        self.backend.allow_control = True
        result = self.backend.set_fans(60, 70)
        self.assertEqual(path.read_text(), '60,70\n')
        self.assertEqual(result['requested_cpu_percent'], 60)
        self.backend.close()
        self.assertEqual(path.read_text(), '0,0\n')

    def test_invalid_requests_never_reach_backend(self):
        path = self.driver()
        self.backend.allow_control = True
        for value in [-1, 101, True, 1.5, '20']:
            with self.assertRaises(ValueError):
                self.backend.set_fans(value, 50)
        self.assertEqual(path.read_text(), '0,0\n')

    def test_ambiguous_interface_is_rejected(self):
        self.driver()
        self.put('devices/platform/unexpected/nitro_sense/fan_speed', '0,0\n')
        self.backend.allow_control = True
        self.assertFalse(self.backend.snapshot()['fan_control_available'])


if __name__ == '__main__':
    unittest.main()
