#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <psp2/sysmodule.h>

#include "services/livearea_service.h"
#include "platform/livearea.h"
#include "debug.h"
#include "common.h"

namespace {

/* Accept XML 1.0 characters and complete UTF-8 sequences. Stored/discovered
 * names may have been truncated at a byte boundary; replace invalid bytes. */
static int label_character_length(const unsigned char *text, int available)
{
    const unsigned int first = text[0];
    if (first < 0x80) return first >= 0x20 || first == 9 || first == 10 || first == 13 ? 1 : 0;
    const int length = first >= 0xc2 && first <= 0xdf ? 2 :
        first >= 0xe0 && first <= 0xef ? 3 : first >= 0xf0 && first <= 0xf4 ? 4 : 0;
    if (!length || available < length) return 0;
    unsigned int value = first & (0x7f >> length);
    for (int i = 1; i < length; ++i) {
        if ((text[i] & 0xc0) != 0x80) return 0;
        value = (value << 6) | (text[i] & 0x3f);
    }
    if ((length == 3 && value < 0x800) || (length == 4 && value < 0x10000) ||
        (value >= 0xd800 && value <= 0xdfff) || value > 0x10ffff ||
        value == 0xfffe || value == 0xffff) return 0;
    return length;
}

static int make_frame_xml(char *xml, unsigned int capacity, int frame, const char *label,
                          const char *host_key, int application_id, bool welcome)
{
    if (!xml || !label || frame < 1 || frame > 7) return -1;
    welcome = welcome && frame < 7;
    paf::string welcome_label;
    if (welcome) {
        if (frame == 2 || frame == 3) {
            welcome_label = ui_text(frame == 2 ? "msg_moonlight_title" : "msg_livearea_welcome");
        }
        label = welcome_label.c_str();
    }
    char escaped[256 * 6 + 1];
    int used = 0;
    for (int i = 0; i < 256 && label[i];) {
        const char *entity = NULL;
        switch (label[i]) {
        case '&': entity = "&amp;"; break;
        case '<': entity = "&lt;"; break;
        case '>': entity = "&gt;"; break;
        case '\"': entity = "&quot;"; break;
        case '\'': entity = "&apos;"; break;
        }
        if (entity) {
            for (int j = 0; entity[j]; ++j) escaped[used++] = entity[j];
            ++i;
        } else {
            int length = label_character_length((const unsigned char *)label + i, 256 - i);
            if (!length) {
                escaped[used++] = '?';
                ++i;
            } else {
                for (int j = 0; j < length; ++j) escaped[used++] = label[i++];
            }
        }
    }
    escaped[used] = '\0';

    char target[160] = {0};
    if (!welcome && label[0] && host_key && host_key[0] && (frame == 7 || application_id > 0)) {
        snprintf(target, sizeof(target), "<target>psla:moonlight1/%s/%d</target>",
                 host_key, frame == 7 ? 0 : application_id);
    }

    const char *background = "";
    const char *image = "";
    const char *text_style = "origin=\"frame\" width=\"440\" height=\"48\" align=\"center\" valign=\"center\" "
        "text-align=\"center\" text-valign=\"center\" line-align=\"center\"";
    if (!welcome && label[0]) {
        if (frame == 7) {
            background = "<background width=\"280\" height=\"158\" align=\"center\" valign=\"top\">pc_card.png</background>";
            image = "<image origin=\"background\" width=\"80\" height=\"80\" align=\"center\" valign=\"center\">pc.png</image>";
            text_style = "origin=\"background\" width=\"280\" height=\"32\" align=\"center\" valign=\"bottom\" "
                "text-align=\"center\" text-valign=\"center\" line-align=\"center\" "
                "margin-left=\"12\" margin-right=\"12\" margin-bottom=\"12\"";
        } else {
            background = "<background width=\"472\" height=\"48\" x=\"6\" y=\"2\" align=\"center\" valign=\"center\">app_row.png</background>";
            image = "<image origin=\"background\" width=\"32\" height=\"32\" x=\"-210\" align=\"center\" valign=\"center\">app.png</image>";
            text_style = "origin=\"background\" width=\"472\" height=\"48\" align=\"left\" valign=\"center\" "
                "text-align=\"left\" text-valign=\"center\" line-align=\"left\" margin-left=\"50\" margin-right=\"16\"";
        }
    }
    int length = snprintf(xml, capacity,
        "<frame id=\"frame%d\" multi=\"o\" autoflip=\"0\">"
        "<liveitem default=\"on\">"
        "%s%s%s"
        "<text %s word-wrap=\"off\" ellipsis=\"on\">"
        "<str size=\"%d\" color=\"%s\" bold=\"off\" shadow=\"off\">%s</str>"
        "</text></liveitem></frame>", frame, target, background, image, text_style,
        welcome ? (frame == 2 ? 28 : 20) : 22,
        welcome && frame == 3 ? "#d0d0d0" : "#ffffff", escaped);
    return length < 0 || (unsigned int)length >= capacity ? -1 : length;
}

}

LiveAreaService::LiveAreaService()
    : m_dirty(0), m_pending_frame(-1), m_module_state(0), m_has_host(false)
{
    memset(m_labels, 0, sizeof(m_labels));
    m_host_key[0] = '\0';
    memset(m_application_ids, 0, sizeof(m_application_ids));
}

void LiveAreaService::Connected(const MoonlightHost *host)
{
    if (!host || !host->internal[0]) return;
    memset(m_labels, 0, sizeof(m_labels));
    strncpy(m_labels[6], host->name[0] ? host->name : host->internal, sizeof(m_labels[6]) - 1);
    memset(m_application_ids, 0, sizeof(m_application_ids));
    const char *hex = "0123456789abcdef";
    int i = 0;
    for (; i < 32 && host->host_id[i]; ++i) {
        unsigned int byte = (unsigned char)host->host_id[i];
        m_host_key[i * 2] = hex[byte >> 4];
        m_host_key[i * 2 + 1] = hex[byte & 15];
    }
    m_host_key[i * 2] = '\0';
    m_has_host = true;
    m_dirty = 0x7f;
}

void LiveAreaService::Applications(const MoonlightApplication *apps, int count)
{
    if (!m_has_host || count < 0 || count > 6 || (!apps && count > 0)) return;
    for (int i = 0; i < 6; ++i) {
        memset(m_labels[i], 0, sizeof(m_labels[i]));
        m_application_ids[i] = i < count ? apps[i].id : 0;
        if (i < count) strncpy(m_labels[i], apps[i].name, sizeof(m_labels[i]) - 1);
    }
    m_dirty = 0x7f;
}

void LiveAreaService::Poll(bool allow_submit)
{
    if (m_pending_frame >= 0) {
        const int result = sceLiveAreaGetStatus();
        if (result == 1) return;
        vita_debug_log("[LiveArea] frame%d complete result=0x%08X", m_pending_frame + 1, (unsigned int)result);
        /* A newly captured snapshot dirties every slot, including the pending
         * one. An older failed completion must not discard that newer work. */
        if (result < 0 && !(m_dirty & (1u << m_pending_frame))) m_dirty = 0;
        m_pending_frame = -1;
        return;
    }
    if (!allow_submit || !m_dirty || m_module_state < 0) return;

    if (m_module_state == 0) {
        int result = sceSysmoduleIsLoaded(SCE_SYSMODULE_LIVEAREA);
        if (result != SCE_SYSMODULE_LOADED) result = sceSysmoduleLoadModule(SCE_SYSMODULE_LIVEAREA);
        vita_debug_log("[LiveArea] module result=0x%08X", (unsigned int)result);
        m_module_state = result < 0 ? -1 : 1;
        if (result < 0) return;
    }

    /* Publish app slots before the PC card. Native frame updates are serial,
     * not an atomic seven-frame transaction. Coalesce new snapshots in place. */
    int frame = 0;
    while (!(m_dirty & (1u << frame))) ++frame;
    bool has_apps = false;
    for (int i = 0; i < 6; ++i) if (m_labels[i][0]) has_apps = true;
    char xml[3072];
    const int length = make_frame_xml(xml, sizeof(xml), frame + 1, m_labels[frame],
        m_host_key, frame < 6 ? m_application_ids[frame] : 0, !has_apps);
    const int result = length < 0 ? -1 : sceLiveAreaUpdateFrameAsync(
        "01.00", xml, length, "app0:sce_sys/livearea/contents", 0);
    vita_debug_log("[LiveArea] frame%d submit bytes=%d result=0x%08X", frame + 1, length, (unsigned int)result);
    if (result < 0) {
        m_dirty = 0;
        return;
    }
    /* Clear on submission, not completion: a newer snapshot may dirty this
     * same slot while SceShell is processing the older request. */
    m_dirty &= ~(1u << frame);
    m_pending_frame = frame;
}

static int hex_digit(char value)
{
    if (value >= '0' && value <= '9') return value - '0';
    if (value >= 'a' && value <= 'f') return value - 'a' + 10;
    return -1;
}

int LiveAreaService::ParseTarget(const char *parameter, MoonlightHost *identity, int *application_id)
{
    if (!parameter || !identity || !application_id || strncmp(parameter, "moonlight1/", 11) != 0) return 0;
    memset(identity, 0, sizeof(*identity));
    const char *cursor = parameter + 11;
    int i = 0;
    for (; i < 32 && cursor[0] && cursor[0] != '/'; ++i) {
        int high = hex_digit(cursor[0]);
        int low = hex_digit(cursor[1]);
        if (high < 0 || low < 0 || (high == 0 && low == 0)) return 0;
        identity->host_id[i] = (char)((high << 4) | low);
        cursor += 2;
    }
    if (i == 0 || cursor[0] != '/') return 0;
    identity->host_id[i] = '\0';
    ++cursor;
    if (!cursor[0] || (cursor[0] == '0' && cursor[1])) return 0;
    int id = 0;
    for (; cursor[0]; ++cursor) {
        if (cursor[0] < '0' || cursor[0] > '9') return 0;
        int digit = cursor[0] - '0';
        if (id > (INT_MAX - digit) / 10) return 0;
        id = id * 10 + digit;
    }
    *application_id = id;
    return 1;
}

void LiveAreaService::Shutdown()
{
    m_dirty = 0;
    m_has_host = false;
    /* SceShell owns a submitted request; there is no cancellation API here.
     * Keep SceLiveAreaUtil resident until process exit, including pending work. */
}
