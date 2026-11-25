#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

int main(void) {
    char name[80] = {0}, volume[24];
    int fd = open("/dev/input/event1", O_RDONLY | O_NONBLOCK);
    if (fd < 0 || ioctl(fd, EVIOCGNAME(sizeof(name)), name) < 0 ||
        strcmp(name, "RG35XX Gamepad") || ioctl(fd, EVIOCGRAB, 1) < 0) {
        perror("gamepad grab"); return 1;
    }
    setbuf(stdout, NULL);
    puts("READY RG35XX Gamepad");
    int vol = open("/sys/class/volume/value", O_RDONLY);
    int previous = -1;
    double start = now();
    struct pollfd p = {fd, POLLIN, 0};
    while (now() - start < 120) {
        if (poll(&p, 1, 100) < 0 && errno != EINTR) break;
        struct input_event e;
        while (read(fd, &e, sizeof(e)) == sizeof(e)) {
            if (e.type == EV_KEY || e.type == EV_ABS)
                printf("%.2f type=%u code=0x%04x value=%d\n", now()-start, e.type, e.code, e.value);
        }
        if (vol >= 0 && lseek(vol, 0, SEEK_SET) == 0) {
            ssize_t n = read(vol, volume, sizeof(volume)-1);
            if (n > 0) {
                volume[n] = 0;
                int value = atoi(volume);
                if (value != previous) printf("%.2f volume=%d\n", now()-start, value);
                previous = value;
            }
        }
    }
    ioctl(fd, EVIOCGRAB, 0);
    close(fd);
    if (vol >= 0) close(vol);
    puts("DONE");
    return 0;
}
