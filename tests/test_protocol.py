import unittest
from nitro_sense.protocol import (
    Pattern, fan_mode, fan_behavior, fan_speed, coolboost, zone_rgb,
    zone_status, dynamic_lighting, service_u64_request,
)


class RecoveredWords(unittest.TestCase):
    def test_original_fan_mode_constants(self):
        self.assertEqual(fan_mode('auto'), 0x410009)
        self.assertEqual(fan_mode('max'), 0x820009)
        self.assertEqual(fan_mode('custom'), 0xC30009)
        self.assertEqual(fan_behavior(True, True), fan_mode('auto'))
        self.assertEqual(fan_behavior(False, False), fan_mode('custom'))
        self.assertEqual(fan_behavior(True, False), 0xC10009)

    def test_separate_behavior_and_speed_selectors(self):
        # GPU behavior uses bit 3, while GPU speed uses bit 2 in original code.
        self.assertEqual(fan_speed('gpu', 100), 0x6404)
        self.assertEqual(fan_speed('cpu', 50), 0x3201)
        self.assertEqual(coolboost(True), 0x10007)
        self.assertEqual(coolboost(False), 7)

    def test_rgb_byte_order_and_zone_masks(self):
        self.assertEqual(zone_rgb(1, 0x12, 0x34, 0x56), 0x56341201)
        self.assertEqual(zone_rgb(4, 0xFF, 0, 0), 0xFF08)
        self.assertEqual(zone_status((True, False, True, False)), 0x050000000008)

    def test_dynamic_effect_selectors_and_noncolor_neon(self):
        word = dynamic_lighting(Pattern.WAVE, 3, 5, 2, 0x12, 0x34, 0x56)
        self.assertEqual(word.to_bytes(8, 'little'), bytes([3, 3, 100, 8, 2, 0x12, 0x34, 0x56]))
        self.assertEqual(dynamic_lighting(Pattern.NEON, 3, 5, 2, 0x12, 0x34, 0x56), 0x640302)
        self.assertEqual(dynamic_lighting(Pattern.BREATHING, 1, 1, 255, 0, 0, 0), 0x101)

    def test_linux_source_formula_agrees_over_valid_domain(self):
        # Independently written arithmetic from Linuwu-Sense fan_val_calc.
        for percentage in range(101):
            for group, selector in [('cpu', 1), ('gpu', 4)]:
                driver_word = (((percentage * 25600) // 100) & 0xFF00) + selector
                self.assertEqual(fan_speed(group, percentage), driver_word)

    def test_original_single_uint64_ipc_frame(self):
        self.assertEqual(service_u64_request(15, fan_mode("auto")),
                         bytes.fromhex("0f0001080000000900410000000000"))

    def test_reject_invalid_inputs(self):
        for percentage in [-1, 101, True, 1.5]:
            with self.assertRaises(ValueError):
                fan_speed('cpu', percentage)
        with self.assertRaises(ValueError):
            zone_rgb(0, 0, 0, 0)
        with self.assertRaises(ValueError):
            dynamic_lighting(Pattern.WAVE, 1, 0, 0, 0, 0, 0)


if __name__ == '__main__':
    unittest.main()
