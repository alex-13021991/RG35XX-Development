// SPDX-License-Identifier: GPL-3.0-or-later
#include <fcntl.h>
#include <linux/fb.h>
#include <linux/input.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
int main(int argc,char **argv){
 int f=open("/dev/fb0",O_RDWR),pad=open("/dev/input/event1",O_RDONLY|O_NONBLOCK);struct fb_var_screeninfo v;struct fb_fix_screeninfo fix;
 if(f<0||ioctl(f,FBIOGET_VSCREENINFO,&v)||ioctl(f,FBIOGET_FSCREENINFO,&fix))return 2;
 uint16_t *fb=mmap(0,fix.smem_len,PROT_READ|PROT_WRITE,MAP_SHARED,f,0);if(fb==MAP_FAILED)return 3;
 FILE *card=fopen("/mnt/mmc/qemu-demo.txt","w");if(!card)return 4;fputs("TF1 OK\n",card);fclose(card);
 card=fopen("/mnt/SDCARD/qemu-demo.txt","w");if(!card)return 5;fputs("TF2 OK\n",card);fclose(card);
 int frames=argc>1?atoi(argv[1]):18000,x=320,y=240,motor=0;printf("640x480 RGB565; arrows move, A vibrates, MENU exits\n");fflush(stdout);
 for(int frame=0;frame<frames;frame++){
  struct input_event e;while(read(pad,&e,sizeof e)==sizeof e){if(e.type==EV_KEY&&e.code==0x13c&&e.value)goto done;if(e.type==EV_ABS&&e.code==16)x+=e.value*15;if(e.type==EV_ABS&&e.code==17)y+=e.value*15;if(e.type==EV_KEY&&e.code==0x130){motor=e.value?255:0;FILE *m=fopen("/sys/class/power_supply/battery/moto","w");if(m){fprintf(m,"%d\n",motor);fclose(m);}}}
  if(x<0)x=0;
  if(x>620)x=620;
  if(y<0)y=0;
  if(y>460)y=460;
  for(int j=0;j<480;j++)for(int i=0;i<640;i++)fb[j*640+i]=((i+frame)/20%32)<<11|((j+frame)/10%64)<<5|((i+j)/30%32);
  for(int j=y;j<y+20;j++)for(int i=x;i<x+20;i++)fb[j*640+i]=motor?0xf800:0xffff;
  usleep(33333);
 }
 done:card=fopen("/sys/class/power_supply/battery/moto","w");if(card){fputs("0\n",card);fclose(card);}munmap(fb,fix.smem_len);close(f);close(pad);return 0;
}
