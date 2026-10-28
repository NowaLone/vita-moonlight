#ifdef __SNC__
#include <kernel.h>
#else
#include <psp2/kernel/clib.h>
#endif

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "common.h"
#include "debug.h"
#include <paf/widget/w_button_base.h>

paf::Plugin *g_plugin = NULL;
static int s_debug_log_enabled = 0;

const wchar_t *ui_string(const char *id)
{
    const wchar_t *text = g_plugin ? g_plugin->GetString(id) : NULL;
    return text ? text : L"";
}

paf::string ui_text(const char *id)
{
    paf::string text;
    if (paf::common::Utf16ToUtf8(ui_string(id), &text) < 0) {
        vita_debug_log("[Locale] UTF-8 conversion failed: %s", id);
        text.clear();
    }
    return text;
}

void trim_incomplete_utf8(char *text)
{
    size_t end = strlen(text);
    if (end == 0) return;
    size_t start = end - 1;
    while (start > 0 && ((unsigned char)text[start] & 0xc0) == 0x80) --start;
    unsigned char first = (unsigned char)text[start];
    size_t length = first < 0x80 ? 1 : first < 0xe0 ? 2 : first < 0xf0 ? 3 : 4;
    if (end - start < length) text[start] = '\0';
}

extern "C" void vita_debug_log_set_enabled(int enabled)
{
    s_debug_log_enabled = enabled ? 1 : 0;
}

extern "C" void vita_debug_log(const char *fmt, ...)
{
    char line[512];
    va_list args;
    int length;

    if (!s_debug_log_enabled || !fmt) {
        return;
    }

    va_start(args, fmt);
    length = vsnprintf(line, sizeof(line), fmt, args);
    va_end(args);
    if (length < 0) {
        return;
    }
    sceClibPrintf("%s\n", line);

}

paf::Plugin::PageOpenParam make_open_param(paf::Plugin::TransitionType transition) {
    paf::Plugin::PageOpenParam param;
    param.option = paf::Plugin::PageOption_None;
    param.fade = true;
    param.fade_time_ms = 200.0f;
    param.transition_type = transition;
    return param;
}

paf::Plugin::PageCloseParam make_close_param(paf::Plugin::TransitionType transition) {
    paf::Plugin::PageCloseParam param;
    param.fade = true;
    param.fade_time_ms = 200.0f;
    param.transition_type = transition;
    return param;
}

void bind_decide(paf::ui::Widget *root, const char *child_id, DecideCb cb, void *userdata) {
    if (root == NULL || child_id == NULL || cb == NULL) {
        return;
    }
    paf::ui::Widget *child = root->FindChild(child_id);
    if (child != NULL) {
        child->SetEventCallback(paf::ui::ButtonBase::CB_BTN_DECIDE, cb, userdata);
    }
}

void set_widget_focusable(paf::ui::Widget *widget, bool on) {
    if (widget == NULL) {
        return;
    }
    if (on) {
        widget->EnableEvent(paf::ui::EV_FOCUS);
    } else {
        widget->EnableFocusEvent(false);
        widget->DisableEvent(paf::ui::EV_FOCUS);
        widget->ReleaseFocus();
    }
}

void set_button_enabled(paf::ui::Widget *button, bool enabled) {
    if (button == NULL) {
        return;
    }

    /*
     * Use PAF's native ButtonBase disabled state and its disabled text color;
     * SetActivate is kept in sync because it controls widget interaction.
     */
    paf::ui::ButtonBase *button_base =
        static_cast<paf::ui::ButtonBase *>(button);
    button_base->SetDisableColor(0.55f, 0.55f, 0.55f, 1.0f);
    if (enabled) {
        button_base->Enable();
    } else {
        button_base->Disable();
    }
    button->SetActivate(enabled);
}

void set_child_text(paf::ui::Widget *parent, const char *id, const char *text) {
    if (parent == NULL || id == NULL || text == NULL) {
        return;
    }
    paf::ui::Widget *widget = parent->FindChild(id);
    if (widget != NULL) {
        ((paf::ui::Text *)widget)->SetString(
            paf::common::string_util::ToWString(text));
    }
}
