#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <alsa/asoundlib.h>
#include <EGL/egl.h>
#include <SDL/SDL.h>

static void framebuffer(const char *path) {
    struct fb_var_screeninfo v;
    struct fb_fix_screeninfo f;
    int fd = open(path, O_RDONLY);
    if (fd >= 0 && ioctl(fd, FBIOGET_VSCREENINFO, &v) == 0 && ioctl(fd, FBIOGET_FSCREENINFO, &f) == 0)
        printf("%s %.16s %ux%u virtual=%ux%u stride=%u bpp=%u R=%u:%u G=%u:%u B=%u:%u A=%u:%u\n",
               path, f.id, v.xres, v.yres, v.xres_virtual, v.yres_virtual, f.line_length,
               v.bits_per_pixel, v.red.offset, v.red.length, v.green.offset, v.green.length,
               v.blue.offset, v.blue.length, v.transp.offset, v.transp.length);
    else printf("%s: %s\n", path, strerror(errno));
    if (fd >= 0) close(fd);
}

static void mixer(void) {
    snd_mixer_t *m;
    if (snd_mixer_open(&m, 0) < 0) return;
    int rc = snd_mixer_attach(m, "hw:0");
    if (rc >= 0) rc = snd_mixer_selem_register(m, NULL, NULL);
    if (rc >= 0) rc = snd_mixer_load(m);
    if (rc < 0) printf("mixer: %s\n", snd_strerror(rc));
    else for (snd_mixer_elem_t *e = snd_mixer_first_elem(m); e; e = snd_mixer_elem_next(e)) {
        printf("mixer %s", snd_mixer_selem_get_name(e));
        if (snd_mixer_selem_has_playback_volume(e)) {
            long lo, hi, value;
            snd_mixer_selem_get_playback_volume_range(e, &lo, &hi);
            if (!snd_mixer_selem_get_playback_volume(e, SND_MIXER_SCHN_FRONT_LEFT, &value))
                printf(" playback=%ld range=%ld..%ld", value, lo, hi);
        }
        putchar('\n');
    }
    snd_mixer_close(m);
}

static void silent_playback(void) {
    snd_pcm_t *pcm;
    int rc = snd_pcm_open(&pcm, "plughw:0,0", SND_PCM_STREAM_PLAYBACK, SND_PCM_NONBLOCK);
    if (rc < 0) { printf("PCM open: %s\n", snd_strerror(rc)); return; }
    rc = snd_pcm_set_params(pcm, SND_PCM_FORMAT_S16_LE, SND_PCM_ACCESS_RW_INTERLEAVED,
                            2, 44100, 1, 50000);
    if (rc >= 0) {
        short silence[512 * 2] = {0};
        snd_pcm_nonblock(pcm, 0);
        long n = snd_pcm_writei(pcm, silence, 512);
        printf("PCM plughw:0,0 S16_LE stereo 44100 Hz frames=%ld\n", n);
        if (n > 0) snd_pcm_drain(pcm);
    } else printf("PCM configure: %s\n", snd_strerror(rc));
    snd_pcm_close(pcm);
}

static void sdl2(void) {
    void *lib = dlopen("libSDL2-2.0.so.0", RTLD_NOW | RTLD_LOCAL);
    if (!lib) { puts(dlerror()); return; }
    void (*version)(SDL_version *) = dlsym(lib, "SDL_GetVersion");
    int (*count)(void) = dlsym(lib, "SDL_GetNumVideoDrivers");
    const char *(*driver)(int) = dlsym(lib, "SDL_GetVideoDriver");
    SDL_version v;
    if (version) { version(&v); printf("SDL2 runtime %u.%u.%u\n", v.major, v.minor, v.patch); }
    if (count && driver) for (int i = 0; i < count(); ++i) printf("SDL2 driver %s\n", driver(i));
    dlclose(lib);
}

int main(void) {
    framebuffer("/dev/fb0");
    framebuffer("/dev/fb1");
    printf("ALSA runtime %s\n", snd_asoundlib_version());
    mixer();
    silent_playback();
    const SDL_version *v = SDL_Linked_Version();
    printf("SDL1 runtime %u.%u.%u\n", v->major, v->minor, v->patch);
    // Headless init is isolated from the active menu. Never set a display mode.
    char driver[64];
    setenv("SDL_VIDEODRIVER", "dummy", 1);
    if (SDL_VideoInit("dummy", 0) == 0) {
        if (SDL_VideoDriverName(driver, sizeof(driver))) printf("SDL1 verified driver %s\n", driver);
        SDL_VideoQuit();
    } else printf("SDL1 dummy: %s\n", SDL_GetError());
    sdl2();
    void *egl = dlopen("libEGL.so.1", RTLD_NOW | RTLD_LOCAL);
    if (!egl) { printf("EGL: %s\n", dlerror()); return 0; }
    EGLDisplay (*display)(EGLNativeDisplayType) = dlsym(egl, "eglGetDisplay");
    EGLBoolean (*init)(EGLDisplay, EGLint *, EGLint *) = dlsym(egl, "eglInitialize");
    EGLint (*error)(void) = dlsym(egl, "eglGetError");
    const char *(*query)(EGLDisplay, EGLint) = dlsym(egl, "eglQueryString");
    EGLBoolean (*term)(EGLDisplay) = dlsym(egl, "eglTerminate");
    if (display && init && error && query && term) {
        EGLDisplay d = display(EGL_DEFAULT_DISPLAY);
        EGLint major, minor;
        if (d != EGL_NO_DISPLAY && init(d, &major, &minor)) {
            printf("EGL %d.%d vendor=%s APIs=%s\n", major, minor, query(d, EGL_VENDOR), query(d, EGL_CLIENT_APIS));
            term(d);
        } else printf("EGL default display unavailable, error=0x%x\n", error());
    }
    dlclose(egl);
    return 0;
}
