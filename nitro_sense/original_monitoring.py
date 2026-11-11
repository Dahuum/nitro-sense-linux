"""Native reconstruction of the shipped 2021 monitoring and power panels.

Geometry and interaction findings are recorded in docs/parity-monitoring.md.
The widgets read snapshots; only an explicit power choice invokes the backend.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
import math
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, Signal, QSignalBlocker
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QAbstractButton, QButtonGroup, QLabel, QWidget

TEMPERATURE = QColor('#e60000')
USAGE = QColor('#ff7800')
MUTED = QColor('#808080')


def _number(value, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    if low is not None and value < low or high is not None and value > high:
        return None
    return float(value)


def _format(value):
    return '--' if value is None else f'{value:.1f}'.rstrip('0').rstrip('.')


def _temperature(value, units):
    if value is None:
        return None
    # The original displays integer Fahrenheit after conversion.
    return int(value * 9 / 5 + 32) if units == 'F' else value


@dataclass(frozen=True)
class Sample:
    time: datetime
    temperature: float | None
    usage: float | None


class ChartPopup(QWidget):
    """84x64 three-line popup positioned ten/fifteen pixels after the cursor."""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedSize(84, 64)
        self.sample = None
        self.units = 'C'

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        shape = QPainterPath()
        shape.moveTo(0, 0); shape.lineTo(12, 4); shape.lineTo(83, 4)
        shape.lineTo(83, 51); shape.lineTo(72, 63); shape.lineTo(4, 63)
        shape.lineTo(4, 12); shape.closeSubpath()
        gradient = QLinearGradient(0, 0, 0, 64)
        gradient.setColorAt(0, QColor('#333333')); gradient.setColorAt(1, QColor('#1e1e1e'))
        p.fillPath(shape, gradient)
        font = QFont('Segoe UI'); font.setPixelSize(14); p.setFont(font)
        if self.sample:
            values = [(self.sample.time.strftime('%H:%M:%S'), MUTED),
                      (_format(_temperature(self.sample.temperature, self.units)) + '°', TEMPERATURE),
                      (_format(self.sample.usage) + '%', USAGE)]
            for y, (text, color) in zip((8, 25, 42), values):
                p.setPen(color); p.drawText(QRectF(10, y, 71, 17), Qt.AlignmentFlag.AlignLeft, text)


class OriginalChart(QWidget):
    """720 samples, one horizontal pixel per sample, with original hover semantics."""
    def __init__(self, parent=None, assets=None):
        super().__init__(parent)
        self.setFixedSize(720, 100)
        self.setMouseTracking(True)
        self.samples = deque(maxlen=720)
        self.units = 'C'
        self.hover_index = None
        self.popup = ChartPopup(self)
        self.background = QPixmap(str(Path(assets) / 'images/100/img_monitor_chart.png')) if assets else QPixmap()

    def append(self, sample):
        self.samples.append(sample)
        self.update()

    def clear(self):
        self.samples.clear(); self.hover_index = None; self.popup.hide(); self.update()

    def closeEvent(self, event):
        self.popup.hide()
        super().closeEvent(event)

    def sample_at(self, x):
        index = int(x) - (720 - len(self.samples))
        if not 0 <= index < len(self.samples):
            return None
        sample = self.samples[index]
        return sample if sample.temperature is not None else None

    def mouseMoveEvent(self, event):
        x = max(0, min(719, int(event.position().x())))
        sample = self.sample_at(x)
        if sample is None or x == 0:
            self.hover_index = None; self.popup.hide(); self.update(); return
        self.hover_index = x
        self.popup.sample = sample; self.popup.units = self.units
        self.popup.move(self.mapToGlobal(event.position().toPoint()) + QPoint(10, 15))
        self.popup.show(); self.popup.update(); self.update()

    def leaveEvent(self, event):
        self.hover_index = None; self.popup.hide(); self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        if not self.background.isNull():
            p.drawPixmap(self.rect(), self.background)
        else:
            p.fillRect(self.rect(), QColor('#101010'))
            p.setPen(QPen(QColor('#242424'), 1))
            for x in range(0, 720, 20): p.drawLine(x, 0, x, 99)
            for y in range(0, 100, 20): p.drawLine(0, y, 719, y)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        left = 720 - len(self.samples)
        for field, color in [('temperature', TEMPERATURE), ('usage', USAGE)]:
            # Original graph scaling stays Celsius/percent 0..100. Fahrenheit
            # conversion affects labels and popup, not the plotted physical scale.
            points = []
            for index, sample in enumerate(self.samples):
                value = getattr(sample, field)
                if value is not None:
                    points.append(QPointF(left + index, 101 - min(100, max(0, value))))
                elif points:
                    self._draw_series(p, points, color); points = []
            if points: self._draw_series(p, points, color)
        if self.hover_index is not None:
            p.setPen(QPen(QColor('#999999'), 1))
            p.drawLine(self.hover_index, 0, self.hover_index, 99)

    @staticmethod
    def _draw_series(painter, points, color):
        if len(points) >= 2:
            fill = QColor(color); fill.setAlphaF(.15)
            polygon = QPolygonF([QPointF(points[0].x(), 100), *points, QPointF(points[-1].x(), 100)])
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(fill); painter.drawPolygon(polygon)
            painter.setPen(QPen(color, 1)); painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(QPolygonF(points))


class OriginalMonitoringWidget(QWidget):
    """840x312 right monitoring section, positioned at shell coordinate396,404."""
    def __init__(self, parent=None, assets=None):
        super().__init__(parent)
        self.setFixedSize(840, 312)
        self.setStyleSheet('background:transparent;')
        self.units = 'C'
        self.cpu_graph = OriginalChart(self, assets)
        self.cpu_graph.move(0, 40)
        self.gpu_graph = OriginalChart(self, assets)
        self.gpu_graph.move(0, 172)
        self.graphs = {'CPU': self.cpu_graph, 'GPU': self.gpu_graph}
        self.unit_label = self._label('Temperature (°C) / Loading (%)', 0, 6, 560, 29, 14)
        self.unit_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self.labels = {}
        self.limits = {'CPU': [None, None], 'GPU': [None, None]}
        for name, top, min_y in [('CPU', 40, 6), ('GPU', 172, 140)]:
            title = self._label(name, 10, top + 10, 220, 26, 16, '#ffffff')
            minimum = self._label('Min : --°', 578, min_y, 71, 29, 12)
            maximum = self._label('Max : --°', 649, min_y, 71, 29, 12)
            for label in (minimum, maximum):label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
            temperature = self._label('--°', 735, top + 29, 105, 34, 28, '#e60000')
            usage = self._label('--', 735, top + 68, 78, 32, 28, '#ff7800')
            self._label('%', 812, top + 78, 28, 22, 18, '#ff7800')
            self.labels[name] = {'title': title, 'min': minimum, 'max': maximum, 'temperature': temperature, 'usage': usage}
        self.last_state = {}

    def _label(self, text, x, y, width, height, size, color='#808080'):
        label = QLabel(text, self)
        label.setGeometry(x, y, width, height)
        label.setStyleSheet(f'background:transparent;color:{color};font:{size}px "Segoe UI";')
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        return label

    @staticmethod
    def _cpu_temperature(state):
        readings = state.get('temperatures', [])
        for needle in ('acer / temp1_input', 'k10temp / Tctl', 'coretemp / Package id 0'):
            for reading in readings:
                if reading.get('name') == needle:
                    return _number(reading.get('celsius'), -50, 150)
        return None

    def set_units(self, units):
        if units not in ('C', 'F'):raise ValueError('Temperature unit must be C or F.')
        self.units = units
        self.unit_label.setText(f'Temperature (°{units}) / Loading (%)')
        for graph in self.graphs.values():graph.units = units; graph.update()
        self._update_labels(self.last_state)

    def update_state(self, snapshot, timestamp=None, append=True):
        timestamp = timestamp or datetime.now()
        self.last_state = snapshot
        gpu = snapshot.get('gpu') or {}
        data = {'CPU': (self._cpu_temperature(snapshot), _number(snapshot.get('cpu_usage_percent'), 0, 100)),
                'GPU': (_number(gpu.get('temperature_c'), -50, 150), _number(gpu.get('utilization_percent'), 0, 100))}
        for name, (temperature, usage) in data.items():
            if append:self.graphs[name].append(Sample(timestamp, temperature, usage))
            if temperature is not None:
                low, high = self.limits[name]
                self.limits[name] = [temperature if low is None else min(low, temperature), temperature if high is None else max(high, temperature)]
        self._update_labels(snapshot)

    def _update_labels(self, snapshot):
        gpu = snapshot.get('gpu') or {}
        values = {'CPU': (self._cpu_temperature(snapshot), _number(snapshot.get('cpu_usage_percent'), 0, 100)),
                  'GPU': (_number(gpu.get('temperature_c'), -50, 150), _number(gpu.get('utilization_percent'), 0, 100))}
        for name, (temperature, usage) in values.items():
            labels = self.labels[name]
            labels['temperature'].setText(_format(_temperature(temperature, self.units)) + '°')
            labels['usage'].setText(_format(usage))
            low, high = self.limits[name]
            labels['min'].setText('Min : ' + _format(_temperature(low, self.units)) + '°')
            labels['max'].setText('Max : ' + _format(_temperature(high, self.units)) + '°')
        gpu_title = gpu.get('label') or 'GPU'
        self.labels['GPU']['title'].setText(gpu_title)

    def clear(self):
        for graph in self.graphs.values():graph.clear()
        self.limits = {'CPU': [None, None], 'GPU': [None, None]}
        self._update_labels(self.last_state)


class PowerTab(QAbstractButton):
    def __init__(self, text, parent=None):
        super().__init__(parent); self.setText(text); self.setCheckable(True); self.setFixedSize(120, 32)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        background = '#333333' if self.isChecked() else '#282828' if self.underMouse() else '#1e1e1e'
        path = QPainterPath(); path.moveTo(0, 12); path.lineTo(12, 0); path.lineTo(108, 0); path.lineTo(120, 12); path.lineTo(120, 32); path.lineTo(0, 32); path.closeSubpath()
        p.fillPath(path, QColor(background)); p.setPen(QColor('#ffffff' if self.isChecked() else '#999999'))
        font = QFont('Segoe UI'); font.setPixelSize(14); p.setFont(font); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
        if self.hasFocus():p.setPen(QPen(QColor('#e60000'), 1)); p.drawLine(12, 29, 108, 29)


class PowerChoice(QAbstractButton):
    def __init__(self, text, kind, parent=None):
        super().__init__(parent); self.setText(text); self.kind = kind; self.setCheckable(True)
        self.setFixedSize(257, 56); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor('#e60000' if self.isChecked() else '#b2b2b2' if self.underMouse() and self.isEnabled() else '#4c4c4c')
        if not self.isEnabled():color = QColor('#3d3d3d')
        p.setPen(QPen(color, 3)); p.setBrush(Qt.BrushStyle.NoBrush)
        # Independent speed/energy drawing in the recovered icon's32x36 box.
        p.drawArc(QRectF(26, 11, 32, 32), 35 * 16, 110 * 16)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(color)
        bolt = QPolygonF([QPointF(40, 18), QPointF(34, 32), QPointF(41, 32), QPointF(38, 44), QPointF(51, 27), QPointF(44, 27), QPointF(47, 18)])
        p.drawPolygon(bolt); p.setPen(color); font = QFont('Segoe UI'); font.setPixelSize(15); p.setFont(font)
        p.drawText(QRectF(64, 0, 190, 56), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text())
        if self.hasFocus():p.setPen(QPen(color, 1, Qt.PenStyle.DotLine)); p.drawRect(self.rect().adjusted(2, 2, -3, -3))


class OriginalPowerWidget(QWidget):
    """Original AC/Battery arrangement with honest Linux profile capability gates."""
    powerChanged = Signal(str)
    operationFailed = Signal(str)
    def __init__(self, backend, parent=None, acer_mode=False):
        super().__init__(parent); self.backend = backend; self.acer_mode = acer_mode
        self.setFixedSize(312, 312); self.setStyleSheet('background:transparent;')
        self.state = {}; self.ac_online = None
        self.mode_label = QLabel('Mode', self); self.mode_label.setGeometry(41, 6, 219, 29)
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self.mode_label.setStyleSheet('color:#808080;font:14px "Segoe UI";background:transparent;')
        self.tab_group = QButtonGroup(self)
        self.tabs = []
        for index, text in enumerate(('AC', 'Battery')):
            button = PowerTab(text, self); button.move(26 + index * 120, 42)
            self.tab_group.addButton(button, index); self.tabs.append(button)
        self.tabs[0].setChecked(True)
        self.tab_group.idClicked.connect(self._tab_changed)
        self.choice_group = QButtonGroup(self)
        self.choices = []
        options = [('Power Saver', 'power-saver'), ('Balance', 'balanced')]
        if acer_mode:options.append(('Acer Optimized', None))
        options.append(('High-Performance', 'performance'))
        for index, (text, profile) in enumerate(options):
            button = PowerChoice(text, profile, self); button.move(18, (80 if not acer_mode else 78) + index * (72 if not acer_mode else 55))
            self.choice_group.addButton(button, index); self.choices.append(button)
            button.clicked.connect(lambda checked=False, value=profile: self._choose(value))
        self._apply_capabilities()

    def update_state(self, snapshot):
        self.state = snapshot
        online = snapshot.get('ac_online')
        if type(online) is not bool:online = None
        if online is not self.ac_online and online is not None:
            with QSignalBlocker(self.tab_group):self.tabs[0 if online else 1].setChecked(True)
        self.ac_online = online
        self._apply_capabilities()

    def _tab_changed(self, index):
        self._apply_capabilities()

    def _apply_capabilities(self):
        power = self.state.get('power') or {}
        active_tab = self.tab_group.checkedId()
        source_matches = self.ac_online is not None and active_tab == (0 if self.ac_online else 1)
        for button in self.choices:
            available = bool(power.get('available') and source_matches and button.kind in power.get('profiles', []))
            button.setEnabled(available)
            with QSignalBlocker(button):button.setChecked(button.kind is not None and button.kind == power.get('active'))
            button.setToolTip('Linux Power Profiles Daemon controls the current active power source.' if available else
                              'Acer Optimized has no verified Linux equivalent.' if button.kind is None else
                              'Select the currently connected power source to change its active Linux profile.' if not source_matches else
                              power.get('reason', 'Power profile unavailable.'))

    def _choose(self, profile):
        choice = next((button for button in self.choices if button.kind == profile), None)
        if choice is None or not choice.isEnabled():return
        try:
            self.backend.set_power_profile(profile)
        except Exception as error:
            self.operationFailed.emit(str(error)); self._apply_capabilities()
        else:
            self.state = dict(self.state, power=dict(self.state.get('power', {}), active=profile))
            self._apply_capabilities(); self.powerChanged.emit(profile)
