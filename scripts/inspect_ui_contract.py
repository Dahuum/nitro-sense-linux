#!/usr/bin/env python3
"""Export bounded original UI facts from the user's recovered local XAML.

This does not execute Acer code or publish original XAML, vector paths, bitmap
payloads, string dictionaries or decompiled method bodies. Grid/style resolution
is deliberately partial: declared properties and named derived shell bounds are
reported separately rather than claiming a general WPF layout engine.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

XAML = '{http://schemas.microsoft.com/winfx/2006/xaml}'
ASSEMBLY_SHA256 = 'f71a2eebf07f11e91337a0f5de7feefda54e96d8b007d3904adf4f459856b2cd'
FILES = {
    'shell': 'NitroSense.Nitro_MainWindow_Octavia.xaml',
    'fan': 'NitroSense.Nitro_FanControlPage.xaml',
    'monitoring': 'NitroSense.Nitro_MonitoringPage.xaml',
    'monitoring_acer_mode': 'NitroSense.Nitro_MonitoringPage_Acermode.xaml',
    'lighting': 'NitroSense.Popup_Lighting.xaml',
    'dynamic_lighting': 'NitroSense.LightingDynamicUI.xaml',
    'custom_color': 'NitroSense.More_color_picker.xaml',
    'style': 'style/100/psstyle.xaml',
    'language': 'lang/en.xaml',
}
PROPERTIES = {'Width', 'Height', 'Margin', 'Padding', 'FontSize', 'FontFamily',
    'FontWeight', 'HorizontalAlignment', 'VerticalAlignment', 'Visibility',
    'IsEnabled', 'Focusable', 'IsTabStop', 'TabIndex', 'Minimum', 'Maximum',
    'SmallChange', 'LargeChange', 'Row', 'Column', 'RowSpan', 'ColumnSpan',
    'Grid.Row', 'Grid.Column', 'Grid.RowSpan', 'Grid.ColumnSpan', 'Canvas.Left',
    'Canvas.Top', 'WindowStyle', 'AllowsTransparency', 'ResizeMode', 'Stretch',
    'Placement', 'HorizontalOffset', 'VerticalOffset', 'StaysOpen'}
EVENTS = {'Click', 'Checked', 'Unchecked', 'Opened', 'Closed', 'MouseDown',
    'MouseEnter', 'MouseLeave', 'MouseMove', 'MouseLeftButtonDown', 'ValueChanged',
    'SelectionChanged', 'IsEnabledChanged', 'Thumb.DragStarted',
    'Thumb.DragCompleted', 'Closing', 'Loaded', 'Initialized', 'SourceInitialized',
    'StateChanged', 'MouseRightButtonDown'}


def value(text):
    if text in ('True', 'False', 'true', 'false'):
        return text.lower() == 'true'
    try:
        number = float(text)
        return int(number) if number.is_integer() else number
    except ValueError:
        pass
    return text


def local(tag):
    return tag.rsplit('}', 1)[-1]


def facts(path):
    root = ET.parse(path).getroot()
    result = {'root_type': local(root.tag), 'root_properties': {}, 'controls': {}}
    result['root_properties'] = {k: value(v) for k, v in root.attrib.items() if k in PROPERTIES}
    for node in root.iter():
        name = node.get('Name') or node.get(XAML + 'Name')
        if not name:
            continue
        properties = {k: value(v) for k, v in node.attrib.items() if k in PROPERTIES}
        handlers = {k: v for k, v in node.attrib.items() if k in EVENTS}
        record = {'type': local(node.tag), 'properties': properties}
        if handlers:
            record['handlers'] = handlers
        rows, columns = [], []
        for child in node:
            if local(child.tag) == 'Grid.RowDefinitions':
                rows = [value(x.get('Height', '*')) for x in child]
            if local(child.tag) == 'Grid.ColumnDefinitions':
                columns = [value(x.get('Width', '*')) for x in child]
        if rows:
            record['rows'] = rows
        if columns:
            record['columns'] = columns
        result['controls'][name] = record
    return result


def shell_bounds():
    # Derived from the shell's explicit 84/92 origin plus FanControlPage grid
    # columns/rows. Header button Y uses WPF's centered available size after
    # top margin, not top margin itself.
    return {
        'window': [0, 0, 1320, 760],
        'content': [84, 92, 1152, 624],
        'fan_page': [84, 92, 1152, 312],
        'monitoring_page': [84, 404, 1152, 312],
        'Close_Button': [1209, 57, 26, 20],
        'Minimize_Button': [1166, 57, 28, 20],
        'Setting_Button': [1125, 54, 26, 26],
        'SoundMode_Button': [1075, 54, 35, 26],
        'Lighting_Button': [1025, 54, 35, 26],
        'Planet9_Button_base': [987, 55, 18, 27],
        'FanModeAuto': [120, 170, 220, 56],
        'FanModeMax': [120, 238, 220, 56],
        'FanModeCustom': [120, 306, 220, 56],
        'CPU_fan_art': [540, 152, 200, 200],
        'GPU_fan_art': [756, 152, 200, 200],
        'CPU_ScrollBar': [372, 275, 160, 28],
        'GPU1_ScrollBar': [964, 275, 160, 28],
        'CPU_Auto': [452, 315, 80, 20],
        'GPU1_Auto': [964, 315, 80, 20],
    }


def build(source, assembly):
    if hashlib.sha256(assembly.read_bytes()).hexdigest() != ASSEMBLY_SHA256:
        raise ValueError('Assembly does not match the investigated NitroSense build.')
    data = {'schema_version': 1, 'artifact_sha256': ASSEMBLY_SHA256,
        'evidence_type': 'static-recovered-xaml-and-managed-handler-observations',
        'limitations': ['No Windows runtime screenshot or execution is established by this contract.',
            'Declared attributes are not a complete WPF layout/style simulation.',
            'Selected absolute bounds are derived for 100% DPI and the base1320x760 shell.',
            'Registry-dependent visibility remains separate from model-package declarations.'],
        'target': {'model': 'Nitro AN515-45', 'machine_type': 1, 'year': 2021,
            'window_class': 'Nitro_MainWindow_Octavia',
            'monitoring_selection': 'standard unless Windows AcerGUID support selects Acer-mode variant'},
        'sources': {}, 'layouts': {}, 'styles': {}, 'bitmap_resources': {},
        'derived_bounds_100dpi': shell_bounds(),
        'interaction_constants': {'fan_slider_minimum': 0, 'fan_slider_maximum': 10,
            'fan_slider_step': 1, 'fan_slider_percent_multiplier': 10,
            'temperature_poll_ms': 4000, 'fan_poll_ms': 5000,
            'fan_animation_direction': 'negative',
            'fan_animation_seconds_formula': 'rpm>4500 ? 2 : 11-floor(rpm/450)',
            'fan_animation_zero_rpm': 'freeze current angle',
            'coolboost_enabled_modes': ['auto'],
            'custom_selection_dispatches_immediately': True,
            'slider_drag_dispatch': 'drag-completed only',
            'slider_keyboard_dispatch': 'each non-drag value change',
            'custom_auto_toggle_dispatches_immediately': True}}
    for key, relative in FILES.items():
        path = source / relative
        data['sources'][key] = {'relative_path': relative,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        if key not in ('style', 'language'):
            data['layouts'][key] = facts(path)
    style = ET.parse(source / FILES['style']).getroot()
    selected = {'SpeedSliderStyle', 'FanStyle'}
    for element in style:
        key = element.get(XAML + 'Key')
        if local(element.tag) == 'BitmapImage':
            data['bitmap_resources'][key] = element.get('UriSource', '').replace('\\', '/')
        if key in selected:
            props = {}
            for node in element:
                if local(node.tag) == 'Setter' and node.get('Value') is not None:
                    prop = node.get('Property')
                    if not node.get('Value').startswith('{'):
                        props[prop] = value(node.get('Value'))
            data['styles'][key] = props
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('extracted/decompiled-xaml'))
    parser.add_argument('--assembly', type=Path, default=Path('extracted/ui-analysis/Win32/NitroSense.exe'))
    parser.add_argument('--output', type=Path, default=Path('nitro_sense/ui_contract.json'))
    args = parser.parse_args()
    try:
        data = build(args.source, args.assembly)
    except (OSError, ValueError, ET.ParseError) as error:
        parser.exit(1, str(error) + '\n')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + '\n')
    print(f'Wrote {len(data["layouts"])} bounded layout inventories to {args.output}')


if __name__ == '__main__':
    main()
