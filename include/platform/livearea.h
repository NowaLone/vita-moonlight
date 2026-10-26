#ifndef VITA_MOONLIGHT_PLATFORM_LIVEAREA_H
#define VITA_MOONLIGHT_PLATFORM_LIVEAREA_H

#include <stdint.h>
#include <vitasdk/build_utils.h>

/* AppUtil's pinned header exposes a raw output pointer. The native LiveArea
 * event parser writes this SDK layout, including its reserved tail. */
typedef struct MoonlightLiveAreaEventParam {
    char param[1019];
    char reserved[32];
} MoonlightLiveAreaEventParam;
VITASDK_BUILD_ASSERT_EQ(1051, MoonlightLiveAreaEventParam);

/* The pinned VitaSDK has SceLiveArea_stub but no psp2/livearea.h.
 * Bind only the existing native exports used here. The final argument is 0:
 * old Sony headers call it FLAG_NONE; newer VitaSDK calls it the normal layer.
 * Do not use the disputed value 1 or link ScePromoterUtil for this operation. */
#ifdef __cplusplus
extern "C" {
#endif

int sceLiveAreaUpdateFrameAsync(const char *format_version, const char *frame_xml,
                              int32_t frame_xml_length, const char *contents_path,
                              uint32_t flags);
int sceLiveAreaGetStatus(void);

#ifdef __cplusplus
}
#endif

#endif
