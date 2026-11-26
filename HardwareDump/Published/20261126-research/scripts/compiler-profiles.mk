# Template only. Include in project Makefile; verify SDK paths and ABI on hardware.
CROSS ?= /opt/miyoo/bin/arm-miyoo-linux-uclibcgnueabi-
CC := $(CROSS)gcc
CXX := $(CROSS)g++
PROFILE ?= stock
ifeq ($(PROFILE),stock)
  ARCH_FLAGS := -mcpu=arm926ej-s -mfloat-abi=soft -O2
else ifeq ($(PROFILE),a9)
  ARCH_FLAGS := -mcpu=cortex-a9 -mfpu=vfpv3 -mfloat-abi=softfp -O2
else ifeq ($(PROFILE),neon)
  ARCH_FLAGS := -mcpu=cortex-a9 -mfpu=neon -mfloat-abi=softfp -O3
else
  $(error Unknown PROFILE: $(PROFILE))
endif
CFLAGS += $(ARCH_FLAGS)
CXXFLAGS += $(ARCH_FLAGS)
LDFLAGS += $(ARCH_FLAGS)
# For C++ optional: LDFLAGS += -static-libstdc++ -static-libgcc
# Link target libraries from matching sysroot, not host libraries.
