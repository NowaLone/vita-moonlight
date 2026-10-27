#include "vita_motion.h"

#include <Limelight.h>
#include <psp2/motion.h>
#include <psp2/kernel/threadmgr.h>
#include <stdbool.h>
#include <stdint.h>

#include "debug.h"

/* Vita raw samples use rad/s and g; Moonlight requires deg/s and m/s^2. */
#define GYRO_RADIANS_TO_DEGREES 57.2957795131f
#define ACCEL_STANDARD_GRAVITY 9.80665f

static bool s_active = false;
static bool s_enabled = false;
static bool s_suspended = true;
static uint16_t s_gyro_rate = 0;
static uint16_t s_accel_rate = 0;
static bool s_initialized = false;
static bool s_gyro_thread_started = false;
static bool s_accel_thread_started = false;

static void send_gyro(void)
{
    SceMotionSensorState state;

    if (sceMotionGetSensorState(&state, 1) < 0) {
        return;
    }

    LiSendControllerMotionEvent(
        0,
        LI_MOTION_TYPE_GYRO,
        state.gyro.x * GYRO_RADIANS_TO_DEGREES,
        state.gyro.y * GYRO_RADIANS_TO_DEGREES,
        state.gyro.z * GYRO_RADIANS_TO_DEGREES);
}

static void send_accel(void)
{
    SceMotionSensorState state;

    if (sceMotionGetSensorState(&state, 1) < 0) {
        return;
    }

    LiSendControllerMotionEvent(
        0,
        LI_MOTION_TYPE_ACCEL,
        state.accelerometer.x * ACCEL_STANDARD_GRAVITY,
        state.accelerometer.y * ACCEL_STANDARD_GRAVITY,
        state.accelerometer.z * ACCEL_STANDARD_GRAVITY);
}

static int gyro_thread_main(SceSize args, void *argp)
{
    (void)args;
    (void)argp;

    while (1) {
        /* Host callbacks/stop may change the rate while send_gyro is running. */
        const uint16_t rate = __atomic_load_n(&s_gyro_rate, __ATOMIC_RELAXED);
        if (__atomic_load_n(&s_active, __ATOMIC_RELAXED) &&
            __atomic_load_n(&s_enabled, __ATOMIC_RELAXED) &&
            !__atomic_load_n(&s_suspended, __ATOMIC_RELAXED) && rate != 0) {
            send_gyro();
            sceKernelDelayThread(
                1000000 / (SceUInt)rate);
        } else {
            sceKernelDelayThread(100000);
        }
    }

    return 0;
}

static int accel_thread_main(SceSize args, void *argp)
{
    (void)args;
    (void)argp;

    while (1) {
        const uint16_t rate = __atomic_load_n(&s_accel_rate, __ATOMIC_RELAXED);
        if (__atomic_load_n(&s_active, __ATOMIC_RELAXED) &&
            __atomic_load_n(&s_enabled, __ATOMIC_RELAXED) &&
            !__atomic_load_n(&s_suspended, __ATOMIC_RELAXED) && rate != 0) {
            send_accel();
            sceKernelDelayThread(
                1000000 / (SceUInt)rate);
        } else {
            sceKernelDelayThread(100000);
        }
    }

    return 0;
}

static void create_thread(
    const char *name,
    int (*entry)(SceSize, void *),
    bool *started)
{
    if (*started) {
        return;
    }

    SceUID thread_id = sceKernelCreateThread(
        name,
        entry,
        0x40,
        0x40000,
        0,
        0,
        NULL);

    if (thread_id < 0) {
        vita_debug_log(
            "[Motion] create thread failed name=%s result=0x%08x",
            name,
            (unsigned int)thread_id);
        return;
    }

    int result = sceKernelStartThread(thread_id, 0, NULL);
    if (result < 0) {
        vita_debug_log(
            "[Motion] start thread failed name=%s result=0x%08x",
            name,
            (unsigned int)result);
        sceKernelDeleteThread(thread_id);
        return;
    }

    *started = true;
}

void vita_motion_init(void)
{
    if (s_initialized) {
        return;
    }

    int result = sceMotionStartSampling();
    if (result < 0 && result != SCE_MOTION_ERROR_ALREADY_SAMPLING) {
        vita_debug_log(
            "[Motion] start sampling failed result=0x%08x",
            (unsigned int)result);
        return;
    }

    result = sceMotionReset();
    if (result < 0) {
        vita_debug_log(
            "[Motion] reset failed result=0x%08x",
            (unsigned int)result);
    }

    create_thread(
        "vita_moonlight_gyro",
        gyro_thread_main,
        &s_gyro_thread_started);
    create_thread(
        "vita_moonlight_accel",
        accel_thread_main,
        &s_accel_thread_started);

    s_initialized = s_gyro_thread_started && s_accel_thread_started;
}

void vita_motion_start(int enabled)
{
    /* Wait for the input thread to apply its current system-UI state. */
    vita_motion_set_suspended(1);
    __atomic_store_n(&s_enabled, enabled != 0, __ATOMIC_RELAXED);

    if (!enabled) {
        vita_motion_stop();
        return;
    }

    vita_motion_init();
    __atomic_store_n(&s_active, s_initialized, __ATOMIC_RELAXED);
}

void vita_motion_stop(void)
{
    vita_motion_set_suspended(1);
    __atomic_store_n(&s_active, false, __ATOMIC_RELAXED);
    __atomic_store_n(&s_gyro_rate, 0, __ATOMIC_RELAXED);
    __atomic_store_n(&s_accel_rate, 0, __ATOMIC_RELAXED);
}

void vita_motion_set_suspended(int suspended)
{
    __atomic_store_n(&s_suspended, suspended != 0, __ATOMIC_RELAXED);
}

void vita_motion_set_state(
    uint16_t controller,
    uint8_t motion_type,
    uint16_t report_rate_hz)
{
    if (controller != 0 || !__atomic_load_n(&s_enabled, __ATOMIC_RELAXED)) {
        return;
    }

    if (motion_type == LI_MOTION_TYPE_GYRO) {
        __atomic_store_n(&s_gyro_rate, report_rate_hz, __ATOMIC_RELAXED);
    } else if (motion_type == LI_MOTION_TYPE_ACCEL) {
        __atomic_store_n(&s_accel_rate, report_rate_hz, __ATOMIC_RELAXED);
    }

    vita_debug_log(
        "[Motion] state controller=%u type=%u rate=%u",
        controller,
        motion_type,
        report_rate_hz);
}
