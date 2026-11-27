#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util,json,subprocess,sys,time
from pathlib import Path
b=Path(__file__).resolve().parents[1];(b/'reports').mkdir(exist_ok=True);spec=importlib.util.spec_from_file_location('h',b/'scripts/rg35xx.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
s=h.state_path('jazz2-default');root=h.prepare(s);save=root/'mnt/mmc/CFW'
for name in ['Jazz2.config','Jazz2.resume','RG35XX.options']:(save/name).unlink(missing_ok=True)
p=subprocess.Popen([str(b/'rg35xx'),'run','--session','jazz2-default','--app',sys.argv[1],'--exec','jazz2','--headless','--seconds','30','--','/config','/mnt/mmc/CFW/Jazz2.config','/level','prince/01_castle1'])
try:
 time.sleep(10);assert p.poll() is None
 text=(s/'console.log').read_text(errors='replace')
 assert 'gameplay FPS limit 45' in text and '320x240 -> 640x480' in text,text[-3000:]
 (b/'reports/jazz2-default.ppm').write_bytes(h.rgb(s))
 h.event(s,'menu',True);assert p.wait(timeout=10)==0
 assert (save/'Jazz2.resume').stat().st_size>100
 (b/'reports/jazz2-default-result.json').write_text(json.dumps({'result':'PASS','default_internal':'320x240','display':'640x480 RGB565','gameplay_cap':45,'menu_save_exit':0},indent=2))
 print('PASS Jazz2 clean defaults: 320x240 -> 640x480, gameplay cap 45, MENU save/exit')
finally:
 if p.poll() is None:p.terminate();p.wait(timeout=5)
