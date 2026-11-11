"""Native controls following the recovered 100% DPI control contracts.

Optional original vector artwork is loaded from the user's local resource cache,
never shipped in the Python package. Fallback drawings are independent artwork.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape
from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QAbstractButton, QCheckBox, QPushButton


class LocalPaths:
    def __init__(self, assets=None):
        self.resources = {}
        if assets:
            try:
                path = Path(assets) / 'original-style-paths.json'
                if path.stat().st_size < 2 * 1024 * 1024:
                    self.resources = json.loads(path.read_text())
            except (OSError, ValueError, TypeError):
                pass

    def paint(self, painter, key, target, color):
        items = self.resources.get(key, [])
        if not items:
            return False
        # These templates use one normal-state vector icon. A local cache is
        # passive geometry, not executable XAML or an application assembly.
        item = items[0]
        data = item.get('data', '').removeprefix('F1 ').removeprefix('F0 ')
        svg = f'<svg xmlns="http://www.w3.org/2000/svg"><path id="shape" fill="{color}" d="{escape(data, {chr(34): "&quot;"})}"/></svg>'
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        if not renderer.isValid():
            return False
        bounds = renderer.boundsOnElement('shape')
        if bounds.isEmpty():
            return False
        renderer.setViewBox(bounds)
        renderer.render(painter, target)
        return True


class OriginalIconButton(QPushButton):
    def __init__(self, kind, parent=None, paths=None):
        super().__init__(parent)
        self.kind = kind
        self.paths = paths or LocalPaths()
        self.setAccessibleName({'close':'Close window','minimize':'Minimize window','settings':'Settings',
                                'lighting':'Keyboard lighting','sound':'Sound mode','planet':'Planet9'}[kind])
        self.setToolTip(self.accessibleName())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet('QPushButton {border:0;background:transparent;padding:0;}')
        if kind in ('close','minimize'):
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = '#e60000' if self.isDown() else '#cccccc' if self.underMouse() or self.hasFocus() else '#808080'
        key = {'close':'CloseButton_ControlTemplate','minimize':'MinimizeButton_ControlTemplate',
               'settings':'SettingButton_ControlTemplate','lighting':'LightingButton_ControlTemplate',
               'sound':'SoundModeButton_ControlTemplate','planet':'Planet9SettingButton_ControlTemplate'}[self.kind]
        if self.paths.paint(p,key,QRectF(self.rect()).adjusted(1,1,-1,-1),color):
            return
        p.setPen(QPen(QColor(color),2.5));p.setBrush(Qt.BrushStyle.NoBrush)
        if self.kind == 'close':
            p.drawLine(3,2,self.width()-3,self.height()-2);p.drawLine(3,self.height()-2,self.width()-3,2)
        elif self.kind == 'minimize':
            p.drawLine(3,self.height()-3,self.width()-3,self.height()-3)
        elif self.kind == 'lighting':
            p.drawRect(QRectF(2,8,self.width()-7,self.height()-10))
            for row in range(2):
                for column in range(4):p.fillRect(QRectF(6+column*5,12+row*5,3,3),QColor(color))
            for x in (10,17,24):p.drawLine(x,1,x,5)
        elif self.kind == 'sound':
            for x,height in [(4,8),(10,17),(16,24),(22,13),(28,7)]:p.drawLine(x,(self.height()-height)//2,x,(self.height()+height)//2)
        elif self.kind == 'settings':
            center = QPointF(self.width()/2,self.height()/2)
            p.drawEllipse(center,7,7);p.drawEllipse(center,2,2)
            for angle in range(0,360,45):
                rad=math.radians(angle);p.drawLine(center+QPointF(math.cos(rad)*8,math.sin(rad)*8),center+QPointF(math.cos(rad)*11,math.sin(rad)*11))
        else:
            p.drawEllipse(QRectF(1,1,self.width()-2,self.height()-2));p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,'9')


class OriginalFanMode(QAbstractButton):
    def __init__(self, title, parent=None, paths=None):
        super().__init__(parent);self.setText(title);self.setCheckable(True)
        self.setAccessibleName(title);self.paths=paths or LocalPaths()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(220,56)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color='#e60000' if self.isChecked() else '#b2b2b2' if self.underMouse() else '#4c4c4c'
        if not self.isEnabled():p.setOpacity(.4)
        key={'Auto':'Nitro_FanModeAutoStyle','Max':'Nitro_FanModeMaxStyle','Custom':'Nitro_FanModeCustomStyle'}[self.text()]
        width=36 if self.text()=='Auto' else 29
        if not self.paths.paint(p,key,QRectF(7,14,width,28),color):
            p.setPen(QPen(QColor(color),2));p.drawEllipse(QRectF(9,16,24,24))
            for angle in range(0,360,60):
                rad=math.radians(angle);p.drawLine(QPointF(21+math.cos(rad)*5,28+math.sin(rad)*5),QPointF(21+math.cos(rad)*11,28+math.sin(rad)*11))
            if self.text()=='Auto':p.drawText(QRectF(29,28,13,16),Qt.AlignmentFlag.AlignCenter,'A')
        p.setPen(QColor(color));font=p.font();font.setPixelSize(15);p.setFont(font)
        p.drawText(QRectF(54,0,166,56),Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft,self.text())
        if self.hasFocus():
            p.setPen(QPen(QColor('#999999'),1,Qt.PenStyle.DotLine));p.drawRect(self.rect().adjusted(1,1,-2,-2))


class OriginalToggle(QCheckBox):
    def __init__(self,parent=None):
        super().__init__(parent);self.setFixedSize(52,20);self.setCursor(Qt.CursorShape.PointingHandCursor)
    def hitButton(self,pos):return self.rect().contains(pos)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():p.setOpacity(.4)
        checked=self.isChecked();p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#005966' if checked else '#242424'))
        p.drawPolygon(QPolygonF([QPointF(0,10),QPointF(10,0),QPointF(42,0),QPointF(52,10),QPointF(42,20),QPointF(10,20)]))
        p.setBrush(QColor('#00aec7' if checked else '#4c4c4c'))
        x=23 if checked else 3
        p.drawPolygon(QPolygonF([QPointF(x,10),QPointF(x+8,2),QPointF(x+18,2),QPointF(x+26,10),QPointF(x+18,18),QPointF(x+8,18)]))
        if self.hasFocus():
            p.setPen(QPen(QColor('#888888'),1,Qt.PenStyle.DotLine));p.setBrush(Qt.BrushStyle.NoBrush);p.drawRect(self.rect().adjusted(0,0,-1,-1))
