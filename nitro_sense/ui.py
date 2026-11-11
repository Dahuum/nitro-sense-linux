"""Native Qt application reconstructed around NitroSense's 2021 layout.

Acer artwork is optional and never required by a release. The default distributed
skin is drawn by this module. Device commands are issued only by explicit actions.
"""
from __future__ import annotations
from collections import deque
import csv
from datetime import datetime, timezone
import json
import math
import os
import signal
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QSignalBlocker, QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import (QAction, QColor, QIcon, QLinearGradient, QPainter,
                          QPainterPath, QPen, QPixmap, QPolygonF)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QColorDialog,
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGraphicsScene,
    QGraphicsView, QGridLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel,
    QMenu, QMessageBox, QPushButton, QRadioButton, QSlider, QSpinBox, QSystemTrayIcon,
    QTabWidget, QVBoxLayout, QWidget)
from .profiles import DEFAULT_PROFILE, ProfileStore, validate_profile

ROOT = Path(__file__).resolve().parents[1]
# Opt in to locally extracted artwork; public distributions contain our drawn skin.
def asset_directory():
    explicit = os.environ.get('NITRO_SENSE_ASSETS')
    if explicit:
        return Path(explicit) if explicit.lower() != 'none' else None
    candidates = [Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'nitro-sense/assets',
                  ROOT / 'extracted/ui-analysis/resources']
    return next((path for path in candidates if (path / 'images/100/img_bg_nitro.png').is_file()), None)


ASSETS = asset_directory()
STYLE = '''
QWidget {color:#e4e4e4;font:14px "Segoe UI",sans-serif;background:transparent;}
QDialog {background:#191b1e;} QToolTip {background:#282b30;color:#eee;border:1px solid #555;}
QPushButton {background:#24272c;border:1px solid #5a5d62;padding:7px 12px;}
QPushButton:hover {border-color:#ed2525;color:white;} QPushButton:pressed {background:#481b20;}
QPushButton:disabled,QCheckBox:disabled,QRadioButton:disabled {color:#777;border-color:#35373b;}
QPushButton:checked {border:1px solid #ff3939;background:#471b22;}
QComboBox,QSpinBox {background:#25282d;border:1px solid #595c62;padding:5px;}
QComboBox QAbstractItemView {background:#25282d;color:#eee;selection-background-color:#a62029;}
QSlider::groove:horizontal {height:4px;background:#555;} QSlider::handle:horizontal {width:14px;background:#ed3030;margin:-5px 0;}
QSlider::groove:horizontal:disabled {background:#34383e;} QSlider::handle:horizontal:disabled {background:#626872;}
QGroupBox {border:1px solid #44484e;margin-top:16px;padding:14px 8px 8px;} QGroupBox::title {subcontrol-origin:margin;left:10px;}
QTabWidget::pane {border:1px solid #43464b;} QTabBar::tab {background:#24272c;padding:6px 16px;border:1px solid #42454a;}
QTabBar::tab:selected {border-bottom:2px solid #ed3030;}
'''


def error(parent, title, exc):
    QMessageBox.critical(parent, title, str(exc))


class SliderSpinBox(QSpinBox):
    def __init__(self, slider):
        super().__init__();self.slider=slider
    def setEnabled(self, enabled):
        super().setEnabled(enabled);self.slider.setEnabled(enabled)


def slider_row(layout, label, low, high, value, suffix=''):
    row = QHBoxLayout()
    row.addWidget(QLabel(label))
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(low, high)
    slider.setValue(value)
    spin = SliderSpinBox(slider)
    spin.setRange(low, high)
    spin.setSuffix(suffix)
    spin.setValue(value)
    slider.valueChanged.connect(spin.setValue)
    spin.valueChanged.connect(slider.setValue)
    row.addWidget(slider, 1)
    row.addWidget(spin)
    layout.addLayout(row)
    return spin


class Skin(QWidget):
    """Original drawing based on measured layout, without copyrighted bitmap assets."""
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('#0c0e10'))
        body = QRectF(42, 30, 1236, 705)
        gradient = QLinearGradient(0, 30, 0, 735)
        gradient.setColorAt(0, QColor('#292c30'))
        gradient.setColorAt(.5, QColor('#17191c'))
        gradient.setColorAt(1, QColor('#26292d'))
        p.setPen(QPen(QColor('#3e4248'), 1))
        p.setBrush(gradient)
        p.drawRoundedRect(body, 36, 36)
        # A restrained fine mesh; all geometry is generated locally.
        p.setPen(QPen(QColor('#31343a'), .5))
        for x in range(62, 1260, 8):
            for y in range(46, 730, 8):
                p.drawPoint(x, y)
        for x,y,w,h in [(104,110,1112,252),(104,378,256,320),(374,378,842,320)]:
            polygon = QPolygonF([QPointF(x+20,y),QPointF(x+w-20,y),QPointF(x+w,y+20),
                                QPointF(x+w,y+h-20),QPointF(x+w-20,y+h),QPointF(x+20,y+h),
                                QPointF(x,y+h-20),QPointF(x,y+20)])
            p.setBrush(QColor('#111417'))
            p.setPen(QPen(QColor('#5b5e63'), 1))
            p.drawPolygon(polygon)
            p.setPen(QPen(QColor('#1b1e22'), 1))
            for yy in range(y+4,y+h-3,4):
                p.drawLine(x+20,yy,x+w-20,yy)
        p.setPen(QColor('#eeeeee'))
        font = p.font();font.setPointSize(23);font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, 6);p.setFont(font)
        p.drawText(QRectF(420,47,480,40), Qt.AlignmentFlag.AlignCenter, 'NITRO SENSE')
        font.setPointSize(11);font.setLetterSpacing(font.SpacingType.AbsoluteSpacing,1);p.setFont(font)
        p.setPen(QColor('#969ba3'));p.drawText(QRectF(100,49,230,35),Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,'LINUX / NATIVE')


class FanArt(QWidget):
    """RPM-driven visual indicator; animation is scaled for readable screen motion."""
    def __init__(self,parent=None,pixmap=None):
        super().__init__(parent);self.rpm=None;self.angle=0.0;self.pixmap=pixmap
        self.animation=QTimer(self);self.animation.setInterval(40);self.animation.timeout.connect(self.advance)
    def set_rpm(self,rpm):
        self.rpm=float(rpm) if isinstance(rpm,(int,float)) and math.isfinite(rpm) and rpm>=0 else None
        if self.rpm and not self.animation.isActive():self.animation.start()
        elif not self.rpm:self.animation.stop()
    def advance(self):
        if self.rpm:
            self.angle=(self.angle+min(self.rpm/1000*120,900)*.04)%360
            self.update()
    def paintEvent(self, event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(self.width()/2,self.height()/2)
        p.save();p.rotate(self.angle)
        if self.pixmap and not self.pixmap.isNull():
            p.drawPixmap(QRectF(-self.width()/2,-self.height()/2,self.width(),self.height()),self.pixmap,QRectF(self.pixmap.rect()))
            p.restore();return
        for angle in range(0,360,15):
            p.save();p.rotate(angle)
            path=QPainterPath();path.moveTo(48,-8);path.cubicTo(90,-18,97,-49,91,-62);path.cubicTo(103,-34,80,-7,49,7);path.closeSubpath()
            p.fillPath(path,QColor('#41474e'));p.restore()
        p.restore()
        p.setPen(QPen(QColor('#9f2832'),2));p.setBrush(QColor('#111417'));p.drawEllipse(QPointF(0,0),63,63)


class Trace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.samples={};self.maximum=120;self.units='°C'
    def update_samples(self, readings):
        active=set()
        for name,value in readings.items():
            if isinstance(value,(int,float)) and math.isfinite(value):
                self.samples.setdefault(name,deque(maxlen=120)).append(float(value));active.add(name)
        for name in set(self.samples)-active:
            self.samples.pop(name,None)
        self.update()
    def clear(self):
        self.samples.clear();self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect=self.rect().adjusted(38,30+18*max(0,(len(self.samples)-1)//4),-8,-20)
        p.setPen(QPen(QColor('#30363d'),1))
        for fraction in (0,.25,.5,.75,1):
            y=rect.bottom()-rect.height()*fraction
            p.drawLine(QPointF(rect.left(),y),QPointF(rect.right(),y))
            p.setPen(QColor('#9299a3'))
            p.drawText(QRectF(0,y-9,33,18),Qt.AlignmentFlag.AlignRight,f'{self.maximum*fraction:.0f}')
            p.setPen(QPen(QColor('#30363d'),1))
        colors=['#f12a36','#f4a340','#4acbd3','#a5aab2','#77d685','#b58cef']
        for i,(name,values) in enumerate(self.samples.items()):
            p.setPen(QPen(QColor(colors[i%len(colors)]),2))
            vals=list(values)
            for j in range(1,len(vals)):
                p.drawLine(QPointF(rect.left()+(j-1)*rect.width()/119,rect.bottom()-max(0,min(self.maximum,vals[j-1]))*rect.height()/self.maximum),
                           QPointF(rect.left()+j*rect.width()/119,rect.bottom()-max(0,min(self.maximum,vals[j]))*rect.height()/self.maximum))
            p.drawText(QRectF(40+(i%4)*185,2+(i//4)*18,180,22),p.fontMetrics().elidedText(name,Qt.TextElideMode.ElideRight,178))
        if not self.samples:
            p.setPen(QColor('#9299a3'));p.drawText(rect,Qt.AlignmentFlag.AlignCenter,'No samples available')
        p.setPen(QColor('#8a919b'));p.drawText(QRectF(rect.left(),rect.bottom()+3,rect.width(),18),Qt.AlignmentFlag.AlignRight,f'Last 4 minutes · {self.units}')


BASIC_COLORS=('FF0000','FFA000','FFFF00','00FF00','00AEC7','001EFF','FF00FF','AA00FF','FFFFFF')
RECENT_COLORS=[]


class PaletteDialog(QDialog):
    """Recovered nine basic colors, nine session-recent swatches, custom picker."""
    def __init__(self,current,parent=None,title='Select color'):
        super().__init__(parent);self.setWindowTitle(title);self.setStyleSheet(STYLE);self.color=current
        layout=QVBoxLayout(self)
        for heading,values in [('Basic colors',BASIC_COLORS),('Recent colors',tuple(RECENT_COLORS)+tuple(None for _ in range(9-len(RECENT_COLORS))))]:
            layout.addWidget(QLabel(heading));row=QHBoxLayout()
            for value in values:
                button=QPushButton();button.setFixedSize(30,30);button.setEnabled(value is not None)
                button.setToolTip('#'+value if value else 'No recent color');button.setAccessibleName('#'+value if value else 'Empty recent color')
                button.setStyleSheet(f'background:#{value or "292d33"};border:1px solid #777;padding:0;')
                button.clicked.connect(lambda checked=False,color=value:self.select_color(color));row.addWidget(button)
            layout.addLayout(row)
        custom=QPushButton('More colors…');custom.clicked.connect(self.custom_color);layout.addWidget(custom)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
    def select_color(self,color):
        self.color=color
        if color in RECENT_COLORS:RECENT_COLORS.remove(color)
        RECENT_COLORS.insert(0,color);del RECENT_COLORS[9:]
        self.accept()
    def custom_color(self):
        value=QColorDialog.getColor(QColor('#'+self.color),self,'Custom color')
        if value.isValid():self.select_color(value.name()[1:].upper())


class KeyboardPreview(QWidget):
    def __init__(self, colors, parent=None):
        super().__init__(parent);self.colors=colors;self.setMinimumHeight(142)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds=self.rect().adjusted(8,8,-8,-8)
        p.setPen(QPen(QColor('#626870'),1));p.setBrush(QColor('#101215'));p.drawRoundedRect(bounds,8,8)
        left,top=bounds.left()+9,bounds.top()+9
        kw=(bounds.width()-22)/15;kh=(bounds.height()-22)/5
        for row in range(5):
            for col in range(15):
                zone=min(3,col*4//15);color=QColor('#'+self.colors[zone]);fill=QColor(color);fill.setAlpha(35)
                key=QRectF(left+col*kw,top+row*kh,kw-4,kh-4)
                p.setPen(QPen(color if color.value()>0 else QColor('#555b62'),1));p.setBrush(fill);p.drawRoundedRect(key,2,2)
        # Spacebar cue keeps the four zones legible without reproducing key legends.
        p.setPen(QPen(QColor('#939aa4'),1));p.setBrush(QColor('#171a1f'))
        p.drawRoundedRect(QRectF(left+4*kw,top+4*kh,5*kw-4,kh-4),2,2)


class LightingDialog(QDialog):
    def __init__(self, backend, state, profile, parent=None):
        super().__init__(parent)
        self.backend=backend;self.profile=json.loads(json.dumps(profile));self.setWindowTitle('Keyboard lighting')
        self.setStyleSheet(STYLE);self.resize(868,488)
        root=QVBoxLayout(self);root.setContentsMargins(24,20,24,20)
        title=QLabel('KEYBOARD LIGHTING');title.setStyleSheet('font-size:22px;letter-spacing:3px;');root.addWidget(title)
        self.tabs=QTabWidget();root.addWidget(self.tabs)
        self.zone_colors=list(profile['colors']);self.zone_buttons=[];self.zone_enabled=[]
        static=QWidget();layout=QVBoxLayout(static);self.keyboard=KeyboardPreview(self.zone_colors);layout.addWidget(self.keyboard);root_static=QHBoxLayout()
        for i,color in enumerate(self.zone_colors):
            box=QVBoxLayout();button=QPushButton(f'ZONE {i+1} · #{color}');button.setMinimumHeight(42)
            button.clicked.connect(lambda checked=False,zone=i:self.choose_zone(zone));box.addWidget(button)
            enabled=QCheckBox('Enabled');enabled.setChecked(color!='000000');box.addWidget(enabled)
            root_static.addLayout(box);self.zone_buttons.append(button);self.zone_enabled.append(enabled)
            enabled.toggled.connect(lambda checked:self.paint_colors())
        layout.addLayout(root_static)
        self.static_brightness=slider_row(layout,'Brightness',0,100,profile['brightness'],'%')
        self.tabs.addTab(static,'Static')
        dynamic=QWidget();dl=QVBoxLayout(dynamic);self.pattern=QComboBox()
        for label,value in [('Breathing',1),('Neon',2),('Wave',3),('Shifting',4),('Zoom',5)]:self.pattern.addItem(label,value)
        index=self.pattern.findData(profile['mode']);self.pattern.setCurrentIndex(max(0,index))
        form=QFormLayout();form.addRow('Effect',self.pattern);dl.addLayout(form)
        self.dynamic_speed=slider_row(dl,'Speed',0,9,profile['speed'])
        self.dynamic_brightness=slider_row(dl,'Brightness',0,100,profile['brightness'],'%')
        self.direction=QComboBox();self.direction.addItem('Left',1);self.direction.addItem('Right',2)
        self.direction.setCurrentIndex(max(0,self.direction.findData(profile['direction'])))
        form2=QFormLayout();form2.addRow('Direction',self.direction);dl.addLayout(form2)
        self.dynamic_color=profile['color'];self.color_button=QPushButton('Effect color');self.color_button.clicked.connect(self.choose_dynamic);dl.addWidget(self.color_button)
        self.effect_note=QLabel();self.effect_note.setWordWrap(True);dl.addWidget(self.effect_note)
        self.pattern.currentIndexChanged.connect(self.effect_changed)
        self.tabs.addTab(dynamic,'Dynamic');self.tabs.setCurrentIndex(1 if profile['type']=='dynamic' else 0)
        self.result_label=QLabel('Changes are applied only when you press Apply.');self.result_label.setWordWrap(True);root.addWidget(self.result_label)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close)
        self.apply_button=buttons.button(QDialogButtonBox.StandardButton.Apply)
        self.apply_button.setEnabled(bool(state.get('lighting_available')))
        self.apply_button.setToolTip(state.get('lighting_reason',''))
        self.apply_button.clicked.connect(self.apply);buttons.rejected.connect(self.reject);root.addWidget(buttons)
        self.paint_colors();self.effect_changed()
    def paint_colors(self):
        for button,color in zip(self.zone_buttons,self.zone_colors):
            button.setText(f'ZONE {self.zone_buttons.index(button)+1} · #{color}')
            button.setStyleSheet(f'border:2px solid #{color};background:#24272c;')
        self.color_button.setStyleSheet(f'border:2px solid #{self.dynamic_color};')
        self.keyboard.colors=[color if enabled.isChecked() else '000000' for color,enabled in zip(self.zone_colors,self.zone_enabled)]
        self.keyboard.update()
    def choose_zone(self,index):
        picker=PaletteDialog(self.zone_colors[index],self,f'Zone {index+1}')
        if picker.exec()==QDialog.DialogCode.Accepted:
            self.zone_colors[index]=picker.color;self.zone_enabled[index].setChecked(True);self.paint_colors()
    def choose_dynamic(self):
        picker=PaletteDialog(self.dynamic_color,self,'Effect color')
        if picker.exec()==QDialog.DialogCode.Accepted:self.dynamic_color=picker.color;self.paint_colors()
    def effect_changed(self):
        mode=self.pattern.currentData();self.direction.setEnabled(mode in (3,4));self.color_button.setEnabled(mode not in (2,3))
        self.dynamic_speed.setEnabled(mode!=1)
        self.effect_note.setText({1:'Breathing speed is firmware-controlled on this model.',2:'Neon cycles its own colors.',3:'Wave uses firmware colors; choose a direction.',4:'Shifting supports direction and effect color.',5:'Zoom uses the selected effect color.'}.get(mode,''))
    def settings(self):
        dynamic=self.tabs.currentIndex()==1
        return {'type':'dynamic' if dynamic else 'static',
                'colors':[v if enabled.isChecked() else '000000' for v,enabled in zip(self.zone_colors,self.zone_enabled)],
                'brightness':self.dynamic_brightness.value() if dynamic else self.static_brightness.value(),
                'mode':self.pattern.currentData(),'speed':self.dynamic_speed.value(),
                'direction':self.direction.currentData(),'color':self.dynamic_color}
    def apply(self):
        try:
            self.profile=self.settings()
            if self.profile['type']=='static':
                self.backend.set_lighting_static(self.profile['colors'],self.profile['brightness'])
            else:
                p=self.profile;self.backend.set_lighting_dynamic(p['mode'],p['speed'],p['brightness'],p['direction'],p['color'])
            self.result_label.setText('Device accepted the lighting request. Visible color and effect must be checked on the keyboard.')
            parent=self.parent()
            if hasattr(parent,'current_profile'):parent.current_profile['lighting']=self.profile
        except Exception as exc:error(self,'Lighting request failed',exc)


class SnapshotSignals(QObject):
    ready=Signal(dict)
    failed=Signal(str)


class SnapshotWorker(QRunnable):
    def __init__(self,backend):
        super().__init__();self.backend=backend;self.signals=SnapshotSignals()
    def run(self):
        try:self.signals.ready.emit(self.backend.snapshot())
        except Exception as exc:self.signals.failed.emit(str(exc))


class NitroWindow(QGraphicsView):
    def __init__(self, backend=None, profile_store=None):
        super().__init__()
        if backend is None:
            from .backend import Backend
            backend=Backend()
        self.backend=backend;self.store=profile_store or ProfileStore();self.current_profile=validate_profile(self.store.profiles[0])
        self.state={};self.history=deque(maxlen=7200);self._quitting=False;self._refreshing=False;self._closing=False;self.pool=QThreadPool(self);self._custom_editing=False
        self.setWindowTitle('NitroSense Linux');self.setMinimumSize(900,540);self.resize(1320,800)
        self.setStyleSheet('QGraphicsView {border:0;background:#0c0e10;}')
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scene=QGraphicsScene(self);self.setScene(scene);scene.setSceneRect(0,0,1320,800)
        self.canvas=self.create_canvas();self.canvas.setFixedSize(1320,800);self.canvas.setStyleSheet(STYLE)
        if ASSETS:
            self.art('images/100/img_bg_nitro.png',0,0,1320,760)
            self.art('images/100/img_bg_newboard_nitro.png',84,92,1152,624)
        for title,x,y,width in [('FAN CONTROL',122,120,210),('POWER PLAN',122,388,216),('MONITORING',394,388,210)]:self.label(title,x,y,width,24,16)
        self.button('Lighting',936,52,108,34).clicked.connect(self.show_lighting)
        self.button('Settings',1054,52,115,34).clicked.connect(self.show_settings)
        self.mode_group=QButtonGroup(self);self.mode_buttons=[]
        for i,text in enumerate(['Auto','Max','Custom']):
            radio=QRadioButton(text,self.canvas);radio.setGeometry(120,170+i*68,220,56);radio.setEnabled(False)
            self.mode_group.addButton(radio,i);self.mode_buttons.append(radio)
            radio.clicked.connect(lambda checked,mode=i:self.change_fans(mode))
        self.fan_values=[];self.fan_art=[]
        for x,name,label_x in [(540,'CPU',480),(756,'GPU',964)]:
            self.label(name,label_x,243,60,28,18,True)
            pixmap=QPixmap(str(ASSETS/'images/100/img_fan.png')) if ASSETS else None
            fan=FanArt(self.canvas,pixmap);fan.setGeometry(x,152,200,200);self.fan_art.append(fan)
            self.fan_values.append(self.label('—',x,229,200,44,28,True));self.label('RPM',x,273,200,26,12,True)
        self.fan_request_label=self.label('Automatic control',540,344,416,16,10,True)
        self.inline_fans=[]
        for x,key in [(372,'cpu'),(964,'gpu')]:
            panel=QWidget(self.canvas);panel.setGeometry(x,275,160,74)
            slider=QSlider(Qt.Orientation.Horizontal,panel);slider.setGeometry(0,0,150,22);slider.setRange(1,100);slider.setValue(50)
            value=QLabel('50%',panel);value.setGeometry(0,22,65,20)
            automatic=QCheckBox('Auto',panel);automatic.setGeometry(72,40,80,22);automatic.setChecked(True);slider.setEnabled(False)
            automatic.toggled.connect(lambda checked,control=slider:control.setEnabled(not checked))
            automatic.clicked.connect(self.mark_custom_pending)
            slider.valueChanged.connect(lambda number,label=value:label.setText(f'{number}%'))
            slider.sliderPressed.connect(self.mark_custom_pending)
            slider.sliderReleased.connect(self.apply_inline_fans)
            panel.hide();self.inline_fans.append({'key':key,'panel':panel,'slider':slider,'auto':automatic,'value':value})
        self.inline_apply=self.button('Apply',235,321,92,28);self.inline_apply.clicked.connect(self.apply_inline_fans);self.inline_apply.hide()
        self.coolboost=QCheckBox('CoolBoost',self.canvas);self.coolboost.setGeometry(1055,124,140,30);self.coolboost.setEnabled(False)
        self.coolboost.clicked.connect(self.set_coolboost)
        self.label('Linux power profile',120,452,205,24,14)
        self.power_buttons=[]
        for i,(text,key) in enumerate([('Power saver','power-saver'),('Balanced','balanced'),('High performance','performance')]):
            button=self.button(text,120,493+i*51,205,39);button.setCheckable(True);button.setEnabled(False)
            button.clicked.connect(lambda checked=False,value=key:self.set_power(value));self.power_buttons.append((button,key))
        self.power_note=self.label('',120,648,210,39,11);self.power_note.setWordWrap(True)
        self.monitor=QComboBox(self.canvas);self.monitor.setGeometry(400,430,155,31)
        for label,key in [('CPU temperature','cpu'),('GPU temperature','gpu'),('All temperatures','all'),('CPU / GPU usage','usage')]:self.monitor.addItem(label,key)
        self.monitor.currentIndexChanged.connect(self.monitor_changed)
        self.button('Clear',930,430,78,31).clicked.connect(self.clear_history)
        self.button('Export CSV',1018,430,112,31).clicked.connect(self.export_history)
        self.button('Details',1140,430,70,31).clicked.connect(self.show_sensors)
        self.sensor_text=self.label('Reading sensors…',400,470,790,50,15);self.sensor_text.setWordWrap(True)
        self.chart=Trace(self.canvas);self.chart.setGeometry(390,522,810,169)
        self.status=self.label('',50,752,1220,42,12);self.status.setWordWrap(True)
        scene.addWidget(self.canvas)
        self.create_tray()
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(2000);self.refresh()
    def create_canvas(self):
        return Skin()
    def label(self,text,x,y,w,h,size=14,center=False):
        label=QLabel(text,self.canvas);label.setGeometry(x,y,w,h);label.setStyleSheet(f'font-size:{size}px;')
        if center:label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
    def button(self,text,x,y,w,h):
        button=QPushButton(text,self.canvas);button.setGeometry(x,y,w,h);return button
    def art(self,filename,x,y,w,h):
        if not ASSETS or not (ASSETS/filename).exists():return
        label=QLabel(self.canvas);label.setGeometry(x,y,w,h);label.setPixmap(QPixmap(str(ASSETS/filename)));label.setScaledContents(True)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.scene():self.fitInView(self.sceneRect(),Qt.AspectRatioMode.KeepAspectRatio)
    def create_tray(self):
        self.tray=None
        if QSystemTrayIcon.isSystemTrayAvailable():
            pix=QPixmap(48,48);pix.fill(QColor('#17191c'));p=QPainter(pix);p.setPen(QPen(QColor('#f12a36'),5));p.drawLine(12,35,12,12);p.drawLine(12,12,35,35);p.drawLine(35,35,35,12);p.end()
            self.tray=QSystemTrayIcon(QIcon(pix),self);self.tray.setToolTip('NitroSense Linux')
            menu=QMenu();show=menu.addAction('Show NitroSense');show.triggered.connect(self.showNormal)
            auto=menu.addAction('Automatic fans');auto.triggered.connect(lambda:self.change_fans(0))
            quit_action=menu.addAction('Quit');quit_action.triggered.connect(self.quit)
            self.tray.setContextMenu(menu);self.tray.activated.connect(lambda reason:self.showNormal() if reason==QSystemTrayIcon.ActivationReason.Trigger else None);self.tray.show()
    def refresh(self):
        if self._refreshing or self._closing:return
        self._refreshing=True
        self._worker=SnapshotWorker(self.backend)
        self._worker.signals.ready.connect(self.snapshot_ready)
        self._worker.signals.failed.connect(self.snapshot_failed)
        self.pool.start(self._worker)
    def snapshot_ready(self,state):
        if self._closing:return
        self._refreshing=False
        self.apply_state(state)
    def snapshot_failed(self,message):
        if self._closing:return
        self._refreshing=False
        self.status.setText('Device read failed: '+message)
    def apply_state(self,state):
        try:
            self.state=state
            for button in self.mode_buttons:button.setEnabled(bool(state.get('fan_control_available')))
            request=state.get('fan_request',{});index=0
            if request:
                cpu,gpu=request.get('cpu',0),request.get('gpu',0)
                index=0 if cpu==gpu==0 else 1 if cpu==gpu==100 else 2
                if not self._custom_editing:self.mode_buttons[index].setChecked(True)
                self.fan_request_label.setText('Custom settings pending Apply' if self._custom_editing else 'Automatic control' if index==0 else f'Requested CPU {cpu}% / GPU {gpu}%')
                self.show_inline_fans(self._custom_editing or index==2)
                if not self._custom_editing:self.sync_inline_fans(request)
            self.show_inline_fans(bool(self._custom_editing or (request and index==2)))
            for label in self.fan_values:label.setText('—')
            for art in self.fan_art:art.set_rpm(None)
            if state.get('model')=='Nitro AN515-45':
                measured={f['name']:f['rpm'] for f in state.get('fans',[])}
                for label,art,key in zip(self.fan_values,self.fan_art,('acer / fan1_input','acer / fan2_input')):
                    if key in measured:label.setText(str(measured[key]));art.set_rpm(measured[key])
            self.coolboost.setEnabled(bool(state.get('capabilities',{}).get('coolboost')))
            coolboost=state.get('switches',{}).get('coolboost',{})
            if coolboost.get('value') in (0,1):self.coolboost.setChecked(coolboost['value']==1)
            self.coolboost.setToolTip(state.get('coolboost_reason','Not exposed by the loaded Linux driver') if not self.coolboost.isEnabled() else '')
            power=state.get('power',{})
            for button,key in self.power_buttons:
                button.setEnabled(bool(power.get('available')) and key in power.get('profiles',[]));button.setChecked(power.get('active')==key)
            self.power_note.setText(power.get('reason','No compatible power-profile interface.'))
            values=self.readings()
            unit='%' if self.monitor.currentData()=='usage' else self.store.preferences.get('temperature_unit','C')
            if unit=='F':values={name:value*9/5+32 for name,value in values.items()}
            self.chart.maximum=100 if unit=='%' else 250 if unit=='F' else 120
            self.chart.units='%' if unit=='%' else '°'+unit
            self.chart.update_samples(values)
            stamp=datetime.now(timezone.utc).isoformat()
            self.history.append({'utc':stamp,'readings':values,'view':self.monitor.currentData(),'unit':unit})
            cpu_usage=state.get('cpu_usage_percent');gpu=state.get('gpu') or {}
            primary=' · '.join(f'{name}: {value:.1f}{"%" if unit=="%" else " °"+unit}' for name,value in list(values.items())[:3])
            if len(values)>3:primary+=f' (+{len(values)-3} sensors; see Details)'
            if len(values)==1 and unit!='%':
                samples=next(iter(self.chart.samples.values()),[])
                if samples:primary+=f' · Min {min(samples):.1f} / Max {max(samples):.1f} °{unit}'
            self.sensor_text.setText(primary or 'No measurements available for this view')
            memory=state.get('memory') or {};memory_text=f" · Memory {memory['percent']:.0f}%" if isinstance(memory.get('percent'),(int,float)) else ''
            self.status.setText(f"{state.get('model','Unknown model')} · {state.get('reason','')}{memory_text}")
        except Exception as exc:self.status.setText(f'Device read failed: {exc}')
    def readings(self):
        state=self.state;kind=self.monitor.currentData();temperatures=state.get('temperatures',[]);gpu=state.get('gpu') or {}
        if kind=='usage':
            values={'CPU':state.get('cpu_usage_percent'),'GPU':gpu.get('utilization_percent')};return {k:v for k,v in values.items() if isinstance(v,(int,float))}
        if kind=='all':return {r['name']:r['celsius'] for r in temperatures}
        if kind=='cpu':
            for prefix in ('k10temp / Tctl','coretemp / Package','acer / temp1_input'):
                for reading in temperatures:
                    if reading['name'].startswith(prefix):return {'CPU':reading['celsius']}
            return {}
        if isinstance(gpu.get('temperature_c'),(int,float)):return {gpu.get('name','Discrete GPU'):gpu['temperature_c']}
        for reading in temperatures:
            if reading['name']=='acer / temp2_input':return {'GPU (Acer sensor)':reading['celsius']}
        return {}
    def monitor_changed(self):
        self.chart.clear();self.chart.maximum=100 if self.monitor.currentData()=='usage' else 120;self.chart.units='%' if self.monitor.currentData()=='usage' else '°C';self.refresh()
    def clear_history(self):
        self.history.clear();self.chart.clear()
    def export_history(self):
        path,_=QFileDialog.getSaveFileName(self,'Export measured history','nitrosense-history.csv','CSV files (*.csv)')
        if not path:return
        try:
            with open(path,'w',newline='') as stream:
                writer=csv.writer(stream);writer.writerow(['utc','view','sensor','value','unit'])
                for row in self.history:
                    for name,value in row['readings'].items():writer.writerow([row['utc'],row['view'],name,value,row.get('unit','%' if row['view']=='usage' else 'C')])
        except OSError as exc:error(self,'Export failed',exc)
    def show_sensors(self):
        dialog=QDialog(self);dialog.setWindowTitle('Live device readings');dialog.setStyleSheet(STYLE);layout=QVBoxLayout(dialog)
        text='\n'.join(f"{v['name']}: {v['celsius']:.1f} °C" for v in self.state.get('temperatures',[]))
        text+='\n\n'+'\n'.join(f"{v['name']}: {v['rpm']} RPM" for v in self.state.get('fans',[]))
        gpu=self.state.get('gpu') or {}
        if gpu:text+='\n\n'+json.dumps(gpu,indent=2)
        label=QLabel(text or 'No readable sensors');label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);layout.addWidget(label)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons);dialog.exec()
    def change_fans(self,mode):
        try:
            if mode in (0,1):
                value=0 if mode==0 else 100;self.backend.set_fans(value,value);self.current_profile['fan']={'cpu':value,'gpu':value};self._custom_editing=False;self.show_inline_fans(False)
            else:self.custom_fans()
            self.refresh()
        except Exception as exc:error(self,'Fan request failed',exc);self.refresh()
    def show_inline_fans(self,visible):
        available=bool(self.state.get('fan_control_available'))
        for controls in self.inline_fans:
            controls['panel'].setVisible(visible)
            controls['auto'].setEnabled(available)
            controls['slider'].setEnabled(available and not controls['auto'].isChecked())
        self.inline_apply.setVisible(visible);self.inline_apply.setEnabled(available)
    def sync_inline_fans(self,request):
        for controls in self.inline_fans:
            number=request.get(controls['key'],0)
            blocker=QSignalBlocker(controls['auto'])
            controls['auto'].setChecked(number==0)
            del blocker
            blocker=QSignalBlocker(controls['slider'])
            if number:controls['slider'].setValue(number);controls['value'].setText(f'{number}%')
            del blocker
            controls['slider'].setEnabled(bool(self.state.get('fan_control_available')) and number!=0)
    def custom_fans(self):
        self.sync_inline_fans(self.state.get('fan_request') or self.current_profile['fan'])
        self._custom_editing=True;self.mode_buttons[2].setChecked(True);self.show_inline_fans(True)
        self.fan_request_label.setText('Custom settings pending Apply')
    def mark_custom_pending(self,*_):
        self._custom_editing=True;self.fan_request_label.setText('Custom settings pending Apply')
    def apply_inline_fans(self):
        try:
            values=[0 if controls['auto'].isChecked() else controls['slider'].value() for controls in self.inline_fans]
            self.backend.set_fans(*values);self.current_profile['fan']=dict(zip(('cpu','gpu'),values));self._custom_editing=False;self.refresh()
        except Exception as exc:error(self,'Fan request failed',exc)
    def set_coolboost(self,checked):
        try:self.backend.set_coolboost(checked);self.refresh()
        except Exception as exc:error(self,'CoolBoost unavailable',exc);self.coolboost.setChecked(not checked)
    def set_power(self,name):
        try:self.backend.set_power_profile(name);self.refresh()
        except Exception as exc:error(self,'Power profile failed',exc);self.refresh()
    def show_lighting(self):
        dialog=LightingDialog(self.backend,self.state,self.current_profile['lighting'],self);dialog.exec()
    def show_settings(self):
        SettingsDialog(self).exec()
    def quit(self):
        self._quitting=True;self.close()
    def closeEvent(self,event):
        if not self._quitting and self.store.preferences.get('minimize_to_tray') and self.tray:
            self.hide();event.ignore();return
        self._closing=True
        self.timer.stop()
        if not self.pool.waitForDone(10000):
            self._closing=False
            self.status.setText('Waiting for a telemetry command to finish; please retry Quit shortly.')
            self.timer.start(2000)
            event.ignore();return
        try:self.backend.close()
        except Exception as exc:
            self._closing=False;self.timer.start(2000)
            error(self,'Automatic fan restoration failed',exc);event.ignore();return
        for art in self.fan_art:art.animation.stop()
        if self.tray:self.tray.hide()
        event.accept()
        QApplication.instance().quit()


class SettingsDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.setWindowTitle('NitroSense settings');self.setStyleSheet(STYLE);self.resize(650,500)
        layout=QVBoxLayout(self);tabs=QTabWidget();layout.addWidget(tabs)
        device=QWidget();form=QFormLayout(device);self.switch_controls={}
        titles={'backlight_timeout':'Keyboard backlight timeout','battery_limiter':'Battery charge limit (80%)','usb_charging':'USB charging battery threshold'}
        for name,title in titles.items():
            info=window.state.get('switches',{}).get(name,{})
            if name=='usb_charging':
                control=QComboBox()
                for choice in info.get('choices',[0,10,20,30]):control.addItem('Off' if choice==0 else f'{choice}%',choice)
                control.setCurrentIndex(max(0,control.findData(info.get('value'))))
            else:
                control=QCheckBox();control.setChecked(info.get('value')==1)
            control.setEnabled(bool(info.get('available')));control.setToolTip(info.get('reason','Interface unavailable'))
            form.addRow(title,control);self.switch_controls[name]=(control,info.get('value'))
        apply=QPushButton('Apply device settings');apply.clicked.connect(self.apply_switches);form.addRow(apply)
        note=QLabel('Battery calibration is intentionally not automated. DTS/TrueHarmony audio processing requires Acer’s Windows components and is unavailable on Linux.');note.setWordWrap(True);form.addRow(note)
        tabs.addTab(device,'Device')
        profiles=QWidget();pl=QVBoxLayout(profiles);self.profiles=QComboBox();self.reload_profiles();pl.addWidget(self.profiles)
        note=QLabel('Selecting or importing a profile does not change hardware. Apply sends the selected fan and lighting requests.');note.setWordWrap(True);pl.addWidget(note)
        for text,callback in [('Save current controls as profile',self.save_profile),('Apply selected profile',self.apply_profile),('Import profile JSON',self.import_profile),('Export selected profile',self.export_profile)]:
            button=QPushButton(text);button.clicked.connect(callback);pl.addWidget(button)
        pl.addStretch();tabs.addTab(profiles,'Profiles')
        app=QWidget();al=QVBoxLayout(app)
        self.tray=QCheckBox('Keep running in the system tray when the window closes');self.tray.setChecked(window.store.preferences['minimize_to_tray']);self.tray.setEnabled(window.tray is not None)
        self.tray.toggled.connect(self.save_preferences);al.addWidget(self.tray)
        unit_row=QFormLayout();self.units=QComboBox();self.units.addItem('Celsius (°C)','C');self.units.addItem('Fahrenheit (°F)','F')
        self.units.setCurrentIndex(max(0,self.units.findData(window.store.preferences.get('temperature_unit','C'))))
        self.units.currentIndexChanged.connect(self.save_preferences);unit_row.addRow('Temperature units',self.units);al.addLayout(unit_row)
        note=QLabel('Manual fans return to firmware automatic control when the application exits normally. Closing to the tray keeps manual control active. Profiles are stored locally and never applied automatically at startup.');note.setWordWrap(True);al.addWidget(note)
        if window.store.error:al.addWidget(QLabel('Previous settings could not be read: '+window.store.error))
        al.addStretch();tabs.addTab(app,'Application')
        about=QWidget();abl=QVBoxLayout(about);label=QLabel('NitroSense Linux\nNative Qt desktop application for Acer Nitro AN515-45\n\nIndependent reconstruction; not affiliated with Acer.\nLinux hardware access uses Linuwu-Sense.\n\nDevice command acceptance does not prove visible keyboard effects.\nExact Windows pixel and audio parity is not established.');label.setWordWrap(True);abl.addWidget(label);abl.addStretch();tabs.addTab(about,'About')
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
    def apply_switches(self):
        try:
            for name,(control,previous) in self.switch_controls.items():
                if not control.isEnabled():continue
                value=control.currentData() if isinstance(control,QComboBox) else int(control.isChecked())
                if value!=previous:self.window.backend.set_switch(name,value);self.switch_controls[name]=(control,value)
            self.window.refresh();QMessageBox.information(self,'Device settings','Device settings were accepted.')
        except Exception as exc:error(self,'Device setting failed',exc)
    def save_preferences(self):
        try:
            self.window.store.preferences['minimize_to_tray']=self.tray.isChecked()
            if hasattr(self,'units'):self.window.store.preferences['temperature_unit']=self.units.currentData()
            self.window.store.save();self.window.chart.clear();self.window.refresh()
        except OSError as exc:error(self,'Settings could not be saved',exc)
    def reload_profiles(self):
        self.profiles.clear()
        for profile in self.window.store.profiles:self.profiles.addItem(profile['name'],profile)
    def save_profile(self):
        name,ok=QInputDialog.getText(self,'Save profile','Profile name')
        if not ok:return
        try:
            value=json.loads(json.dumps(self.window.current_profile));value['name']=name;self.window.store.put(value);self.reload_profiles()
        except (OSError,ValueError) as exc:error(self,'Profile could not be saved',exc)
    def apply_profile(self):
        profile=self.profiles.currentData()
        if not profile:return
        fan_applied=False
        try:
            profile=validate_profile(profile);self.window.backend.set_fans(profile['fan']['cpu'],profile['fan']['gpu']);fan_applied=True
            p=profile['lighting']
            if p['type']=='static':self.window.backend.set_lighting_static(p['colors'],p['brightness'])
            else:self.window.backend.set_lighting_dynamic(p['mode'],p['speed'],p['brightness'],p['direction'],p['color'])
            self.window.current_profile=profile;self.window.refresh();QMessageBox.information(self,'Profile applied','Fan and lighting requests were accepted. Check visible lighting on the keyboard.')
        except Exception as exc:
            if fan_applied:
                try:self.window.backend.set_fans(0,0)
                except Exception as restore:exc=RuntimeError(f'{exc}\nAutomatic fan restoration also failed: {restore}')
            error(self,'Profile was not fully applied',exc)
    def import_profile(self):
        path,_=QFileDialog.getOpenFileName(self,'Import profile','','JSON files (*.json)')
        if not path:return
        try:self.window.store.import_file(path);self.reload_profiles()
        except (OSError,ValueError,TypeError) as exc:error(self,'Invalid profile',exc)
    def export_profile(self):
        profile=self.profiles.currentData()
        if not profile:return
        path,_=QFileDialog.getSaveFileName(self,'Export profile','nitrosense-profile.json','JSON files (*.json)')
        if not path:return
        try:self.window.store.export_file(profile,path)
        except (OSError,ValueError) as exc:error(self,'Profile export failed',exc)


def run(backend=None,smoke_test=False):
    app=QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName('NitroSense Linux');app.setOrganizationName('NitroSense Linux')
    window=NitroWindow(backend);window.show()
    previous_handlers={}
    for sig in (signal.SIGINT,signal.SIGTERM):
        try:
            previous_handlers[sig]=signal.signal(sig,lambda *_:QTimer.singleShot(0,window.quit))
        except ValueError:
            pass  # Embedders may run Qt outside Python's main thread.
    heartbeat=QTimer();heartbeat.timeout.connect(lambda:None);heartbeat.start(200)
    failure=[0]
    if smoke_test:
        def finish():
            explicit=os.environ.get('NITRO_SENSE_SCREENSHOT')
            local=Path.cwd()/'evidence'
            cache=Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'nitro-sense'
            target=Path(explicit) if explicit else (local if local.is_dir() else cache)/'ui-preview.png'
            try:
                target.parent.mkdir(parents=True,exist_ok=True)
                if not window.grab().save(str(target)):
                    raise OSError('Qt could not encode screenshot')
            except OSError as exc:
                failure[0]=1;print(f'Screenshot failed: {exc}',file=sys.stderr)
            window.quit()
        QTimer.singleShot(1200,finish)
    try:
        return max(app.exec(),failure[0])
    finally:
        heartbeat.stop()
        for sig,handler in previous_handlers.items():signal.signal(sig,handler)
