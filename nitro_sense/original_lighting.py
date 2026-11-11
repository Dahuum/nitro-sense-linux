"""Native reconstruction of the 2021 NitroSense lighting overlay.

Geometry/control semantics come from the locally recovered XAML and handlers.
No original vector paths or bitmap payloads are included. Optional local artwork
can be supplied separately. Explicit user actions apply immediately, as the
original does; construction and loading never issue device writes.
"""
from __future__ import annotations

import colorsys
import copy
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal, QSignalBlocker
from PySide6.QtGui import QColor, QImage, QIntValidator, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QAbstractButton, QButtonGroup, QDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QRadioButton, QSlider, QWidget

BASIC_COLORS = ('FF0000', 'FFA000', 'FFFF00', '00FF00', '00AEC7', '001EFF', 'FF00FF', 'AA00FF', 'FFFFFF')
COLOR_NAMES = ('Red', 'Orange', 'Yellow', 'Green', 'Cyan', 'Blue', 'Pink', 'Purple', 'White')
EFFECTS = ((1, 'Breathing'), (3, 'Wave'), (5, 'Zoom'), (4, 'Shifting'), (2, 'Neon'))
PANEL_SIZE = (868, 488)
OVERLAY_SIZE = (1320, 760)

STYLE = '''
QWidget {font-family:"Segoe UI",sans-serif;font-size:16px;color:#808080;background:transparent;}
QRadioButton {spacing:7px;} QRadioButton::indicator {width:26px;height:18px;}
QRadioButton::indicator:unchecked {background:#3e3e3e;border:1px solid #4c4c4c;border-radius:8px;}
QRadioButton::indicator:checked {background:#e60000;border:1px solid #6e0000;border-radius:8px;}
QRadioButton::indicator:hover {border:1px solid #e60000;}
QRadioButton:disabled {color:#424242;}
QPushButton {padding:0;background:transparent;border:1px solid #72706c;color:#dadada;}
QPushButton:hover {border-color:#e60000;} QPushButton:focus {border:1px solid #e60000;}
QPushButton:disabled {color:#444;border-color:#333;}
QSlider::groove:horizontal {height:4px;background:#4c4c4c;}
QSlider::sub-page:horizontal {background:#e60000;}
QSlider::handle:horizontal {width:12px;background:#dadada;border:1px solid #72706c;margin:-6px 0;}
QSlider::handle:horizontal:hover {background:#fff;border-color:#e60000;}
QSlider::handle:horizontal:disabled {background:#555;}
QLineEdit {background:#242424;color:#fff;border:1px solid #72706c;padding:2px;font-size:13px;}
'''


def _hex(value, default='FF0000'):
    value = str(value).removeprefix('#').upper()
    return value if len(value) == 6 and all(c in '0123456789ABCDEF' for c in value) else default


def _label(parent, text, x, y, w, h=24, size=16, color='#808080'):
    label = QLabel(text, parent)
    label.setGeometry(x, y, w, h)
    label.setStyleSheet(f'color:{color};font-size:{size}px;')
    return label


def _polygon(x, y, width, height, cut):
    return QPolygonF([QPointF(x+cut,y), QPointF(x+width-cut,y), QPointF(x+width,y+cut),
        QPointF(x+width,y+height-cut), QPointF(x+width-cut,y+height), QPointF(x+cut,y+height),
        QPointF(x,y+height-cut), QPointF(x,y+cut)])


class OriginalSwitch(QAbstractButton):
    """52×20 hexagonal on/off control from the inspected template dimensions."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(52, 20)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(.4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#6e0000' if self.isChecked() else '#242424'))
        painter.drawPolygon(_polygon(0, 0, 52, 20, 10))
        painter.setBrush(QColor('#e60000' if self.isChecked() else '#4c4c4c'))
        painter.drawPolygon(_polygon(23 if self.isChecked() else 3, 2, 26, 16, 8))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor('#e60000'), 1))
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))


class Swatch(QAbstractButton):
    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self.color = color
        self.setCheckable(True)
        self.setFixedSize(24, 24)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setEnabled(color is not None)
        self.setAccessibleName('Color #' + color if color else 'Empty recent color')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#e60000' if self.isChecked() or self.hasFocus() else '#72706c'), 1))
        p.setBrush(QColor('#' + (self.color or 'B2B2B2')))
        p.drawPolygon(_polygon(2, 2, 20, 20, 4))
        if not self.isEnabled():
            p.fillRect(self.rect(), QColor(21, 21, 21, 130))


class LightingPanel(QWidget):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#72706c'), 1))
        p.setBrush(QColor('#151515'))
        p.drawPolygon(_polygon(4, 4, 860, 480, 20))
        p.setPen(QPen(QColor('#72706c'), 1))
        p.drawLine(320, 8, 548, 8)


def _local_wpf_path(data):
    """Read local WPF M/L/C geometry without executing markup or storing it here."""
    data = data[data.find('M'):]
    tokens = re.findall(r'[MLCZmlcz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', data)
    if len(tokens) > 30000:
        raise ValueError('Local keyboard geometry is too large')
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    command, index = None, 0
    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
            if command.upper() == 'Z':
                path.closeSubpath()
                continue
        count = {'M': 2, 'L': 2, 'C': 6}.get((command or '').upper())
        if count is None or index + count > len(tokens):
            raise ValueError('Unsupported local keyboard path')
        numbers = [float(value) for value in tokens[index:index+count]]
        if not all(math.isfinite(value) and abs(value) < 10000 for value in numbers):
            raise ValueError('Invalid local keyboard coordinate')
        if command.islower():
            origin = path.currentPosition()
            numbers = [value + (origin.x() if n % 2 == 0 else origin.y()) for n,value in enumerate(numbers)]
        if command.upper() == 'M':
            path.moveTo(*numbers)
            command = 'l' if command.islower() else 'L'
        elif command.upper() == 'L':
            path.lineTo(*numbers)
        else:
            path.cubicTo(*numbers)
        index += count
    return path


def _local_keyboard_geometry(source):
    """Optional private geometry: original paths never enter distributed source."""
    if not source:
        return []
    source = Path(source)
    if not source.is_file() or source.stat().st_size > 2*1024*1024:
        return []
    try:
        root = ET.fromstring(source.read_bytes())
        result = []
        for zone in (4, 3, 2, 1):
            node = next(n for n in root.iter() if n.attrib.get('Name') == f'Zone{zone}_color_block')
            path = _local_wpf_path(node.attrib['Data'])
            # Resolve the local Path+Grid margins in the 819.84px source cell.
            margin = [float(v) for v in node.attrib.get('Margin','0,0,0,0').split(',')]
            width = float(node.attrib['Width'])
            if zone == 4:
                x = 819.84 - 37.5 - width
                y = margin[1] - 30
            else:
                desired = width + margin[0] + margin[2]
                extra_left = 100 if zone == 2 else 0
                x = (819.84 - desired - extra_left)/2 + extra_left + margin[0]
                y = margin[1] + (30 if zone == 2 else 0) - 30
            stops = []
            for child in node.iter():
                if child.tag.endswith('GradientStop'):
                    color = child.attrib.get('Color','#FFFF0000')
                    alpha = int(color[1:3],16)/255 if len(color)==9 else 1
                    stops.append((float(child.attrib['Offset']),alpha))
            result.append((zone-1,path,x,y,width,stops))
        return result
    except (ET.ParseError,ValueError,KeyError,StopIteration,IndexError,OSError):
        return []


class OriginalKeyboard(QWidget):
    """Locally drawn ANSI keyboard; optional original chassis bitmap is local only."""
    def __init__(self, parent, assets=None, geometry_xaml=None):
        super().__init__(parent)
        self.geometry = _local_keyboard_geometry(geometry_xaml)
        self.colors = ['FF0000'] * 4
        self.enabled = [True] * 4
        self.dimmed = False
        self.art = QPixmap(str(Path(assets) / 'images/100/img_lighting_zone.png')) if assets else QPixmap()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.dimmed:
            p.setOpacity(.4)
        if self.geometry:
            p.setPen(Qt.PenStyle.NoPen)
            for zone,path,x,y,width,stops in self.geometry:
                p.save()
                p.translate(x,y)
                gradient = QLinearGradient(0,0,width,0)
                for offset,alpha in stops:
                    color = QColor('#'+self.colors[zone]) if self.enabled[zone] else QColor('#303030')
                    color.setAlphaF(alpha)
                    gradient.setColorAt(offset,color)
                p.fillPath(path,gradient)
                p.restore()
            return
        if not self.art.isNull():
            p.drawPixmap(QRectF(0, 0, 816, 228), self.art, QRectF(self.art.rect()))
        else:
            p.setPen(QPen(QColor('#77736f'), 1))
            p.setBrush(QColor('#1b1b1b'))
            p.drawPolygon(_polygon(25, 8, 766, 210, 12))
        # Keyboard rows are independently drawn; Acer's large vector paths are
        # not redistributed. Zone placement follows the recovered four columns.
        rows = (17, 17, 16, 15, 15, 13)
        for row, count in enumerate(rows):
            for key in range(count):
                x = 43 + key * 42 + (row % 3) * 3
                y = 21 + row * 30
                zone = min(3, int((x - 43) / 183))
                color = QColor('#' + self.colors[zone]) if self.enabled[zone] else QColor('#303030')
                p.setPen(QPen(color, 1))
                p.setBrush(QColor('#151515'))
                p.drawRoundedRect(QRectF(x, y, 34, 23), 3, 3)
        p.setPen(QColor('#777'))
        for i, text in enumerate(('esc', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12')):
            p.drawText(QRectF(44+i*42, 23, 32, 18), Qt.AlignmentFlag.AlignCenter, text)


class HslPlane(QWidget):
    selected = Signal(float, float)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(240, 220)
        self.hue = 0.
        self.saturation = 1.
        self.image = QImage(240, 220, QImage.Format.Format_RGB32)
        for x in range(240):
            for y in range(220):
                self.image.setPixelColor(x, y, QColor.fromHslF(x/240, 1-y/219, .5))
        self.setAccessibleName('Hue and saturation color plane')
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        p = QPainter(self)
        p.drawImage(0, 0, self.image)
        p.setPen(QPen(QColor('#000'), 1))
        p.drawRect(QRectF(self.hue*240-4, (1-self.saturation)*219-4, 8, 8))
        p.setPen(QPen(QColor('#fff'), 1))
        p.drawRect(QRectF(self.hue*240-3, (1-self.saturation)*219-3, 6, 6))

    def _pick(self, point):
        self.hue = max(0., min(239., point.x()))/240
        self.saturation = 1-max(0., min(219., point.y()))/219
        self.selected.emit(self.hue, self.saturation)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pick(event.position())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._pick(event.position())

    def keyPressEvent(self, event):
        dx = {Qt.Key.Key_Left:-1, Qt.Key.Key_Right:1}.get(event.key(), 0)
        dy = {Qt.Key.Key_Up:-1, Qt.Key.Key_Down:1}.get(event.key(), 0)
        if dx or dy:
            self._pick(QPointF(self.hue*240+dx, (1-self.saturation)*219+dy))
        else:
            super().keyPressEvent(event)


class OriginalColorPicker(QDialog):
    """480×364 HSL plane + lightness slider + RGB editor, matching source roles."""
    def __init__(self, color, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(480, 364)
        self.setWindowTitle('Color')
        self.setStyleSheet(STYLE + 'QDialog {background:#151515;border:1px solid #72706c;}')
        self.color = QColor('#' + _hex(color))
        self._editing = False
        h, l, s = colorsys.rgb_to_hls(self.color.redF(), self.color.greenF(), self.color.blueF())
        self.hue, self.saturation, self.lightness = h, s, l
        _label(self, 'Color', 45, 23, 240, size=18, color='#fff')
        self.plane = HslPlane(self)
        self.plane.move(45, 61)
        self.plane.hue, self.plane.saturation = h, s
        self.plane.selected.connect(self._plane_changed)
        self.lightness_slider = QSlider(Qt.Orientation.Vertical, self)
        self.lightness_slider.setGeometry(303, 61, 15, 220)
        self.lightness_slider.setRange(0, 219)
        self.lightness_slider.setValue(round(l*219))
        self.lightness_slider.setAccessibleName('Color lightness')
        self.lightness_slider.valueChanged.connect(self._lightness_changed)
        self.preview = QLabel(self)
        self.preview.setGeometry(362, 61, 78, 50)
        self.rgb_fields = []
        for index, (label, value) in enumerate(zip(('R', 'G', 'B'), (self.color.red(), self.color.green(), self.color.blue()))):
            _label(self, label, 361, 199+index*28, 35, size=13, color='#fff')
            field = QLineEdit(str(value), self)
            field.setGeometry(400, 199+index*28, 40, 24)
            field.setValidator(QIntValidator(0, 255, field))
            field.setMaxLength(3)
            field.setAccessibleName({'R':'Red', 'G':'Green', 'B':'Blue'}[label])
            field.textEdited.connect(self._rgb_edited)
            self.rgb_fields.append(field)
        self.ok_button = QPushButton('OK', self)
        self.ok_button.setGeometry(194, 300, 120, 36)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.setGeometry(320, 300, 120, 36)
        self.cancel_button.clicked.connect(self.reject)
        close = QPushButton('×', self)
        close.setGeometry(438, 18, 20, 16)
        close.clicked.connect(self.reject)
        self._update_preview()

    def _update_preview(self):
        self.preview.setStyleSheet('background:' + self.color.name() + ';border:1px solid #72706c;')
        self.plane.hue, self.plane.saturation = self.hue, self.saturation
        self.plane.update()
        self._editing = True
        for field, value in zip(self.rgb_fields, (self.color.red(), self.color.green(), self.color.blue())):
            field.setText(str(value))
        self._editing = False
        self.ok_button.setEnabled(True)

    def _plane_changed(self, hue, saturation):
        self.hue, self.saturation = hue, saturation
        self.color = QColor.fromHslF(hue, saturation, self.lightness)
        self._update_preview()

    def _lightness_changed(self, value):
        self.lightness = value/219
        self.color = QColor.fromHslF(self.hue, self.saturation, self.lightness)
        self._update_preview()

    def _rgb_edited(self, _):
        if self._editing:
            return
        if not all(field.hasAcceptableInput() for field in self.rgb_fields):
            self.ok_button.setEnabled(False)
            return
        self.color = QColor(*(int(field.text()) for field in self.rgb_fields))
        self.hue, self.lightness, self.saturation = colorsys.rgb_to_hls(self.color.redF(), self.color.greenF(), self.color.blueF())
        self.lightness_slider.blockSignals(True)
        self.lightness_slider.setValue(round(self.lightness*219))
        self.lightness_slider.blockSignals(False)
        self.preview.setStyleSheet('background:' + self.color.name() + ';border:1px solid #72706c;')
        self.plane.hue, self.plane.saturation = self.hue, self.saturation
        self.plane.update()
        self.ok_button.setEnabled(True)

    def selected_color(self):
        return self.color.name()[1:].upper()


class ColorPopup(QDialog):
    chosen = Signal(str, bool)
    def __init__(self, recent_colors, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(280, 140)
        self.setStyleSheet('QDialog {background:#dadada;color:#191919;} QLabel {color:#191919;background:transparent;font:14px "Segoe UI";} QPushButton {color:#191919;border:0;background:transparent;text-align:left;font:14px "Segoe UI";}')
        self.recent_colors = recent_colors
        _label(self, 'Basic colors', 24, 5, 240, size=14, color='#191919')
        _label(self, 'Recent colors', 24, 59, 240, size=14, color='#191919')
        self.basic = []
        self.recent = []
        for index, color in enumerate(BASIC_COLORS):
            button = Swatch(color, self)
            button.move(24+index*27, 29)
            button.clicked.connect(lambda checked=False, color=color:self.choose(color))
            self.basic.append(button)
        for index in range(9):
            color = recent_colors[index] if index < len(recent_colors) else None
            button = Swatch(color, self)
            button.move(24+index*27, 83)
            button.clicked.connect(lambda checked=False, button=button:self.choose(button.color))
            self.recent.append(button)
        self.more = QPushButton('More color...', self)
        self.more.setGeometry(24, 108, 244, 32)
        self.more.clicked.connect(self.more_color)
        self.current_color = 'FF0000'

    def choose(self, color):
        self.chosen.emit(color, False)
        self.hide()

    def more_color(self):
        self.hide()
        picker = OriginalColorPicker(self.current_color, self.parentWidget())
        if picker.exec() == QDialog.DialogCode.Accepted:
            self.chosen.emit(picker.selected_color(), True)


class OriginalLightingDialog(QDialog):
    profileChanged = Signal(dict)
    recentColorsChanged = Signal(list)

    def __init__(self, backend, state, profile, parent=None, *, assets=None, recent_colors=None, overlay=True, geometry_xaml=None):
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.backend = backend
        self.profile = copy.deepcopy(profile)
        self.recent_colors = [_hex(color) for color in (recent_colors or [])][:9]
        self.available = bool(state.get('lighting_available'))
        self._ready = False
        self._mode = 'dynamic' if profile.get('type') == 'dynamic' else 'static'
        self._effect = profile.get('mode', 1) if profile.get('mode', 1) in dict(EFFECTS) else 1
        self._direction = profile.get('direction', 1) if profile.get('direction') in (1, 2) else 1
        self._colors = [_hex(color) for color in profile.get('colors', ['FF0000']*4)]
        if len(self._colors) != 4:
            self._colors = ['FF0000']*4
        self._enabled = list(profile.get('zone_enabled', [color!='000000' for color in self._colors]))
        if len(self._enabled) != 4:
            self._enabled = [True]*4
        self._dynamic_color = _hex(profile.get('color', 'FF0000'))
        self._target_zone = 0
        self._effects = copy.deepcopy(profile.get('effect_settings', {}))
        self._effects[str(self._effect)] = {'speed': max(1, min(9, profile.get('speed', 5))), 'direction': self._direction}
        self.overlay = overlay
        self.setFixedSize(*(OVERLAY_SIZE if overlay else PANEL_SIZE))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle('Keyboard Lighting')
        self.setStyleSheet(STYLE)
        self.panel = LightingPanel(self)
        self.panel.setFixedSize(*PANEL_SIZE)
        self.panel.move(226, 136) if overlay else self.panel.move(0, 0)
        _label(self.panel, 'Keyboard Lighting', 44, 20, 500, size=18, color='#fff')
        self.close_button = QPushButton('×', self.panel)
        self.close_button.setGeometry(822, 20, 20, 16)
        self.close_button.setAccessibleName('Close Keyboard Lighting Window')
        self.close_button.clicked.connect(self.reject)
        self.kind_group = QButtonGroup(self)
        self.static_radio = QRadioButton('Static', self.panel)
        self.dynamic_radio = QRadioButton('Dynamic', self.panel)
        for index, button in enumerate((self.static_radio, self.dynamic_radio)):
            button.setGeometry(44+index*130, 67, 125, 28)
            self.kind_group.addButton(button, index)
        (self.dynamic_radio if self._mode == 'dynamic' else self.static_radio).setChecked(True)
        self.kind_group.idClicked.connect(self._kind_clicked)
        _label(self.panel, '☼', 650, 65, 24, size=18)
        _label(self.panel, '☼', 810, 65, 24, size=18, color='#fff')
        self.brightness = QSlider(Qt.Orientation.Horizontal, self.panel)
        self.brightness.setGeometry(680, 62, 121, 28)
        self.brightness.setRange(1, 5)
        self.brightness.setSingleStep(1)
        self.brightness.setPageStep(1)
        self.brightness.setTickInterval(1)
        self.brightness.setValue(max(1, min(5, round(profile.get('brightness', 100)/25)+1)))
        self.brightness.setAccessibleName('Brightness Scroll Bar')
        self.brightness.sliderReleased.connect(self._apply)
        self.brightness.valueChanged.connect(self._brightness_changed)
        self.static_page = QWidget(self.panel)
        self.static_page.setGeometry(24, 97, 820, 367)
        self.keyboard = OriginalKeyboard(self.static_page, assets, geometry_xaml)
        self.keyboard.setGeometry(0, 30, 820, 240)
        self.zone_switches = []
        self.zone_buttons = []
        for zone in range(4):
            x = 39 + zone*194
            label = _label(self.static_page, f'Zone {zone+1}', x, 293, 160, 22)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            switch = OriginalSwitch(self.static_page)
            switch.move(x+35, 333)
            switch.setChecked(bool(self._enabled[zone]))
            switch.setAccessibleName(f'Zone {zone+1} Lighting')
            switch.clicked.connect(lambda checked, zone=zone:self._zone_toggled(zone, checked))
            color = QPushButton('', self.static_page)
            color.setGeometry(x+103, 333, 20, 20)
            color.setAccessibleName(f'Zone {zone+1} Lighting Color')
            color.clicked.connect(lambda checked=False, zone=zone:self.open_palette(zone))
            self.zone_switches.append(switch)
            self.zone_buttons.append(color)
        self.dynamic_page = QWidget(self.panel)
        self.dynamic_page.setGeometry(24, 97, 816, 367)
        _label(self.dynamic_page, 'Light Effects', 13, 10, 300)
        self.effect_group = QButtonGroup(self)
        self.effect_buttons = {}
        for index, (wire_id, title) in enumerate(EFFECTS):
            column = 0 if index < 3 else 1
            row = index if index < 3 else index-3
            button = QRadioButton(title, self.dynamic_page)
            button.setGeometry(18+column*261, 40+row*36, 220, 28)
            self.effect_group.addButton(button, wire_id)
            self.effect_buttons[wire_id] = button
            button.setChecked(wire_id == self._effect)
        self.effect_group.idClicked.connect(self._effect_clicked)
        _label(self.dynamic_page, 'Speed', 13, 176, 180)
        self.speed = QSlider(Qt.Orientation.Horizontal, self.dynamic_page)
        self.speed.setGeometry(21, 208, 160, 28)
        self.speed.setRange(1, 9)
        self.speed.setValue(max(1, min(9, profile.get('speed', 5))))
        self.speed.setAccessibleName('Speed Scroll Bar')
        self.speed.valueChanged.connect(self._speed_changed)
        self.speed.sliderReleased.connect(self._apply)
        self.direction_panel = QWidget(self.dynamic_page)
        self.direction_panel.setGeometry(253, 176, 280, 90)
        _label(self.direction_panel, 'Direction', 0, 0, 180)
        self.direction_group = QButtonGroup(self)
        self.left_direction = QRadioButton('←', self.direction_panel)
        self.right_direction = QRadioButton('→', self.direction_panel)
        for wire_id, button, x, title in ((2, self.left_direction, 0, 'Direction Left'), (1, self.right_direction, 78, 'Direction Right')):
            button.setGeometry(x, 36, 72, 28)
            button.setAccessibleName(title)
            self.direction_group.addButton(button, wire_id)
            button.setChecked(wire_id == self._direction)
        self.direction_group.idClicked.connect(self._direction_clicked)
        self.color_area = QWidget(self.dynamic_page)
        self.color_area.setGeometry(13, 277, 803, 90)
        _label(self.color_area, 'Basic colors', 0, 0, 230, size=18)
        _label(self.color_area, 'Recent colors', 276, 0, 230, size=18)
        self.basic_buttons = []
        self.recent_buttons = []
        for index, color in enumerate(BASIC_COLORS):
            button = Swatch(color, self.color_area)
            button.move(4+index*24, 32)
            button.setAccessibleName(COLOR_NAMES[index])
            button.clicked.connect(lambda checked=False, color=color:self._choose_color(color, False, dynamic=True))
            self.basic_buttons.append(button)
        for index in range(9):
            color = self.recent_colors[index] if index < len(self.recent_colors) else None
            button = Swatch(color, self.color_area)
            button.move(280+index*24, 32)
            button.setAccessibleName(f'Recent Color {index+1}')
            button.clicked.connect(lambda checked=False, button=button:self._choose_color(button.color, False, dynamic=True))
            self.recent_buttons.append(button)
        self.more_color = QPushButton('More color...', self.color_area)
        self.more_color.setGeometry(590, 25, 193, 36)
        self.more_color.clicked.connect(self._dynamic_more)
        self.palette = ColorPopup(self.recent_colors, self.panel)
        self.palette.chosen.connect(self._palette_chosen)
        self._refresh_controls()
        self._ready = True

    def settings(self):
        return {'type': self._mode, 'colors': list(self._colors), 'zone_enabled': list(self._enabled),
                'brightness': (self.brightness.value()-1)*25, 'mode': self._effect,
                'speed': self.speed.value(), 'direction': self._direction, 'color': self._dynamic_color,
                'effect_settings': dict(self._effects, **{str(self._effect): {'speed': self.speed.value(), 'direction': self._direction}})}

    def _refresh_controls(self):
        static = self._mode == 'static'
        self.static_page.setVisible(static)
        self.dynamic_page.setVisible(not static)
        active = self.available and self.brightness.value() > 1
        self.brightness.setEnabled(self.available)
        self.static_radio.setEnabled(self.available)
        self.dynamic_radio.setEnabled(self.available)
        self.keyboard.colors = list(self._colors)
        self.keyboard.enabled = list(self._enabled)
        self.keyboard.dimmed = not active
        self.keyboard.update()
        for index, (switch, button) in enumerate(zip(self.zone_switches, self.zone_buttons)):
            switch.setEnabled(active)
            button.setEnabled(active and self._enabled[index])
            button.setStyleSheet(f'background:#{self._colors[index]};border:1px solid #808080;')
        self.direction_panel.setVisible(self._effect in (3, 4))
        self.direction_panel.setEnabled(active)
        for button in self.effect_buttons.values():
            button.setEnabled(active)
        self.speed.setEnabled(active)
        colors_enabled = active and self._effect not in (2, 3)
        self.color_area.setEnabled(colors_enabled)
        self.color_area.setStyleSheet('color:#808080;' if colors_enabled else 'color:#404040;')
        for button in self.basic_buttons:
            button.setEnabled(colors_enabled)
            button.setChecked(button.color == self._dynamic_color)
        for index, button in enumerate(self.recent_buttons):
            button.color = self.recent_colors[index] if index < len(self.recent_colors) else None
            button.setEnabled(colors_enabled and button.color is not None)
            button.setChecked(button.color == self._dynamic_color)
            button.update()

    def _apply(self):
        if not self._ready or not self.available:
            return
        proposed = self.settings()
        try:
            if self._mode == 'static':
                colors = [color if enabled else '000000' for color, enabled in zip(self._colors, self._enabled)]
                self.backend.set_lighting_static(colors, proposed['brightness'])
            else:
                self.backend.set_lighting_dynamic(self._effect, self.speed.value(), proposed['brightness'],
                    self._direction if self._effect in (3, 4) else 0, self._dynamic_color)
        except Exception as exc:
            QMessageBox.critical(self, 'Lighting request failed', str(exc))
            return
        self.profile = proposed
        self.profileChanged.emit(copy.deepcopy(proposed))

    def _kind_clicked(self, index):
        self._mode = 'static' if index == 0 else 'dynamic'
        self._refresh_controls()
        self._apply()

    def _effect_clicked(self, effect):
        self._effects[str(self._effect)] = {'speed': self.speed.value(), 'direction': self._direction}
        self._effect = effect
        saved = self._effects.get(str(effect), {'speed': 5, 'direction': 1})
        with QSignalBlocker(self.speed):self.speed.setValue(saved['speed'])
        self._direction = saved['direction']
        for value, button in ((1, self.right_direction), (2, self.left_direction)):
            with QSignalBlocker(button):button.setChecked(value == self._direction)
        self._refresh_controls()
        self._apply()

    def _direction_clicked(self, direction):
        self._direction = direction
        self._apply()

    def _brightness_changed(self, _):
        self._refresh_controls()
        if not self.brightness.isSliderDown():
            self._apply()

    def _speed_changed(self, _):
        if not self.speed.isSliderDown():
            self._apply()

    def _zone_toggled(self, index, enabled):
        self._enabled[index] = enabled
        self._refresh_controls()
        self._apply()

    def open_palette(self, zone):
        if not self.available or not self._enabled[zone] or self.brightness.value() == 1:
            return
        self._target_zone = zone
        self.palette.current_color = self._colors[zone]
        self.palette.recent_colors = list(self.recent_colors)
        for index, button in enumerate(self.palette.recent):
            button.color = self.recent_colors[index] if index < len(self.recent_colors) else None
            button.setEnabled(button.color is not None)
            button.setChecked(False)
            button.update()
        for button in self.palette.basic:
            button.setChecked(False)
        point = self.zone_buttons[zone].mapToGlobal(self.zone_buttons[zone].rect().topRight())
        self.palette.move(point.x()+5, point.y()-60)
        self.palette.show()

    def _palette_chosen(self, color, custom):
        self._choose_color(color, custom, dynamic=False)

    def _choose_color(self, color, custom, *, dynamic):
        if not color:
            return
        color = _hex(color)
        if dynamic:
            self._dynamic_color = color
        else:
            self._colors[self._target_zone] = color
        if custom and color not in BASIC_COLORS and color not in self.recent_colors:
            self.recent_colors = ([color] + self.recent_colors)[:9]
            self.recentColorsChanged.emit(list(self.recent_colors))
        self._refresh_controls()
        self._apply()

    def _dynamic_more(self):
        picker = OriginalColorPicker(self._dynamic_color, self)
        if picker.exec() == QDialog.DialogCode.Accepted:
            self._choose_color(picker.selected_color(), True, dynamic=True)

    def paintEvent(self, event):
        if self.overlay:
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 130))

    def mousePressEvent(self, event):
        if self.overlay and not self.panel.geometry().contains(event.position().toPoint()):
            self.reject()
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.palette.isVisible():
            self.palette.hide()
            event.accept()
        else:
            super().keyPressEvent(event)
