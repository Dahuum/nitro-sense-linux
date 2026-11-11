#!/usr/bin/env python3
"""Cache passive icon paths from the user's recovered original PSStyle XAML.

This optional local tool does not execute XAML and does not distribute Acer art.
"""
import argparse,json
from pathlib import Path
import xml.etree.ElementTree as ET
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('style',type=Path)
parser.add_argument('assets',type=Path)
a=parser.parse_args()
keys=('Nitro_FanModeAutoStyle','Nitro_FanModeMaxStyle','Nitro_FanModeCustomStyle','CloseButton_ControlTemplate',
      'MinimizeButton_ControlTemplate','SettingButton_ControlTemplate','LightingButton_ControlTemplate',
      'SoundModeButton_ControlTemplate','Planet9SettingButton_ControlTemplate')
ns={'p':'http://schemas.microsoft.com/winfx/2006/xaml/presentation'}
root=ET.parse(a.style).getroot();result={}
for node in root:
 key=node.get('{http://schemas.microsoft.com/winfx/2006/xaml}Key')
 if key in keys:
  result[key]=[{'data':p.get('Data'),'width':p.get('Width'),'height':p.get('Height')}
               for p in node.findall('.//p:Path',ns) if p.get('Data') and p.get('Name','').startswith(('icon','Icon'))]
a.assets.mkdir(parents=True,exist_ok=True)
target=a.assets/'original-style-paths.json';target.write_text(json.dumps(result))
print('Cached',sum(bool(v) for v in result.values()),'local control icons:',target)
