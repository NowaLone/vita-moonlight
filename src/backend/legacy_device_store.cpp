#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <time.h>
#include <zlib.h>
#include "moonlight/app_artwork.h"

#include <psp2/io/fcntl.h>
#include <psp2/io/stat.h>

#include "backend/legacy_device_store.h"
#include "device.h"
#include "config.h"
#include "debug.h"

namespace {

static bool s_initialized = false;

static bool ensure_directory(const char *path)
{
    int result = sceIoMkdir(path, 0777);
    return result >= 0 || result == 0x80010011;
}

static bool ensure_device_directory(const char *name)
{
    char path[512];
    if (!device_storage_name_valid(name)) return false;
    int length = snprintf(path, sizeof(path), "%s%s", config.key_dir, name);
    if (length < 0 || (size_t)length >= sizeof(path)) return false;
    if (!ensure_directory(path)) {
        vita_debug_log("[HostStore] cannot create host directory: %s", path);
        return false;
    }
    return true;
}

static void copy_string(char *destination, size_t size, const char *source)
{
    if (!destination || size == 0) {
        return;
    }

    destination[0] = '\0';
    if (!source) {
        return;
    }

    strncpy(destination, source, size - 1);
    destination[size - 1] = '\0';
}


static device_info_t *find_stored_host(const MoonlightHost *host)
{
    if (!host) return NULL;

    device_info_t *stored = NULL;

    if (host->host_id[0]) {
        stored = find_device_by_host_id(host->host_id);
        if (stored) return stored;
    }

    if (host->mac[0]) {
        for (int i = 0; i < known_devices.count; ++i) {
            if (known_devices.devices[i].mac[0] &&
                strcmp(known_devices.devices[i].mac, host->mac) == 0) {
                return &known_devices.devices[i];
            }
        }
    }

    if (host->internal[0]) {
        stored = find_device_by_address(host->internal);
        if (stored) return stored;
    }

    if (host->external[0]) {
        stored = find_device_by_address(host->external);
        if (stored) return stored;
    }

    if (host->name[0]) {
        stored = find_device(host->name);
        if (stored) return stored;
    }

    return NULL;
}

/* ponytail: one file per app ID until host deletion; add pruning if disk usage warrants it. */
static int artwork_path(const MoonlightHost *host, int application_id, char *out, size_t size)
{
    if (!s_initialized || !host || !out || !size || application_id <= 0 || !host->host_id[0]) return -1;
    out[0] = '\0';
    /* A cache must never fall back to a same-name/different-UUID PC. */
    device_info_t *stored = find_device_by_host_id(host->host_id);
    if (!stored || !stored->paired) return -1;
    const char *directory = stored->storage_name[0] ? stored->storage_name : stored->name;
    if (!device_storage_name_valid(directory)) return -1;
    int n = snprintf(out, size, "%s%s/app_%d.png", config.key_dir, directory, application_id);
    if (n < 0 || (size_t)n >= size) { out[0] = '\0'; return -1; }
    return 0;
}

static uint32_t artwork_u32(const unsigned char *data)
{
    return ((uint32_t)data[0] << 24) | ((uint32_t)data[1] << 16) |
           ((uint32_t)data[2] << 8) | data[3];
}

/* Check complete chunk framing/CRCs before a local file reaches the native decoder. */
static int artwork_png_valid(const unsigned char *data, size_t size)
{
    int w = 0, h = 0;
    if (!moonlight_artwork_extent(data, size, &w, &h)) return 0;
    size_t offset = 8;
    while (size - offset >= 12) {
        uint32_t count = artwork_u32(data + offset);
        if (count > size - offset - 12) return 0;
        uint32_t crc = artwork_u32(data + offset + 8 + count);
        if (crc32(0, data + offset + 4, count + 4) != crc) return 0;
        if (memcmp(data + offset + 4, "IEND", 4) == 0)
            return count == 0 && offset + 12 == size;
        offset = offset + count + 12;
    }
    return 0;
}

static void fill_host(const device_info_t *device, int id, MoonlightHost *host)
{
    *host = MoonlightHost();
    host->id = id;
    host->port = device->port;
    host->paired = device->paired ? 1 : 0;
    host->online = 0;
    host->prefer_external = device->prefer_external ? 1 : 0;

    copy_string(host->host_id, sizeof(host->host_id), device->host_id);
    copy_string(host->name, sizeof(host->name), device->name);
    copy_string(host->internal, sizeof(host->internal), device->internal);
    copy_string(host->external, sizeof(host->external), device->external);
    copy_string(host->mac, sizeof(host->mac), device->mac);
}

static void update_host_metadata(device_info_t *stored, const MoonlightHost *host)
{
    if (host->name[0]) {
        copy_string(stored->name, sizeof(stored->name), host->name);
    }
    if (host->internal[0]) {
        copy_string(stored->internal, sizeof(stored->internal), host->internal);
    }
    if (host->external[0]) {
        copy_string(stored->external, sizeof(stored->external), host->external);
    }
    if (host->mac[0]) {
        copy_string(stored->mac, sizeof(stored->mac), host->mac);
    }
    stored->port = host->port != 0 ? host->port : stored->port;
}

static device_info_t *append_host(const MoonlightHost *host, const char *host_id, bool paired)
{
    device_info_t info;
    memset(&info, 0, sizeof(info));
    update_host_metadata(&info, host);
    if (!info.name[0]) {
        copy_string(info.name, sizeof(info.name), host->internal);
    }
    copy_string(info.host_id, sizeof(info.host_id), host_id);
    if (!info.port) info.port = 47989;
    info.prefer_external = host->prefer_external != 0;
    info.paired = paired;
    return append_device(&info);
}

static int save_host(device_info_t *stored)
{
    if (!stored || !ensure_device_directory(
            stored->storage_name[0] ? stored->storage_name : stored->name)) {
        return -1;
    }
    return save_device_info(stored);
}

}

int legacy_device_store_read_artwork(const MoonlightHost *host, int application_id,
    char **body, size_t *length)
{
    if (!body || !length) return -1;
    *body = NULL;
    *length = 0;
    char path[512];
    if (artwork_path(host, application_id, path, sizeof(path)) != 0) return -1;
    struct stat info;
    time_t now = time(NULL);
    /* No stale hit after clock rollback; failure simply uses the paired HTTPS path. */
    if (stat(path, &info) != 0 || info.st_size < 33 || info.st_size > MOONLIGHT_ARTWORK_MAX_BYTES ||
        now == (time_t)-1 || info.st_mtime > now || now - info.st_mtime >= 24 * 60 * 60) return -1;
    FILE *file = fopen(path, "rb");
    if (!file) return -1;
    size_t size = (size_t)info.st_size;
    char *data = (char *)malloc(size);
    int valid = data && fread(data, 1, size, file) == size && fgetc(file) == EOF && !ferror(file);
    if (fclose(file) != 0) valid = 0;
    if (!valid || !artwork_png_valid((const unsigned char *)data, size)) {
        free(data);
        return -1;
    }
    *body = data;
    *length = size;
    vita_debug_log("[Artwork] disk cache hit app=%d bytes=%u", application_id, (unsigned int)size);
    return 0;
}

int legacy_device_store_write_artwork(const MoonlightHost *host, int application_id,
    const char *body, size_t length)
{
    char path[512], temporary[520];
    if (artwork_path(host, application_id, path, sizeof(path)) != 0 ||
        !artwork_png_valid((const unsigned char *)body, length)) return -1;
    int n = snprintf(temporary, sizeof(temporary), "%s.tmp", path);
    if (n < 0 || (size_t)n >= sizeof(temporary)) return -1;
    FILE *file = fopen(temporary, "wb");
    int valid = 0;
    if (file) {
        valid = fwrite(body, 1, length, file) == length && fflush(file) == 0;
        if (fclose(file) != 0) valid = 0;
    }
    if (valid) {
        /* Vita rename may reject replacement. Only remove an old cache after the
         * complete temporary file closes; interruption leaves a miss, never a partial PNG. */
        remove(path);
        valid = rename(temporary, path) == 0;
    }
    if (!valid) {
        remove(temporary);
        vita_debug_log("[Artwork] disk cache write failed app=%d", application_id);
        return -1;
    }
    vita_debug_log("[Artwork] disk cache saved app=%d bytes=%u", application_id, (unsigned int)length);
    return 0;
}

int legacy_device_store_init(void)
{
    if (s_initialized) {
        return 0;
    }

#ifdef USE_DIR_UMA0
    static const char *paths[] = {
        "uma0:data/moonlight/"
    };
#else
    static const char *paths[] = {
        "ux0:data/moonlight/",
        "ux0:moonlight/",
        "uma0:data/moonlight/"
    };
#endif

    const size_t path_count = sizeof(paths) / sizeof(paths[0]);

    for (size_t i = 0; i < path_count; ++i) {
        if (!ensure_directory(paths[i])) {
            continue;
        }

        copy_string(config.key_dir, sizeof(config.key_dir), paths[i]);
        load_all_known_devices();
        s_initialized = true;
        return 0;
    }

    return -1;
}

int legacy_device_store_get_hosts(MoonlightHost *out, int capacity)
{
    if (!s_initialized || capacity < 0) {
        return -1;
    }

    if (capacity == 0) {
        return known_devices.count;
    }

    if (!out) {
        return -1;
    }

    int count = known_devices.count;
    if (count > capacity) {
        count = capacity;
    }

    for (int i = 0; i < count; ++i) {
        fill_host(&known_devices.devices[i], i, &out[i]);
    }

    return count;
}

int legacy_device_store_add_host(const char *address, uint16_t port, const char *name)
{
    if (!s_initialized || !address || !address[0]) {
        return -1;
    }

    device_info_t *stored = find_device_by_address(address);
    if (!stored && name && name[0]) {
        stored = find_device(name);
    }

    if (stored) {
        if (name && name[0] && strcmp(stored->name, name) != 0) {
            copy_string(stored->name, sizeof(stored->name), name);
        }
        copy_string(stored->internal, sizeof(stored->internal), address);
        stored->port = port != 0 ? port : 47989;
    } else {
        device_info_t info;
        memset(&info, 0, sizeof(info));
        copy_string(info.name, sizeof(info.name), name && name[0] ? name : address);
        copy_string(info.internal, sizeof(info.internal), address);
        info.port = port != 0 ? port : 47989;
        stored = append_device(&info);
    }

    return save_host(stored);
}

int legacy_device_store_mark_paired(const MoonlightHost *host)
{
    if (!s_initialized || !host || !host->internal[0]) {
        return -1;
    }

    device_info_t *stored = find_stored_host(host);

    if (!stored) {
        stored = append_host(host, host->host_id, true);
    } else {
        update_host_metadata(stored, host);
        if (host->host_id[0] && !stored->host_id[0]) {
            copy_string(stored->host_id, sizeof(stored->host_id), host->host_id);
        }
        stored->prefer_external = host->prefer_external != 0;
        stored->paired = true;
    }

    return save_host(stored);
}


int legacy_device_store_set_host_id(
    const MoonlightHost *host,
    const char *host_id)
{
    if (!s_initialized || !host || !host_id || !host_id[0]) {
        return -1;
    }

    device_info_t *stored = find_stored_host(host);

    if (!stored) {
        stored = append_host(host, host_id, false);
    } else {
        copy_string(stored->host_id, sizeof(stored->host_id), host_id);
        update_host_metadata(stored, host);
    }

    int result = save_host(stored);
    if (result != 0) {
        return result;
    }

    vita_debug_log(
        "legacy_device_store_set_host_id: host %s uuid=%s storage=%s",
        stored->name,
        stored->host_id,
        stored->storage_name);

    return 0;
}

int legacy_device_store_delete_host(const MoonlightHost *host)
{
    if (!s_initialized || !host) {
        return -1;
    }

    device_info_t *stored = find_stored_host(host);
    if (!stored) {
        return -1;
    }

    return remove_device_by_info(stored) ? 0 : -1;
}

int legacy_device_store_get_client_directory(
    char *out,
    size_t size)
{
    static const char *client_directory_name = "client";

    if (!s_initialized || !out || size == 0) {
        return -1;
    }

    int length = snprintf(
        out,
        size,
        "%s%s",
        config.key_dir,
        client_directory_name);
    if (length < 0 || (size_t)length >= size) {
        return -1;
    }

    return ensure_directory(out) ? 0 : -1;
}

int legacy_device_store_get_server_certificate_path(
    const MoonlightHost *host, char *out, size_t size)
{
    if (!s_initialized || !out || !size) return -1;
    out[0] = '\0';
    device_info_t *stored = find_stored_host(host);
    if (!stored) return -1;
    const char *directory = stored->storage_name[0] ? stored->storage_name : stored->name;
    if (!device_storage_name_valid(directory)) return -1;
    int length = snprintf(out, size, "%s%s/server.pem", config.key_dir, directory);
    if (length < 0 || (size_t)length >= size) {
        out[0] = '\0';
        return -1;
    }
    return 0;
}

int legacy_device_store_get_client_unique_id_path(
    char *out,
    size_t size)
{
    char directory[512];

    if (legacy_device_store_get_client_directory(
            directory, sizeof(directory)) != 0 ||
        !out || size == 0) {
        return -1;
    }

    int length = snprintf(out, size, "%s/uniqueid.dat", directory);
    return length < 0 || (size_t)length >= size ? -1 : 0;
}
