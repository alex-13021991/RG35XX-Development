#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""RG35XX application test harness; QEMU linux-user + explicit device stubs."""
import argparse, array, errno, fcntl, hashlib, json, os, shlex, shutil, signal, struct, subprocess, sys, time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
BUTTONS={'a':(1,0x130,1),'b':(1,0x131,1),'x':(1,0x133,1),'y':(1,0x134,1),'l1':(1,0x136,1),'r1':(1,0x137,1),'l2':(3,2,255),'r2':(3,5,255),'select':(1,0x13a,1),'start':(1,0x13b,1),'menu':(1,0x13c,1),'vol+':(1,0x13d,1),'vol-':(1,0x13e,1),'up':(3,17,-1),'down':(3,17,1),'left':(3,16,-1),'right':(3,16,1),'power':(1,116,1)}
def state_path(name):
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in name): raise ValueError('Invalid session name')
    return BASE/'state'/name

def event(state,button,pressed):
    t,c,v=BUTTONS[button];v=v if pressed else 0
    power=button=='power';dev=state/'root/dev/input'/('event0' if power else 'event1')
    try:fd=os.open(dev,os.O_WRONLY|os.O_NONBLOCK)
    except OSError as exc:
        if not pressed and exc.errno==errno.ENXIO:return
        raise
    try:
        now=time.time();sec=int(now);usec=int((now-sec)*1e6)
        os.write(fd,struct.pack('<iiHHi',sec,usec,t,c,v)+struct.pack('<iiHHi',sec,usec,0,0,0))
    finally:os.close(fd)
    path=state/'root/run/rg35xx'/('power-state' if power else 'pad-state')
    with path.open('r+b',buffering=0) as f:
        data=bytearray(f.read())
        if t==1:
            if pressed:data[c//8]|=1<<(c%8)
            else:data[c//8]&=~(1<<(c%8))
        else:struct.pack_into('<i',data,96+c*4,v)
        f.seek(0);f.write(data)

def prepare(state):
    root=state/'root'
    for d in ['dev/input','run/rg35xx','sys/class/power_supply/battery','sys/class/volume','mnt/mmc/CFW','mnt/SDCARD','proc','tmp','etc','lib','usr/lib','opt/rg35xx','app']:(root/d).mkdir(parents=True,exist_ok=True)
    for name,size in [('fb0',1280*1440),('fb1',5120*1440)]:
        with (root/'dev'/name).open('wb') as f:f.truncate(size)
    for i in range(2):
        path=root/f'dev/input/event{i}'
        if not path.exists():os.mkfifo(path)
    for name in ['pad-state','power-state']:(root/'run/rg35xx'/name).write_bytes(bytes(96+64*4))
    (root/'run/rg35xx/page').write_text('0\n')
    for name,text in [('moto','0\n'),('capacity','100\n'),('status','Full\n'),('voltage_now','4000000\n')]: (root/'sys/class/power_supply/battery'/name).write_text(text)
    (root/'sys/class/volume/value').write_text('40\n')
    (root/'etc/asound.conf').write_text('pcm.!default { type null }\npcm.hw { type null }\npcm.plughw { type null }\n')
    return root

def rgb(state):
    root=state/'root';page=int((root/'run/rg35xx/page').read_text().strip() or 0)
    with (root/'dev/fb0').open('rb') as f:f.seek(page*1280);raw=f.read(640*480*2)
    if len(raw)!=640*480*2:raise ValueError('Invalid framebuffer size/page')
    data=array.array('H');data.frombytes(raw)
    if sys.byteorder!='little':data.byteswap()
    out=bytearray(len(data)*3)
    for i,v in enumerate(data):
        r=(v>>11)&31;g=(v>>5)&63;b=v&31
        out[3*i]=(r<<3)|(r>>2);out[3*i+1]=(g<<2)|(g>>4);out[3*i+2]=(b<<3)|(b>>2)
    return b'P6\n640 480\n255\n'+out

def viewer(state,process=None):
    import tkinter as tk
    window=tk.Tk();window.title('RG35XX / QEMU — 640×480 RGB565')
    image_label=tk.Label(window);image_label.pack()
    status=tk.StringVar();tk.Label(window,textvariable=status).pack()
    tk.Label(window,text='Arrows: D-pad | Z/X: A/B | A/S: X/Y | Q/W: L1/R1 | E/R: L2/R2\nEnter: Start | Backspace: Select | Esc: Menu | +/-: Volume | P: Power').pack()
    keys={'Up':'up','Down':'down','Left':'left','Right':'right','z':'a','x':'b','a':'x','s':'y','q':'l1','w':'r1','e':'l2','r':'r2','Return':'start','BackSpace':'select','Escape':'menu','plus':'vol+','equal':'vol+','minus':'vol-','p':'power'}
    pressed=set();pending={}
    def emit(button,value):
        try:event(state,button,value)
        except OSError:pass
    def key(e,value):
        k=e.keysym if e.keysym in keys else e.keysym.lower()
        if k not in keys:return
        if k in pending:window.after_cancel(pending.pop(k))
        if value:
            if k not in pressed:pressed.add(k);emit(keys[k],True)
        else:
            def release():
                pending.pop(k,None);pressed.discard(k);emit(keys[k],False)
            pending[k]=window.after(10,release)
    def release_all(e=None):
        for timer in pending.values():window.after_cancel(timer)
        pending.clear()
        for k in pressed:emit(keys[k],False)
        pressed.clear()
    window.bind('<KeyPress>',lambda e:key(e,True));window.bind('<KeyRelease>',lambda e:key(e,False));window.bind('<FocusOut>',release_all)
    def close():
        release_all()
        if process and process.poll() is None:os.killpg(process.pid,signal.SIGTERM)
        window.destroy()
    window.protocol('WM_DELETE_WINDOW',close)
    def tick():
        try:
            photo=tk.PhotoImage(data=rgb(state),format='PPM');image_label.configure(image=photo);image_label.image=photo
            motor=(state/'root/sys/class/power_supply/battery/moto').read_text().strip()
            code=process.poll() if process else None
            status.set(f'Motor (simulation): {motor or 0} | TF1 /mnt/mmc | TF2 /mnt/SDCARD'+(f' | Exit: {code}' if code is not None else ''))
        except (OSError,ValueError):pass
        window.after(66,tick)
    tick();window.mainloop()

def launch(args):
    state=state_path(args.session);state.mkdir(parents=True,exist_ok=True)
    lock=(state/'lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    root=prepare(state);app=Path(args.app).expanduser().resolve() if args.app else BASE/'build'
    target=app/args.binary
    if not target.is_file():raise ValueError(f'Executable missing: {target}')
    target.chmod(target.stat().st_mode|0o100)
    if ':' in str(app):raise ValueError('App path cannot contain colon')
    envs={'LD_PRELOAD':'/opt/rg35xx/devices.so','LD_LIBRARY_PATH':'/app/lib:/usr/lib:/lib','SDL_VIDEODRIVER':'dummy','SDL_AUDIODRIVER':'dummy','ALSOFT_DRIVERS':'null','ALSOFT_CONF':'/app/alsoft.conf','JAZZ2_RESOLUTION':'640x480','JAZZ2_RUMBLE_PATH':'/sys/class/power_supply/battery/moto','HOME':'/mnt/mmc/CFW','XDG_CONFIG_HOME':'/mnt/mmc/CFW','XDG_DATA_HOME':'/mnt/mmc/CFW','LANG':'C','ALSA_CONFIG_PATH':'/etc/asound.conf'}
    for item in args.env:
        k,v=item.split('=',1);envs[k]=v
    qemu=['qemu-arm','-cpu','cortex-a9']
    if args.strace:qemu+=['-strace']
    for k,v in envs.items():qemu+=['-E',k+'='+v]
    cmd=['proot','-r',str(root),'-q',shlex.join(qemu),'-w','/app',
         '-b',str(BASE/'runtime/lib')+':/lib','-b',str(BASE/'runtime/usr/lib')+':/usr/lib',
         '-b',str(BASE/'build')+':/opt/rg35xx','-b',str(app)+':/app','-b','/dev/null','-b','/dev/zero','-b','/dev/urandom','-b','/dev/random', '/app/'+args.binary]+args.arguments
    # PRoot 5.1 rewrites LD_LIBRARY_PATH for QEMU. Overlay app libraries explicitly.
    if (app/'lib').is_dir():
        for lib in sorted((app/'lib').iterdir()):
            if lib.is_file() and '.so' in lib.name:
                cmd[-(len(args.arguments)+1):-(len(args.arguments)+1)] = ['-b',str(lib.resolve())+':/usr/lib/'+lib.name]
    clean=os.environ.copy()
    for k in ['LD_PRELOAD','LD_LIBRARY_PATH','QEMU_LD_PREFIX','QEMU_SET_ENV','QEMU_UNSET_ENV','QEMU_CPU']:clean.pop(k,None)
    clean['PROOT_NO_SECCOMP']='1'
    (state/'command.json').write_text(json.dumps(cmd,ensure_ascii=False,indent=2))
    (state/'pid.json').write_text('{}')
    fifos=[os.open(root/f'dev/input/event{i}',os.O_RDWR|os.O_NONBLOCK) for i in range(2)]
    proc=None;result=None
    try:
        with (state/'console.log').open('wb') as log:
            proc=subprocess.Popen(cmd,env=clean,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            (state/'pid.json').write_text(json.dumps({'pid':proc.pid}))
            print(f'Session: {state}\nLog: {state}/console.log',flush=True)
            if args.headless:
                try:result=proc.wait(timeout=args.seconds or None)
                except subprocess.TimeoutExpired:
                    result=124
            else:viewer(state,proc);result=proc.poll()
    finally:
        if proc and proc.poll() is None:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        (root/'sys/class/power_supply/battery/moto').write_text('0\n')
        for fd in fifos:os.close(fd)
        (state/'pid.json').write_text('{}')
    return result if result is not None else 0

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('--session',default='default');run.add_argument('--app');run.add_argument('--exec',dest='binary',default='demo');run.add_argument('--headless',action='store_true');run.add_argument('--seconds',type=float);run.add_argument('--strace',action='store_true');run.add_argument('--env',action='append',default=[]);run.add_argument('arguments',nargs=argparse.REMAINDER)
    v=sub.add_parser('view');v.add_argument('--session',default='default')
    e=sub.add_parser('key');e.add_argument('button',choices=BUTTONS);e.add_argument('--session',default='default');e.add_argument('--hold',type=float,default=.12)
    shot=sub.add_parser('screenshot');shot.add_argument('output',type=Path);shot.add_argument('--session',default='default')
    a=parser.parse_args()
    if a.command=='run':
        if a.arguments[:1]==['--']:a.arguments.pop(0)
        return launch(a)
    state=state_path(a.session)
    if a.command=='view':viewer(state)
    elif a.command=='key':
        event(state,a.button,True)
        try:time.sleep(a.hold)
        finally:event(state,a.button,False)
    elif a.command=='screenshot':a.output.write_bytes(rgb(state));print(a.output)
    return 0
def interrupted(signum,frame):raise KeyboardInterrupt
if __name__=='__main__':
    signal.signal(signal.SIGTERM,interrupted)
    try:sys.exit(main())
    except KeyboardInterrupt:sys.exit(130)
    except (ValueError,OSError) as exc:sys.exit(str(exc))
