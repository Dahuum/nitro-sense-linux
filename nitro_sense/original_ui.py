"""Original Octavia shell and recovered native interaction contract.

This view is based on the selected AN515-45 XAML/handlers, not a Windows runtime
capture. Linux-only tools remain in a separate F10 extension window.
"""
from __future__ import annotations
import copy
import math
import os
from pathlib import Path
import signal
import sys
import time
from PySide6.QtCore import QEvent, QPoint, QPointF, QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import QApplication, QAbstractButton, QButtonGroup, QCheckBox, QDialog, QLabel, QMessageBox, QRadioButton, QWidget
from .ui import NitroWindow as LinuxWindow, Skin, FanArt, SettingsDialog, ASSETS, error
from .original_controls import LocalPaths, OriginalIconButton, OriginalFanMode, OriginalToggle
from .original_monitoring import OriginalMonitoringWidget, OriginalPowerWidget
from .original_lighting import OriginalLightingDialog


class OriginalSkin(Skin):
    def paintEvent(self, event):
        if ASSETS:
            # The user's original background child image supplies its alpha.
            return
        super().paintEvent(event)


class OriginalFanArt(FanArt):
    """Original negative rotation period from Nitro_FanControlPage.cs."""
    @staticmethod
    def period(rpm):
        return 2 if rpm > 4500 else max(1, 11 - int(rpm / 450))
    def advance(self):
        if self.rpm:
            self.angle=(self.angle-360 / self.period(self.rpm)*.04)%360
            self.update()


class OriginalSettingsPopup(QDialog):
    def __init__(self, window):
        super().__init__(window, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.window=window
        self.setFixedSize(340,219)
        self.setStyleSheet('QDialog {background:#dadada;} QLabel,QCheckBox,QRadioButton {color:#191919;background:transparent;font-family:"Segoe UI";font-size:14px;} QRadioButton::indicator {width:18px;height:18px;}')
        self.setAccessibleName('Setting Menu')
        def label(text,y,bold=False):
            item=QLabel(text,self);item.setGeometry(15,y,245,25)
            if bold:item.setStyleSheet('font-weight:bold;')
            return item
        label('Advanced Settings',25,True)
        label('Sticky keys',55)
        label('Windows and menu key',91)
        label('Temperature units',127)
        label('Keyboard Settings',158,True)
        label('Backlight off after 30 seconds',187)
        self.sticky=OriginalToggle(self);self.sticky.move(278,58)
        self.windows_keys=OriginalToggle(self);self.windows_keys.move(278,94)
        for control in (self.sticky,self.windows_keys):
            control.setEnabled(False);control.setToolTip('This Windows input feature has no verified Linux backend.')
        self.celsius=QRadioButton('˚C',self);self.celsius.setGeometry(219,128,55,20)
        self.fahrenheit=QRadioButton('˚F',self);self.fahrenheit.setGeometry(278,128,55,20)
        self.celsius.setChecked(window.store.preferences.get('temperature_unit')!='F')
        self.fahrenheit.setChecked(window.store.preferences.get('temperature_unit')=='F')
        self.celsius.clicked.connect(lambda:window.set_units('C'))
        self.fahrenheit.clicked.connect(lambda:window.set_units('F'))
        self.backlight=OriginalToggle(self);self.backlight.move(278,188)
        info=window.state.get('switches',{}).get('backlight_timeout',{})
        self.backlight.setChecked(info.get('value')==1);self.backlight.setEnabled(bool(info.get('available')))
        self.backlight.setToolTip(info.get('reason','Interface unavailable'))
        self.backlight.clicked.connect(self.change_backlight)
    def change_backlight(self,checked):
        try:self.window.backend.set_switch('backlight_timeout',int(checked));self.window.refresh()
        except Exception as exc:
            with QSignalBlocker(self.backlight):self.backlight.setChecked(not checked)
            error(self,'Backlight timeout unavailable',exc)
    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape:self.reject()
        else:super().keyPressEvent(event)
    def closeEvent(self,event):
        self.window.header['settings'].setFocus();super().closeEvent(event)


class OriginalNitroWindow(LinuxWindow):
    def create_canvas(self):
        canvas=OriginalSkin();canvas.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);return canvas
    def __init__(self,backend=None,profile_store=None):
        self._original_ready=False;self._mode=None;self._last_graph=-math.inf;self._last_fan=-math.inf;self._syncing=False
        super().__init__(backend,profile_store)
        self.setWindowTitle('NitroSense')
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet('QGraphicsView {border:0;background:transparent;}')
        self.viewport().setStyleSheet('background:transparent;')
        self.setFixedSize(1320,760);self.canvas.setFixedSize(1320,760);self.scene().setSceneRect(0,0,1320,760)
        # Remove the extension-only footer, selector, CSV and modern toolbar from
        # the recovered shell. They remain available through F10.
        for child in self.canvas.findChildren(QWidget,options=Qt.FindChildOption.FindDirectChildrenOnly):
            if child.y()>=404 or isinstance(child,QAbstractButton) and child.y()==52:
                child.hide()
            if isinstance(child,QLabel):child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.status.hide();self.fan_request_label.hide();self.inline_apply.hide()
        self.paths=LocalPaths(ASSETS)
        for index,old in enumerate(self.mode_buttons):
            self.mode_group.removeButton(old);old.hide();old.deleteLater()
        self.mode_buttons=[]
        for index,title in enumerate(('Auto','Max','Custom')):
            button=OriginalFanMode(title,self.canvas,self.paths);button.move(120,170+68*index)
            self.mode_group.addButton(button,index);button.clicked.connect(lambda checked=False,mode=index:self.change_fans(mode))
            self.mode_buttons.append(button)
        for index,old in enumerate(self.fan_art):
            old.animation.stop();old.hide();old.deleteLater()
        self.fan_art=[]
        for x,label in zip((540,756),self.fan_values):
            pixmap=None
            if ASSETS:
                from PySide6.QtGui import QPixmap
                pixmap=QPixmap(str(ASSETS/'images/100/img_fan.png'))
            art=OriginalFanArt(self.canvas,pixmap);art.setGeometry(x,152,200,200);art.stackUnder(label);self.fan_art.append(art)
            font=label.font();font.setBold(True);label.setFont(font)
        for index,controls in enumerate(self.inline_fans):
            slider=controls['slider'];automatic=controls['auto'];controls['panel'].setFixedSize(160,65)
            slider.setGeometry(0,0,160,28);slider.setRange(0,10);slider.setSingleStep(1);slider.setPageStep(1)
            controls['value'].hide();automatic.setGeometry(80 if index==0 else 0,40,80,20)
            automatic.clicked.disconnect();slider.sliderPressed.disconnect();slider.sliderReleased.disconnect();slider.valueChanged.disconnect()
            automatic.clicked.connect(self.original_auto_changed)
            slider.sliderReleased.connect(self.apply_inline_fans)
            slider.valueChanged.connect(lambda value,i=index:self.slider_changed(i,value))
            saved=copy.deepcopy(self.store.preferences.get('original_custom',{}))
            slider.setValue(int(saved.get(controls['key'],50))//10)
            automatic.setChecked(bool(saved.get(controls['key']+'_auto',True)))
        self.coolboost.hide()
        self.coolboost=OriginalToggle(self.canvas);self.coolboost.move(1154,126);self.coolboost.setAccessibleName('CoolBoost status')
        self.coolboost.clicked.connect(self.set_coolboost)
        self.label('CoolBoost',1040,124,92,24,14).show()
        self.info_button=self.button('i',1133,128,16,16);self.info_button.setStyleSheet('border:1px solid #666;border-radius:8px;padding:0;color:#808080;font-size:11px;')
        self.info_button.clicked.connect(self.show_coolboost_info)
        self.header={}
        for kind,x,y,width,height in [('lighting',1025,54,35,26),('sound',1075,54,35,26),('settings',1125,54,26,26),('minimize',1166,57,28,20),('close',1209,57,26,20),('planet',987,55,18,27)]:
            button=OriginalIconButton(kind,self.canvas,self.paths);button.setGeometry(x,y,width,height);self.header[kind]=button
        self.header['close'].clicked.connect(self.quit)
        self.header['minimize'].clicked.connect(self.showMinimized)
        self.header['settings'].clicked.connect(self.show_settings)
        self.header['lighting'].clicked.connect(self.show_lighting)
        self.header['sound'].clicked.connect(self.show_sound)
        self.header['planet'].clicked.connect(self.show_planet)
        self.original_monitor=OriginalMonitoringWidget(self.canvas,assets=ASSETS);self.original_monitor.move(396,404)
        self.original_power=OriginalPowerWidget(self.backend,self.canvas);self.original_power.move(84,404)
        self.original_power.operationFailed.connect(lambda message:error(self,'Power profile unavailable',message))
        self.original_monitor.set_units(self.store.preferences.get('temperature_unit','C'))
        self.extension_shortcut=QShortcut(QKeySequence('F10'),self);self.extension_shortcut.activated.connect(self.show_extensions)
        self.canvas.installEventFilter(self);self._drag=None
        self.timer.setInterval(4000)
        self.fan_timer=QTimer(self);self.fan_timer.setInterval(5000);self.fan_timer.timeout.connect(self.refresh);self.fan_timer.start()
        self._original_ready=True
        for control in list(self.header.values()) + self.mode_buttons + self.fan_art + [self.coolboost,self.info_button,self.original_monitor,self.original_power]:
            control.show()
        self._fan_snapshot=[]
        self._monitor_snapshot={}
        if self.state:self.apply_state(self.state)
    def eventFilter(self,obj,event):
        if obj is getattr(self,'canvas',None):
            if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton and event.position().y()<92:
                self._drag=event.globalPosition().toPoint()-self.frameGeometry().topLeft();return True
            if event.type()==QEvent.Type.MouseMove and self._drag is not None:
                self.move(event.globalPosition().toPoint()-self._drag);return True
            if event.type()==QEvent.Type.MouseButtonRelease:self._drag=None
        return super().eventFilter(obj,event)
    def apply_state(self,state):
        if not self._original_ready:
            super().apply_state(state);return
        # Keep Linux extension telemetry/history functional, but hidden from the
        # original shell. No checked-state signal performs a hardware write.
        now=time.monotonic()
        if now-self._last_fan>=4.9:
            self._fan_snapshot=copy.deepcopy(state.get('fans',[]));self._last_fan=now
        state=dict(state,fans=self._fan_snapshot)
        super().apply_state(state)
        if self._mode is None:
            request=state.get('fan_request') or {'cpu':0,'gpu':0}
            self._mode=0 if request['cpu']==request['gpu']==0 else 1 if request['cpu']==request['gpu']==100 else 2
        for index,button in enumerate(self.mode_buttons):button.setChecked(index==self._mode)
        self.show_inline_fans(self._mode==2)
        self.coolboost.setEnabled(bool(state.get('capabilities',{}).get('coolboost')) and self._mode==0)
        self.original_power.update_state(state)
        append=now-self._last_graph>=3.9
        if append:self._last_graph=now;self._monitor_snapshot=copy.deepcopy(state)
        self.original_monitor.update_state(self._monitor_snapshot,append=append)
        self.status.hide();self.fan_request_label.hide();self.inline_apply.hide()
    def show_inline_fans(self,visible):
        if not self._original_ready:
            return super().show_inline_fans(visible)
        available=bool(self.state.get('fan_control_available'))
        for controls in self.inline_fans:
            controls['panel'].setVisible(visible);controls['auto'].setEnabled(available)
            controls['slider'].setEnabled(available and not controls['auto'].isChecked())
        self.inline_apply.hide()
    def sync_inline_fans(self,request):
        # Custom values are separate saved controls in the original. Auto/Max
        # queries must not erase those stored percentages and Auto flags.
        if not self._original_ready:return super().sync_inline_fans(request)
    def change_fans(self,mode):
        try:
            if mode in (0,1):self.backend.set_fans(0 if mode==0 else 100,0 if mode==0 else 100)
            else:self.apply_inline_fans()
            self._mode=mode;self._custom_editing=False
            self.show_inline_fans(mode==2)
            for index,button in enumerate(self.mode_buttons):button.setChecked(index==mode)
            self.coolboost.setEnabled(bool(self.state.get('capabilities',{}).get('coolboost')) and mode==0)
            self.refresh()
        except Exception as exc:error(self,'Fan request failed',exc)
    def original_auto_changed(self):
        if self._mode==2:self.apply_inline_fans()
        self.show_inline_fans(self._mode==2)
    def slider_changed(self,index,value):
        if not self._original_ready or self._syncing:return
        if self._mode==2 and not self.inline_fans[index]['slider'].isSliderDown():self.apply_inline_fans()
    def apply_inline_fans(self):
        values=[0 if c['auto'].isChecked() else c['slider'].value()*10 for c in self.inline_fans]
        self.backend.set_fans(*values)
        self.current_profile['fan']=dict(zip(('cpu','gpu'),values))
        self.store.preferences['original_custom']={key:value for c in self.inline_fans for key,value in ((c['key'],c['slider'].value()*10),(c['key']+'_auto',c['auto'].isChecked()))}
        self.store.save();self.refresh()
    def set_units(self,units):
        self.store.preferences['temperature_unit']=units;self.store.save()
        self.original_monitor.set_units(units);self.refresh()
    def show_settings(self):
        self._settings_popup=OriginalSettingsPopup(self)
        point=self.header['settings'].mapToGlobal(QPoint(-231,31))
        self._settings_popup.move(point);self._settings_popup.show()
        self._settings_popup.sticky.setFocus()
    def show_extensions(self):SettingsDialog(self).exec()
    def show_lighting(self):
        if not self.state.get('lighting_available'):
            error(self,'Keyboard lighting unavailable',self.state.get('lighting_reason','Driver interface unavailable'));return
        dialog=OriginalLightingDialog(self.backend,self.state,self.current_profile['lighting'],self.canvas,assets=ASSETS,recent_colors=self.store.preferences.get('recent_colors',[]))
        dialog.setWindowFlags(Qt.WindowType.Widget);dialog.setGeometry(0,0,1320,760)
        dialog.profileChanged.connect(lambda value:self.current_profile.__setitem__('lighting',value))
        dialog.recentColorsChanged.connect(self.save_recent)
        dialog.finished.connect(lambda *_:self.header['lighting'].setFocus())
        self._lighting_overlay=dialog;dialog.show();dialog.raise_();dialog.setFocus()
    def save_recent(self,colors):
        self.store.preferences['recent_colors']=list(colors)[:9];self.store.save()
    def show_coolboost_info(self):
        QMessageBox.information(self,'CoolBoost','CoolBoost increases fan speed to improve cooling. This control is available in Auto fan mode.')
    def show_sound(self):
        QMessageBox.information(self,'Sound Mode','The original audio modes require the original Windows audio components. No supported Linux audio-mode backend is available.')
    def show_planet(self):
        # Preserve the button affordance; opening an external promotional URL
        # remains a deliberate separate click.
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        popup=QMessageBox(self);popup.setWindowTitle('Planet9');popup.setText('Planet9')
        visit=popup.addButton('Join now',QMessageBox.ButtonRole.ActionRole);popup.addButton(QMessageBox.StandardButton.Close)
        popup.exec()
        if popup.clickedButton() is visit:QDesktopServices.openUrl(QUrl('https://p9.gg/NitroSense'))
    def clear_history(self):
        super().clear_history()
        if self._original_ready:self.original_monitor.clear()
    def closeEvent(self,event):
        # The original X means shutdown. Its separate minimize button minimizes.
        self._quitting=True
        if hasattr(self,'fan_timer'):self.fan_timer.stop()
        super().closeEvent(event)


def run(backend=None,smoke_test=False):
    app=QApplication.instance() or QApplication(sys.argv);app.setApplicationName('NitroSense Linux')
    window=OriginalNitroWindow(backend);window.show()
    previous={}
    for sig in (signal.SIGINT,signal.SIGTERM):
        try:previous[sig]=signal.signal(sig,lambda *_:QTimer.singleShot(0,window.quit))
        except ValueError:pass
    heartbeat=QTimer();heartbeat.timeout.connect(lambda:None);heartbeat.start(200)
    result=[0]
    if smoke_test:
        def finish():
            path=Path(os.environ.get('NITRO_SENSE_SCREENSHOT',str(Path.home()/'.cache/nitro-sense/original-ui.png')))
            try:
                path.parent.mkdir(parents=True,exist_ok=True)
                if not window.grab().save(str(path)):raise OSError('Screenshot could not be encoded')
            except OSError as exc:result[0]=1;print(exc,file=sys.stderr)
            window.quit()
        QTimer.singleShot(1200,finish)
    try:return max(app.exec(),result[0])
    finally:
        heartbeat.stop()
        for sig,handler in previous.items():signal.signal(sig,handler)
