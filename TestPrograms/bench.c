#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <SDL/SDL.h>

static double now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) exit(2);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

int main(void) {
    const size_t bytes = 4u * 1024 * 1024;
    unsigned char *a = malloc(bytes), *b = malloc(bytes);
    SDL_Surface *src = SDL_CreateRGBSurface(0, 640, 480, 16, 0xf800, 0x07e0, 31, 0);
    SDL_Surface *dst = SDL_CreateRGBSurface(0, 640, 480, 16, 0xf800, 0x07e0, 31, 0);
    if (!a || !b || !src || !dst) return 2;
    memset(a, 1, bytes);
    memset(b, 0, bytes);
    SDL_FillRect(src, NULL, 0x07e0);
    uint32_t x = 1;
    double start = now();
    for (unsigned i = 0; i < 16000000u; ++i) {
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
    }
    double cpu = now() - start;
    void *(*volatile copy)(void *, const void *, size_t) = memcpy;
    start = now();
    for (unsigned i = 0; i < 32; ++i) {
        copy(b, a, bytes);
        unsigned char *tmp = b; b = a; a = tmp;
    }
    double mem = now() - start;
    start = now();
    for (unsigned i = 0; i < 200; ++i)
        if (SDL_BlitSurface(src, NULL, dst, NULL) != 0) return 3;
    double blit = now() - start;
    printf("checksum=%08x byte=%u pixel=%04x cpu_ms=%.3f copy_MiB_s=%.2f blits_s=%.2f\n",
           x, a[bytes-1], *(uint16_t *)dst->pixels, cpu * 1000, 128.0 / mem, 200.0 / blit);
    SDL_FreeSurface(src);
    SDL_FreeSurface(dst);
    free(a);
    free(b);
    return 0;
}
