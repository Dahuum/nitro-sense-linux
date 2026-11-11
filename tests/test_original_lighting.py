"""Original-overlay contracts exercised without any hardware writes."""
import copy
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from unittest.mock import patch

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from nitro_sense.original_lighting import BASIC_COLORS, OriginalLightingDialog, OriginalColorPicker

PROFILE = {'type':'static', 'colors':['FF0000','00FF00','0000FF','FFFFFF'],
           'brightness':100, 'mode':1, 'speed':5, 'direction':1, 'color':'FF0000'}


class FakeBackend:
    def __init__(self):
        self.calls=[]
    def set_lighting_static(self, *args):
        self.calls.append(('static',)+args)
    def set_lighting_dynamic(self, *args):
        self.calls.append(('dynamic',)+args)


class OriginalLightingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.backend=FakeBackend()
        self.dialog=OriginalLightingDialog(self.backend, {'lighting_available':True}, copy.deepcopy(PROFILE), overlay=False)
        self.dialog.show();self.app.processEvents()
    def tearDown(self):
        self.dialog.palette.close();self.dialog.close();self.dialog.deleteLater();self.app.processEvents()
    def test_original_dimensions_and_no_loading_write(self):
        self.assertEqual((self.dialog.width(),self.dialog.height()),(868,488))
        self.assertEqual(self.backend.calls,[])
        self.assertEqual((self.dialog.palette.width(),self.dialog.palette.height()),(280,140))
        self.assertEqual((self.dialog.brightness.minimum(),self.dialog.brightness.maximum()),(1,5))
        self.assertEqual((self.dialog.speed.minimum(),self.dialog.speed.maximum()),(1,9))
    def test_color_choice_immediately_targets_zone_and_closes_palette(self):
        self.dialog.open_palette(2)
        self.dialog.palette.basic[3].click()
        self.assertEqual(self.backend.calls,[('static',['FF0000','00FF00','00FF00','FFFFFF'],100)])
        self.assertFalse(self.dialog.palette.isVisible())
        self.assertEqual(self.dialog.profile['colors'][2],'00FF00')
    def test_disabled_zone_preserves_color_for_reenable(self):
        self.dialog.zone_switches[1].click()
        self.assertEqual(self.backend.calls[-1],('static',['FF0000','000000','0000FF','FFFFFF'],100))
        self.assertEqual(self.dialog.settings()['colors'][1],'00FF00')
        self.assertFalse(self.dialog.zone_buttons[1].isEnabled())
        self.dialog.zone_switches[1].click()
        self.assertEqual(self.backend.calls[-1],('static',['FF0000','00FF00','0000FF','FFFFFF'],100))
    def test_brightness_steps_and_off_disable_content_without_resetting_it(self):
        self.dialog.brightness.setValue(3)
        self.assertEqual(self.backend.calls[-1][-1],50)
        self.dialog.brightness.setValue(1)
        self.assertEqual(self.backend.calls[-1][-1],0)
        self.assertFalse(self.dialog.zone_switches[0].isEnabled())
        self.assertTrue(self.dialog.brightness.isEnabled())
        self.dialog.brightness.setValue(5)
        self.assertTrue(self.dialog.zone_switches[0].isEnabled())
        self.assertEqual(self.dialog.settings()['colors'],PROFILE['colors'])
    def test_dynamic_modes_direction_ids_and_color_availability(self):
        self.dialog.dynamic_radio.click()
        self.assertEqual(self.backend.calls[-1],('dynamic',1,5,100,0,'FF0000'))
        self.assertFalse(self.dialog.direction_panel.isVisible())
        self.dialog.effect_buttons[3].click()
        self.assertTrue(self.dialog.direction_panel.isVisible())
        self.assertFalse(self.dialog.color_area.isEnabled())
        self.dialog.left_direction.click()
        self.assertEqual(self.backend.calls[-1],('dynamic',3,5,100,2,'FF0000'))
        self.dialog.right_direction.click()
        self.assertEqual(self.backend.calls[-1][4],1)
        self.dialog.effect_buttons[4].click()
        self.assertTrue(self.dialog.color_area.isEnabled())
        self.dialog.effect_buttons[2].click()
        self.assertFalse(self.dialog.direction_panel.isVisible())
        self.assertFalse(self.dialog.color_area.isEnabled())
    def test_slider_drag_defers_write_until_release(self):
        self.dialog.dynamic_radio.click();self.backend.calls.clear()
        self.dialog.speed.setSliderDown(True)
        self.dialog.speed.setValue(7)
        self.assertEqual(self.backend.calls,[])
        self.dialog.speed.setSliderDown(False)
        self.assertEqual(self.backend.calls,[('dynamic',1,7,100,0,'FF0000')])
    def test_custom_recent_color_unique_limit_and_change_signal(self):
        values=[];self.dialog.recentColorsChanged.connect(values.append)
        self.dialog._choose_color('123456',True,dynamic=False)
        self.assertEqual(values,[['123456']])
        self.dialog._choose_color('123456',True,dynamic=False)
        self.dialog._choose_color(BASIC_COLORS[0],True,dynamic=False)
        self.assertEqual(len(values),1)
        for i in range(12):self.dialog._choose_color(f'{i+16:06X}',True,dynamic=False)
        self.assertEqual(len(self.dialog.recent_colors),9)
    def test_unavailable_interface_disables_controls_and_never_writes(self):
        dialog=OriginalLightingDialog(self.backend, {'lighting_available':False}, PROFILE, overlay=False)
        dialog.show();self.app.processEvents()
        self.assertFalse(dialog.dynamic_radio.isEnabled())
        self.assertFalse(dialog.brightness.isEnabled())
        dialog._apply()
        self.assertEqual(self.backend.calls,[])
        dialog.close();dialog.deleteLater()
    def test_failed_device_action_does_not_claim_new_profile(self):
        before=copy.deepcopy(self.dialog.profile)
        with patch.object(self.backend,'set_lighting_static',side_effect=OSError('hardware rejected')):
            with patch('nitro_sense.original_lighting.QMessageBox.critical') as message:
                self.dialog._choose_color('123456',False,dynamic=False)
                message.assert_called_once()
        self.assertEqual(self.dialog.profile,before)
    def test_overlay_mask_and_escape_close(self):
        overlay=OriginalLightingDialog(self.backend, {'lighting_available':True}, PROFILE)
        overlay.show();self.app.processEvents()
        self.assertEqual((overlay.width(),overlay.height()),(1320,760))
        self.assertEqual(overlay.panel.pos(),QPoint(226,136))
        QTest.mouseClick(overlay,Qt.MouseButton.LeftButton,pos=QPoint(10,10))
        self.assertFalse(overlay.isVisible())
        overlay.show();QTest.keyClick(overlay,Qt.Key.Key_Escape)
        self.assertFalse(overlay.isVisible());overlay.deleteLater()
    def test_color_picker_exact_size_rgb_validation_and_cancel(self):
        picker=OriginalColorPicker('123456',self.dialog)
        picker.show();self.app.processEvents()
        self.assertEqual((picker.width(),picker.height()),(480,364))
        self.assertEqual(picker.selected_color(),'123456')
        picker.rgb_fields[0].setText('999');picker._rgb_edited('999')
        self.assertFalse(picker.ok_button.isEnabled())
        picker.rgb_fields[0].setText('255');picker._rgb_edited('255')
        self.assertTrue(picker.ok_button.isEnabled())
        self.assertEqual(picker.selected_color(),'FF3456')
        picker.cancel_button.click();self.assertFalse(picker.isVisible())
        self.assertEqual(self.backend.calls,[]);picker.deleteLater()


if __name__=='__main__':
    unittest.main()
