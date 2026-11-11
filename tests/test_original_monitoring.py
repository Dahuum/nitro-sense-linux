"""Original monitoring/power interaction contracts, with no hardware writes."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from datetime import datetime
import unittest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from nitro_sense.original_monitoring import OriginalMonitoringWidget, OriginalPowerWidget


class FakeBackend:
    def __init__(self): self.calls = []; self.fail = False
    def set_power_profile(self, value):
        self.calls.append(value)
        if self.fail: raise RuntimeError('Denied by OS')


def snapshot():
    return {'temperatures': [{'name': 'k10temp / Tctl', 'celsius': 52.5}],
            'cpu_usage_percent': 12,
            'gpu': {'temperature_c': 45, 'utilization_percent': 18},
            'ac_online': True,
            'power': {'available': True, 'active': 'balanced',
                      'profiles': ['power-saver', 'balanced', 'performance']}}


class MonitoringParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])
    def setUp(self):
        self.widget = OriginalMonitoringWidget(); self.widget.show(); self.app.processEvents()
    def tearDown(self):
        self.widget.close(); self.widget.deleteLater(); self.app.processEvents()

    def test_original_chart_geometry_and_display_channels(self):
        self.widget.update_state(snapshot())
        self.assertEqual(self.widget.size().toTuple(), (840, 312))
        self.assertEqual(self.widget.cpu_graph.geometry().getRect(), (0, 40, 720, 100))
        self.assertEqual(self.widget.gpu_graph.geometry().getRect(), (0, 172, 720, 100))
        self.assertEqual(self.widget.labels['CPU']['temperature'].text(), '52.5°')
        self.assertEqual(self.widget.labels['GPU']['usage'].text(), '18')

    def test_samples_are_right_aligned_bounded_and_hover_has_timestamp(self):
        stamp = datetime(2026, 11, 11, 12, 34, 56)
        self.widget.update_state(snapshot(), timestamp=stamp)
        graph = self.widget.cpu_graph
        self.assertIsNone(graph.sample_at(718))
        self.assertEqual(graph.sample_at(719).time, stamp)
        QTest.mouseMove(graph, QPoint(719, 50)); self.app.processEvents()
        self.assertEqual(graph.hover_index, 719)
        self.assertTrue(graph.popup.isVisible())
        self.assertEqual(graph.popup.sample.time.strftime('%H:%M:%S'), '12:34:56')
        QApplication.sendEvent(graph, QEvent(QEvent.Type.Leave))
        self.assertFalse(graph.popup.isVisible())
        for _ in range(725): self.widget.update_state(snapshot(), timestamp=stamp)
        self.assertEqual(len(graph.samples), 720)
        self.assertIsNotNone(graph.sample_at(0))

    def test_units_relabel_existing_samples_and_keep_physical_history(self):
        self.widget.update_state(snapshot())
        self.widget.set_units('F')
        self.assertEqual(self.widget.labels['CPU']['temperature'].text(), '126°')
        self.assertEqual(self.widget.labels['CPU']['min'].text(), 'Min : 126°')
        self.assertEqual(self.widget.cpu_graph.samples[-1].temperature, 52.5)
        self.widget.set_units('C')
        self.assertEqual(self.widget.labels['CPU']['temperature'].text(), '52.5°')

    def test_missing_readings_remain_unavailable_and_clear_resets_history(self):
        self.widget.update_state(snapshot())
        data = snapshot(); data['gpu'] = None; data['cpu_usage_percent'] = None
        self.widget.update_state(data)
        self.assertEqual(self.widget.labels['GPU']['temperature'].text(), '--°')
        self.assertEqual(self.widget.labels['CPU']['usage'].text(), '--')
        self.widget.clear()
        self.assertFalse(self.widget.cpu_graph.samples)
        self.assertEqual(self.widget.labels['CPU']['min'].text(), 'Min : --°')

    def test_exact_acer_sensor_is_preferred_over_generic_cpu(self):
        data = snapshot(); data['temperatures'].append({'name':'acer / temp1_input','celsius':50})
        self.widget.update_state(data)
        self.assertEqual(self.widget.labels['CPU']['temperature'].text(), '50°')


class PowerParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])
    def setUp(self):
        self.backend = FakeBackend(); self.widget = OriginalPowerWidget(self.backend)
        self.widget.show(); self.widget.update_state(snapshot()); self.app.processEvents()
    def tearDown(self):
        self.widget.close(); self.widget.deleteLater(); self.app.processEvents()

    def test_snapshot_and_tab_selection_never_change_power(self):
        self.assertEqual(self.backend.calls, [])
        QTest.mouseClick(self.widget.tabs[1], Qt.MouseButton.LeftButton)
        self.assertEqual(self.backend.calls, [])
        self.assertTrue(all(not b.isEnabled() for b in self.widget.choices))
        QTest.mouseClick(self.widget.tabs[0], Qt.MouseButton.LeftButton)
        self.assertTrue(all(b.isEnabled() for b in self.widget.choices))

    def test_explicit_choice_dispatches_and_failed_change_restores_selection(self):
        QTest.mouseClick(self.widget.choices[2], Qt.MouseButton.LeftButton)
        self.assertEqual(self.backend.calls, ['performance'])
        self.assertTrue(self.widget.choices[2].isChecked())
        self.backend.fail = True; failures = []; self.widget.operationFailed.connect(failures.append)
        QTest.mouseClick(self.widget.choices[0], Qt.MouseButton.LeftButton)
        self.assertEqual(failures, ['Denied by OS'])
        self.assertTrue(self.widget.choices[2].isChecked())

    def test_unknown_power_source_or_unadvertised_profile_cannot_write(self):
        data = snapshot(); data['ac_online'] = None
        self.widget.update_state(data)
        self.assertTrue(all(not b.isEnabled() for b in self.widget.choices))
        data['ac_online'] = True; data['power']['profiles'] = ['balanced']
        self.widget.update_state(data)
        self.assertFalse(self.widget.choices[0].isEnabled())
        self.assertTrue(self.widget.choices[1].isEnabled())

    def test_acer_optimized_variant_is_visible_but_has_no_fake_linux_mapping(self):
        widget = OriginalPowerWidget(self.backend, acer_mode=True)
        widget.update_state(snapshot())
        self.assertEqual(len(widget.choices), 4)
        self.assertEqual(widget.choices[2].text(), 'Acer Optimized')
        self.assertFalse(widget.choices[2].isEnabled())
        widget.deleteLater()


if __name__ == '__main__': unittest.main()
