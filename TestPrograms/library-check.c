#include <dlfcn.h>
#include <stdio.h>

int main(void) {
    struct library { const char *name, *symbol; };
    const struct library libs[] = {
        {"libjson-c.so.3", "json_object_new_int"},
        {"libintl.so.8", "libintl_gettext"}
    };
    int rc = 0;
    for (unsigned i = 0; i < sizeof(libs)/sizeof(libs[0]); ++i) {
        void *lib = dlopen(libs[i].name, RTLD_NOW | RTLD_LOCAL);
        if (!lib) { printf("%s: %s\n", libs[i].name, dlerror()); rc = 1; continue; }
        void *symbol = dlsym(lib, libs[i].symbol);
        printf("%s %s %s\n", libs[i].name, libs[i].symbol, symbol ? "OK" : "missing");
        if (!symbol) rc = 1;
        dlclose(lib);
    }
    return rc;
}
