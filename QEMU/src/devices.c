// SPDX-License-Identifier: GPL-3.0-or-later
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <linux/input.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>
static int same(int fd,const char *path){struct stat a,b;return !fstat(fd,&a)&&!stat(path,&b)&&a.st_dev==b.st_dev&&a.st_ino==b.st_ino;}
static int page;
static void var(struct fb_var_screeninfo *v,int second){
 memset(v,0,sizeof(*v));v->xres=v->xres_virtual=second?1280:640;v->yres=second?720:480;v->yres_virtual=1440;v->bits_per_pixel=second?32:16;
 v->red.offset=second?0:11;v->red.length=second?8:5;v->green.offset=second?8:5;v->green.length=second?8:6;v->blue.offset=second?16:0;v->blue.length=second?8:5;v->transp.offset=second?24:0;v->transp.length=second?8:0;
 v->yoffset=second?0:page;v->activate=FB_ACTIVATE_NOW;
}
static void bit(void *buf,size_t size,int n){if((size_t)(n/8)<size)((unsigned char*)buf)[n/8]|=1u<<(n%8);}
int ioctl(int fd,unsigned long req,...){
 va_list ap;va_start(ap,req);void *arg=va_arg(ap,void*);va_end(ap);
 int second=same(fd,"/dev/fb1");
 if(second||same(fd,"/dev/fb0")){
  if(req==FBIOGET_VSCREENINFO){var(arg,second);return 0;}
  if(req==FBIOGET_FSCREENINFO){struct fb_fix_screeninfo *f=arg;memset(f,0,sizeof(*f));strcpy(f->id,"RG35XX-QEMU");f->line_length=second?5120:1280;f->smem_len=f->line_length*1440;f->type=FB_TYPE_PACKED_PIXELS;f->visual=FB_VISUAL_TRUECOLOR;f->ypanstep=1;return 0;}
  if(req==FBIOPUT_VSCREENINFO||req==FBIOPAN_DISPLAY){struct fb_var_screeninfo *v=arg;
   if(v->xres!=(unsigned)(second?1280:640)||v->yres!=(unsigned)(second?720:480)||v->bits_per_pixel!=(unsigned)(second?32:16)||v->xoffset||v->yoffset+v->yres>1440){errno=EINVAL;return -1;}
   if(!second){page=v->yoffset;int f=open("/run/rg35xx/page",O_WRONLY);if(f>=0){char s[32];int n=snprintf(s,sizeof s,"%d\n",page);ftruncate(f,0);write(f,s,n);close(f);}}return 0;}
  if(req==FBIO_WAITFORVSYNC){usleep(16667);return 0;}
  if(req==FBIOBLANK)return 0;
  errno=ENOTTY;return -1;
 }
 int power=same(fd,"/dev/input/event0");
 if(power||same(fd,"/dev/input/event1")){
  unsigned nr=_IOC_NR(req);size_t size=_IOC_SIZE(req);
  if(req==EVIOCGVERSION){*(int*)arg=EV_VERSION;return 0;}
  if(req==EVIOCGID){struct input_id *id=arg;memset(id,0,sizeof(*id));id->bustype=BUS_HOST;id->vendor=0x10d6;id->product=0x4e42;id->version=1;return 0;}
  if(req==EVIOCGRAB)return 0;
  if(_IOC_TYPE(req)=='E'&&nr==6){const char *s=power?"atc260x_onoff":"RG35XX Gamepad";size_t n=strlen(s)+1;if(n>size)n=size;if(n){memcpy(arg,s,n);((char*)arg)[n-1]=0;}return n;}
  if(_IOC_TYPE(req)=='E'&&nr>=0x20&&nr<=0x20+EV_MAX){memset(arg,0,size);int type=nr-0x20;
   if(type==0){bit(arg,size,EV_SYN);bit(arg,size,EV_KEY);if(!power)bit(arg,size,EV_ABS);}
   else if(type==EV_KEY){if(power)bit(arg,size,KEY_POWER);else {int k[]={0x130,0x131,0x133,0x134,0x136,0x137,0x13a,0x13b,0x13c,0x13d,0x13e};for(unsigned i=0;i<sizeof k/sizeof*k;i++)bit(arg,size,k[i]);}}
   else if(type==EV_ABS&&!power){int a[]={2,5,16,17};for(int i=0;i<4;i++)bit(arg,size,a[i]);}
   return size;}
  if(_IOC_TYPE(req)=='E'&&nr==0x18){memset(arg,0,size);int f=open(power?"/run/rg35xx/power-state":"/run/rg35xx/pad-state",O_RDONLY);if(f>=0){read(f,arg,size<96?size:96);close(f);}
   return size;}
  if(_IOC_TYPE(req)=='E'&&nr>=0x40&&nr<=0x40+ABS_MAX){int axis=nr-0x40;if(power||(axis!=2&&axis!=5&&axis!=16&&axis!=17)){errno=EINVAL;return -1;}
   struct input_absinfo *a=arg;memset(a,0,sizeof(*a));a->minimum=axis>=16?-1:0;a->maximum=axis>=16?1:255;
   int f=open("/run/rg35xx/pad-state",O_RDONLY);if(f>=0){pread(f,&a->value,4,96+axis*4);close(f);}return 0;}
  errno=ENOTTY;return -1;
 }
 static int(*real)(int,unsigned long,...);if(!real)real=dlsym(RTLD_NEXT,"ioctl");return real(fd,req,arg);
}
