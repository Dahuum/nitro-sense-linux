"""Native interaction tests with a fake backend; no device writes."""
import csv
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ['NITRO_SENSE_ASSETS'] = 'none'
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool
from PySide6.QtTest import QTest
from nitro_sense.profiles import DEFAULT_PROFILE, ProfileStore
from nitro_sense.ui import LightingDialog, NitroWindow, SettingsDialog, FanArt, PaletteDialog, BASIC_COLORS, RECENT_COLORS


class FakeBackend:
    def __init__(self):self.calls=[];self.request={'cpu':0,'gpu':0}
    def snapshot(self):
        return {'model':'Nitro AN515-45','fan_control_available':True,'lighting_available':True,
                'temperatures':[{'name':'k10temp / Tctl','celsius':52.5}],
                'fans':[{'name':'acer / fan1_input','rpm':3125},{'name':'acer / fan2_input','rpm':3703}],
                'fan_request':dict(self.request),'capabilities':{'coolboost':False},
                'reason':'Ready','power':{'available':True,'profiles':['balanced'],'active':'balanced'},
                'gpu':{'name':'GPU','temperature_c':45.0,'utilization_percent':8.0},'cpu_usage_percent':12.0}
    def set_fans(self,cpu,gpu):self.calls.append(('fans',cpu,gpu));self.request={'cpu':cpu,'gpu':gpu}
    def set_lighting_static(self,*args):self.calls.append(('static',)+args)
    def set_lighting_dynamic(self,*args):self.calls.append(('dynamic',)+args)
    def close(self):self.calls.append(('close',))


class NativeUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.backend=FakeBackend();self.window=NitroWindow(self.backend,ProfileStore(Path(self.temp.name)))
        self.window.show();QTest.qWait(50);self.window.timer.stop()
        self.window.pool.waitForDone(1000);self.app.processEvents()
    def tearDown(self):
        self.window._quitting=True;self.window.close();self.window.deleteLater();self.app.processEvents()
    def test_opening_ui_reads_but_does_not_change_hardware(self):
        self.assertEqual(self.backend.calls,[])
        self.assertEqual(self.window.fan_values[0].text(),'3125')
        self.assertFalse(self.window.coolboost.isEnabled())
        self.assertTrue(self.window.mode_buttons[1].isEnabled())
    def test_explicit_max_and_auto_call_backend(self):
        self.window.change_fans(1);self.window.change_fans(0)
        self.assertEqual(self.backend.calls,[('fans',100,100),('fans',0,0)])
    def test_static_zone_controls_apply_selected_brightness_and_disabled_zone(self):
        dialog=LightingDialog(self.backend,self.backend.snapshot(),DEFAULT_PROFILE['lighting'],self.window)
        dialog.zone_colors=['FF0000','00FF00','0000FF','FFFFFF'];dialog.zone_enabled[2].setChecked(False)
        dialog.static_brightness.setValue(50);dialog.apply()
        self.assertEqual(self.backend.calls[-1],('static',['FF0000','00FF00','000000','FFFFFF'],50))
        self.assertIn('accepted',dialog.result_label.text())
        dialog.deleteLater()
    def test_dynamic_controls_have_model_specific_enablement_and_wire_id(self):
        dialog=LightingDialog(self.backend,self.backend.snapshot(),DEFAULT_PROFILE['lighting'],self.window)
        dialog.tabs.setCurrentIndex(1);dialog.pattern.setCurrentIndex(dialog.pattern.findData(3))
        self.assertFalse(dialog.color_button.isEnabled());self.assertTrue(dialog.direction.isEnabled())
        dialog.dynamic_speed.setValue(7);dialog.direction.setCurrentIndex(dialog.direction.findData(2));dialog.apply()
        self.assertEqual(self.backend.calls[-1],('dynamic',3,7,100,2,'FF0000'))
        dialog.deleteLater()
    def test_csv_export_preserves_measured_values(self):
        target=str(Path(self.temp.name)/'history.csv')
        with patch('nitro_sense.ui.QFileDialog.getSaveFileName',return_value=(target,'')):
            self.window.export_history()
        with open(target,newline='') as stream:rows=list(csv.DictReader(stream))
        self.assertEqual(rows[0]['sensor'],'CPU');self.assertEqual(float(rows[0]['value']),52.5)
        self.assertEqual(rows[0]['unit'],'C')
        self.window.clear_history();self.assertFalse(self.window.history);self.assertFalse(self.window.chart.samples)
    def test_fahrenheit_has_converted_readings_and_unit_identity(self):
        self.window.store.preferences['temperature_unit']='F';self.window.chart.clear()
        self.window.apply_state(self.backend.snapshot())
        row=self.window.history[-1]
        self.assertEqual(row['unit'],'F')
        self.assertAlmostEqual(row['readings']['CPU'],126.5)
        self.assertEqual(self.window.chart.units,'°F')
    def test_invalid_profile_never_reaches_fan_backend(self):
        dialog=SettingsDialog(self.window)
        bad=dict(DEFAULT_PROFILE);bad['lighting']=dict(DEFAULT_PROFILE['lighting'],type='dynamic',mode=7)
        dialog.profiles.clear();dialog.profiles.addItem('Invalid',bad)
        with patch('nitro_sense.ui.error') as report:
            dialog.apply_profile()
        report.assert_called_once()
        self.assertEqual(self.backend.calls,[])
        dialog.deleteLater()
    def test_inline_custom_controls_are_explicit_and_independent(self):
        self.window.change_fans(2)
        self.assertEqual(self.backend.calls,[])
        self.assertTrue(self.window.inline_fans[0]['panel'].isVisible())
        cpu,gpu=self.window.inline_fans
        cpu['auto'].setChecked(False);cpu['slider'].setValue(61)
        self.assertFalse(gpu['slider'].isEnabled())
        self.window.apply_inline_fans()
        self.assertEqual(self.backend.calls,[('fans',61,0)])
        self.window.change_fans(0)
        self.assertFalse(self.window.inline_fans[0]['panel'].isVisible())
    def test_fan_animation_uses_measured_rpm_and_stops_when_missing(self):
        fan=FanArt();fan.set_rpm(3000);fan.advance()
        self.assertGreater(fan.angle,0);self.assertTrue(fan.animation.isActive())
        angle=fan.angle;fan.set_rpm(0);fan.advance()
        self.assertEqual(fan.angle,angle);self.assertFalse(fan.animation.isActive())
        fan.set_rpm(None);fan.advance();self.assertEqual(fan.angle,angle)
        fan.deleteLater()
    def test_recovered_basic_palette_and_recent_selection(self):
        self.assertEqual(BASIC_COLORS,('FF0000','FFA000','FFFF00','00FF00','00AEC7','001EFF','FF00FF','AA00FF','FFFFFF'))
        RECENT_COLORS.clear();dialog=PaletteDialog('FF0000')
        dialog.select_color('00AEC7')
        self.assertEqual(dialog.color,'00AEC7');self.assertEqual(RECENT_COLORS[0],'00AEC7')
        self.assertEqual(self.backend.calls,[]);dialog.deleteLater();RECENT_COLORS.clear()
    def test_unavailable_controls_remain_disabled_without_false_success(self):
        state=self.backend.snapshot();state['fan_control_available']=False;state['lighting_available']=False
        self.window.apply_state(state)
        self.assertFalse(self.window.mode_buttons[1].isEnabled())
        dialog=LightingDialog(self.backend,state,DEFAULT_PROFILE['lighting'],self.window)
        self.assertFalse(dialog.apply_button.isEnabled());dialog.deleteLater()


if __name__=='__main__':unittest.main()
