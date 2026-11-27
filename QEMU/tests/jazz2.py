#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Private external Jazz2 package integration test. No game files are bundled."""
import argparse,hashlib,importlib.util,json,struct,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
(BASE/'reports').mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('harness',BASE/'scripts/rg35xx.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
a=argparse.ArgumentParser();a.add_argument('app',type=Path);args=a.parse_args();app=args.app.resolve()
state=h.state_path('jazz2-test');root=h.prepare(state);save=root/'mnt/mmc/CFW';save.mkdir(parents=True,exist_ok=True)
(save/'RG35XX.options').write_bytes(struct.pack('<Iiiii',0x324F4752,1,45,1,1))
cmd=[str(BASE/'rg35xx'),'run','--session','jazz2-test','--app',str(app),'--exec','jazz2','--headless','--seconds','110','--','/config','/mnt/mmc/CFW/Jazz2.config','/level','prince/01_castle1']
report={'app':str(app),'tests':[]};proc=subprocess.Popen(cmd)
def key(name,hold=.18):
 h.event(state,name,True);time.sleep(hold);h.event(state,name,False);time.sleep(.45)
def sample(seconds):
 frames=set();motor=set();end=time.monotonic()+seconds
 while time.monotonic()<end:
  assert proc.poll() is None,'Early game exit: '+(state/'console.log').read_text(errors='replace')[-2000:]
  raw=(root/'dev/fb0').read_bytes()
  if any(raw):frames.add(hashlib.sha256(raw).hexdigest())
  motor.add((root/'sys/class/power_supply/battery/moto').read_text().strip())
  time.sleep(.08)
 return frames,motor
try:
 frames,motor=sample(15);assert len(frames)>3,frames
 report['tests'].append({'dynamic_frames':len(frames)})
 (BASE/'reports/jazz2-level.ppm').write_bytes(h.rgb(state))
 h.event(state,'b',True)
 try:fire_frames,motor=sample(5)
 finally:h.event(state,'b',False)
 report['tests'].append({'fire_frames':len(fire_frames),'motor_values':sorted(motor)})
 assert any(v not in ('','0') for v in motor),motor
 key('right',1);key('a');key('start');time.sleep(1)
 (BASE/'reports/jazz2-pause.ppm').write_bytes(h.rgb(state))
 key('start');key('menu');assert proc.wait(timeout=20)==0
 resume=save/'Jazz2.resume';config=save/'Jazz2.config'
 assert resume.stat().st_size>100 and config.stat().st_size>0
 assert (root/'sys/class/power_supply/battery/moto').read_text().strip()=='0'
 report['tests'].append({'menu_exit':0,'resume_bytes':resume.stat().st_size,'config_bytes':config.stat().st_size,'motor_off_on_exit':True})
 # Restart through the normal menu and choose Continue.
 cmd2=cmd[:-2]
 proc=subprocess.Popen(cmd2)
 sample(7);key('a');time.sleep(2);key('a');sample(5)
 text=(state/'console.log').read_text(errors='replace')
 assert 'Resuming saved state' in text,text[-2500:]
 (BASE/'reports/jazz2-resumed.ppm').write_bytes(h.rgb(state))
 key('menu');assert proc.wait(timeout=20)==0
 report['tests'].append({'continue_restored_gameplay':True})
 report['result']='PASS'
finally:
 if proc.poll() is None:proc.terminate();proc.wait(timeout=10)
 (BASE/'reports/jazz2-test.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
