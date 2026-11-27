// SPDX-License-Identifier: GPL-3.0-or-later
#include <dlfcn.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <linux/input.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);return 1;}}while(0)
int main(void){
 for(int i=0;i<2;i++){char path[32];snprintf(path,sizeof path,"/dev/fb%d",i);int fd=open(path,O_RDWR);CHECK(fd>=0);struct fb_var_screeninfo v;struct fb_fix_screeninfo f;CHECK(!ioctl(fd,FBIOGET_VSCREENINFO,&v));CHECK(!ioctl(fd,FBIOGET_FSCREENINFO,&f));CHECK(v.xres==(i?1280:640)&&v.yres==(i?720:480)&&v.yres_virtual==1440&&v.bits_per_pixel==(i?32:16));CHECK(f.line_length==(i?5120:1280));CHECK(v.red.offset==(i?0:11)&&v.green.offset==(i?8:5));void *pixels=mmap(0,f.smem_len,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);CHECK(pixels!=MAP_FAILED);memset(pixels,0,f.smem_len);munmap(pixels,f.smem_len);if(!i){v.yoffset=480;CHECK(!ioctl(fd,FBIOPAN_DISPLAY,&v));v.yoffset=1440;CHECK(ioctl(fd,FBIOPAN_DISPLAY,&v)<0);v.yoffset=0;CHECK(!ioctl(fd,FBIOPAN_DISPLAY,&v));}close(fd);}
 int pad=open("/dev/input/event1",O_RDONLY|O_NONBLOCK);CHECK(pad>=0);char name[80];CHECK(ioctl(pad,EVIOCGNAME(sizeof name),name)>0&&!strcmp(name,"RG35XX Gamepad"));struct input_absinfo a;CHECK(!ioctl(pad,EVIOCGABS(ABS_HAT0X),&a)&&a.minimum==-1&&a.maximum==1);CHECK(!ioctl(pad,EVIOCGABS(ABS_Z),&a)&&a.maximum==255);close(pad);
 FILE *f=fopen("/mnt/mmc/probe.txt","w");CHECK(f);fputs("TF1",f);fclose(f);f=fopen("/mnt/SDCARD/probe.txt","w");CHECK(f);fputs("TF2",f);fclose(f);
 f=fopen("/sys/class/power_supply/battery/moto","w");CHECK(f);fputs("255\n",f);fclose(f);
 void *s=dlopen("libSDL2-2.0.so.0",RTLD_NOW);CHECK(s);int(*init)(unsigned)=dlsym(s,"SDL_Init");void(*quit)(void)=dlsym(s,"SDL_Quit");CHECK(init&&quit&&!init(0x20));quit();dlclose(s);
 s=dlopen("libSDL-1.2.so.0",RTLD_NOW);CHECK(s);init=dlsym(s,"SDL_Init");quit=dlsym(s,"SDL_Quit");CHECK(init&&quit&&!init(0x20));quit();dlclose(s);
 puts("PASS fb0/fb1 geometry mmap pan; evdev; TF1 TF2; motor; original SDL1 SDL2 dummy");return 0;
}
