#ifndef VITA_MOONLIGHT_APP_ARTWORK_H
#define VITA_MOONLIGHT_APP_ARTWORK_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define MOONLIGHT_ARTWORK_MAX_BYTES (512 * 1024)
#define MOONLIGHT_ARTWORK_THUMB_SIZE 90

/* Sunshine's appasset is PNG. Bound its header before handing it to the native decoder. */
static inline int moonlight_artwork_extent(const unsigned char *data, size_t size,
                                           int *width, int *height)
{
    if (!data || !width || !height || size < 33 || size > MOONLIGHT_ARTWORK_MAX_BYTES ||
        memcmp(data, "\x89PNG\r\n\x1a\n\0\0\0\x0dIHDR", 16) != 0) return 0;
    uint32_t w = ((uint32_t)data[16] << 24) | ((uint32_t)data[17] << 16) |
                 ((uint32_t)data[18] << 8) | data[19];
    uint32_t h = ((uint32_t)data[20] << 24) | ((uint32_t)data[21] << 16) |
                 ((uint32_t)data[22] << 8) | data[23];
    if (w == 0 || h == 0 || w > 1024 || h > 1024) return 0;
    *width = (int)w;
    *height = (int)h;
    return 1;
}

/* Fit the complete cover in Music's square slot, including portrait GameStream artwork. */
static inline void moonlight_artwork_fit(int width, int height, int *w, int *h)
{
    *w = MOONLIGHT_ARTWORK_THUMB_SIZE;
    *h = MOONLIGHT_ARTWORK_THUMB_SIZE;
    if (width > height) *h = height * MOONLIGHT_ARTWORK_THUMB_SIZE / width;
    else *w = width * MOONLIGHT_ARTWORK_THUMB_SIZE / height;
    if (*w < 1) *w = 1;
    if (*h < 1) *h = 1;
}

#endif
