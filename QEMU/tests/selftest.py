#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util,json,os,subprocess,sys,time
from pathlib import Path
base=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('h',base/'scripts/rg35xx.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
subprocess.run([str(base/'rg35xx'),'run','--session','self-probe','--exec','probe','--headless','--seconds','20'],check=True)
assert 'PASS' in (base/'state/self-probe/console.log').read_text()
state=h.state_path('self-demo');proc=subprocess.Popen([str(base/'rg35xx'),'run','--session','self-demo','--headless','--seconds','20','--','400'])
try:
 time.sleep(1);root=state/'root';assert proc.poll() is None
 frame=(root/'dev/fb0').read_bytes();time.sleep(.3);assert any(frame) and frame!=(root/'dev/fb0').read_bytes()
 assert (root/'mnt/mmc/qemu-demo.txt').read_text()=='TF1 OK\n'
 assert (root/'mnt/SDCARD/qemu-demo.txt').read_text()=='TF2 OK\n'
 h.event(state,'a',True);time.sleep(.2);assert (root/'sys/class/power_supply/battery/moto').read_text().strip()=='255'
 h.event(state,'a',False);time.sleep(.2);assert (root/'sys/class/power_supply/battery/moto').read_text().strip()=='0'
 h.event(state,'right',True);h.event(state,'right',False)
 (base/'reports').mkdir(exist_ok=True)
 (base/'reports/demo.ppm').write_bytes(h.rgb(state))
 h.event(state,'menu',True);assert proc.wait(timeout=5)==0
finally:
 if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
# Exercise Tk image decoding and a real WSLg window, then close it automatically.
if os.environ.get('DISPLAY'):
 import tkinter as tk
 original=tk.Tk.mainloop
 def bounded(self):self.after(1200,self.destroy);original(self)
 tk.Tk.mainloop=bounded
 h.viewer(state)
 photo=tk.Tk();photo.withdraw();im=tk.PhotoImage(data=h.rgb(state),format='PPM');im.write(str(base/'reports/demo.png'),format='png');photo.destroy()
print('PASS ARM devices + SDL; animated RGB565; separate TF1/TF2; button->motor; MENU exit; WSLg viewer')
