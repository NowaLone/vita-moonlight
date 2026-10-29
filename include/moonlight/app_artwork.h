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

/* Average source rectangles into a tightly packed thumbnail. Channel order is preserved
 * (RGBA/BGRA); native Surface::Load/Copy own decoding, texture layout and cache flushing. */
static inline int moonlight_artwork_reduce(const unsigned char *src, size_t size,
    int sw, int sh, int stride, unsigned char *dst, int dw, int dh)
{
    if (!src || !dst || sw < 1 || sh < 1 || sw > 1024 || sh > 1024 ||
        dw < 1 || dh < 1 || dw > MOONLIGHT_ARTWORK_THUMB_SIZE ||
        dh > MOONLIGHT_ARTWORK_THUMB_SIZE || stride < sw * 4 || stride > 4096 ||
        size < (size_t)(sh - 1) * stride + sw * 4) return 0;
    for (int y = 0; y < dh; ++y) {
        int y0 = y * sh / dh, y1 = (y + 1) * sh / dh;
        if (y1 <= y0) y1 = y0 + 1;
        for (int x = 0; x < dw; ++x) {
            int x0 = x * sw / dw, x1 = (x + 1) * sw / dw;
            if (x1 <= x0) x1 = x0 + 1;
            unsigned int sum[4] = {0, 0, 0, 0};
            unsigned int count = (x1 - x0) * (y1 - y0);
            for (int sy = y0; sy < y1; ++sy) {
                for (int sx = x0; sx < x1; ++sx) {
                    for (int c = 0; c < 4; ++c)
                        sum[c] = sum[c] + src[(size_t)sy * stride + sx * 4 + c];
                }
            }
            for (int c = 0; c < 4; ++c)
                dst[(y * dw + x) * 4 + c] = (unsigned char)(sum[c] / count);
        }
    }
    return 1;
}

#endif
