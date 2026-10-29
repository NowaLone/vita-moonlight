#include <paf.h>

#include "common.h"
#include "debug.h"

#include "pages/page_apps.h"
#include "app/moonlight_app.h"
#include "pages/page_stream.h"
#include "pages/page_main.h"
#include "pages/page_pairing.h"

namespace page {

namespace {

/* Photos' furl-stack targets; CXML gives both content planes a left pivot. */
const float kNavigationDuration = 500.0f;
const float kNavigationOriginX = -480.0f;
const float kFoldedX = -596.0f;
const float kFoldedZ = -150.0f;
const float kRightAngle = 1.5707963f;

void stop_navigation(paf::ui::Widget *widget)
{
    if (!widget) return;
    widget->KillAnim(paf::ui::Widget::ANIM_MOVE);
    widget->KillAnim(paf::ui::Widget::ANIM_ROT);
    widget->KillAnim(paf::ui::Widget::ANIM_META_ALPHA);
}

void set_navigation(paf::ui::Widget *widget, float x, float z, float angle, float alpha)
{
    widget->SetPos(paf::math::v4(x, 0.0f, z));
    widget->SetRot(paf::math::v4(0.0f, angle, 0.0f));
    widget->SetMetaAlpha(alpha);
}

bool animate_navigation(paf::ui::Widget *widget, float x, float z, float angle,
                        float alpha, paf::ui::AnimCB finished, void *userdata)
{
    paf::Timer *move = new paf::Timer(kNavigationDuration, paf::Timer::FUNC_CIRQ_OUT);
    paf::Timer *rotate = new paf::Timer(kNavigationDuration, paf::Timer::FUNC_CIRQ_OUT);
    paf::Timer *opacity = new paf::Timer(kNavigationDuration * 0.8f, paf::Timer::FUNC_LINEAR);
    if (!move || !rotate || !opacity) {
        delete move;
        delete rotate;
        delete opacity;
        return false;
    }
    /* PAF owns timers after they are passed to the widget animation API. */
    int moved = widget->SetPos(paf::math::v4(x, 0.0f, z), move);
    int faded = widget->SetMetaAlpha(alpha, opacity);
    int rotated = widget->SetRot(paf::math::v4(0.0f, angle, 0.0f), 0, rotate,
        paf::ui::Widget::ANIM_ROT, 0, 0.0f, finished, userdata);
    return moved >= 0 && faded >= 0 && rotated >= 0;
}

} // namespace

Apps::Apps(int application_id)
    : Base("page_apps", "btn_close_apps",
           paf::Plugin::TransitionType_None,
           paf::Plugin::TransitionType_None),
      m_pending_app(0),
      m_app_count(0),
      m_livearea_application_id(application_id),
      m_launching(false),
      m_apps_ready(false),
      m_closing(false),
      m_navigation_pending(0),
      m_content(NULL),
      m_main_content(NULL),
      m_list(NULL) {
    if (!IsValid()) return;

    m_content = root->FindChild("plane_apps_content");
    Base *main = Base::Find("page_main");
    if (main && main->root) m_main_content = main->root->FindChild("plane_main_content");
    bind_decide(root, "btn_close_apps", OnBack, this);
    StartNavigation(false);

    m_list = static_cast<paf::ui::ListView *>(
        root->FindChild("list_view_generic"));

    if (m_list) {
        m_list->SetItemFactory(new ListViewFactory(this));
        m_list->InsertSegment(0, 1);
        m_list->SetCellSizeDefault(0, { 730.0f, 90.0f });
        m_list->SetGenerateMargin(paf::math::v2());
        m_list->SetSegmentLayoutType(0, paf::ui::ListView::LAYOUT_TYPE_LIST);
    }

    paf::common::MainThreadCallList::Register(ArtworkTask, this);
    MoonlightApp::Instance()->SetEventCallback(OnMoonlightEvent, this);

    paf::ui::Widget *title = root->FindChild("text_top");
    if (title) {
        ((paf::ui::Text *)title)->SetString(
            paf::wstring(ui_string("msg_applications")));
    }

    HideStatus(); /* ApplicationService opens the native progress message. */

    int result = MoonlightApp::Instance()->Applications().Refresh();
    if (result != 0) {
        m_livearea_application_id = 0;
        MoonlightApp::Instance()->Connection().ShowError(ui_text("msg_error_load_apps").c_str(), result);
        ShowEmptyState();
    }
}

Apps::~Apps() {
    /* Cancel native callbacks before this userdata or the closing page is released. */
    m_transitioning = false;
    paf::common::MainThreadCallList::Unregister(NavigationTask, this);
    stop_navigation(m_content);
    stop_navigation(m_main_content);
    if (m_main_content && m_content) {
        set_navigation(m_main_content, kNavigationOriginX, 0.0f, 0.0f, 1.0f);
    }

    paf::common::MainThreadCallList::Unregister(ArtworkTask, this);
    ClearArtwork();

    if (!MoonlightApp::Instance() ||
        !MoonlightApp::Instance()->IsInitialized()) {
        return;
    }

    Pairing *pairing = static_cast<Pairing *>(Base::Find("page_pairing"));
    if (pairing) {
        pairing->RestoreEventCallback();
        return;
    }

    Main *main = Main::Instance();
    if (main) {
        main->RestoreEventCallback();
        return;
    }

    MoonlightApp::Instance()->SetEventCallback(NULL, NULL);
}

void Apps::StartNavigation(bool closing)
{
    if (!m_content || !m_main_content) {
        vita_debug_log("[Apps] navigation containers unavailable");
        if (closing) Base::CloseCurrent();
        return;
    }

    m_transitioning = false;
    stop_navigation(m_content);
    stop_navigation(m_main_content);
    m_closing = closing;
    m_navigation_pending = 2;
    m_transitioning = true;
    root->SetActivate(false);
    if (!closing) set_navigation(m_content, 480.0f, 330.0f, -kRightAngle, 0.0f);

    float main_x = closing ? kNavigationOriginX : kFoldedX;
    float main_z = closing ? 0.0f : kFoldedZ;
    float main_angle = closing ? 0.0f : kRightAngle;
    float main_alpha = closing ? 1.0f : 0.15f;
    float apps_x = closing ? 480.0f : kNavigationOriginX;
    float apps_z = closing ? 330.0f : 0.0f;
    float apps_angle = closing ? -kRightAngle : 0.0f;
    float apps_alpha = closing ? 0.0f : 1.0f;
    if (!animate_navigation(m_main_content, main_x, main_z, main_angle, main_alpha,
                            NavigationFinished, this) ||
        !animate_navigation(m_content, apps_x, apps_z, apps_angle, apps_alpha,
                            NavigationFinished, this)) {
        /* A failed animation must neither strand input nor retain stale callbacks. */
        m_transitioning = false;
        stop_navigation(m_content);
        stop_navigation(m_main_content);
        set_navigation(m_main_content, main_x, main_z, main_angle, main_alpha);
        set_navigation(m_content, apps_x, apps_z, apps_angle, apps_alpha);
        m_navigation_pending = 0;
        m_transitioning = true;
        vita_debug_log("[Apps] navigation animation failed; completed immediately");
    }
    paf::common::MainThreadCallList::Register(NavigationTask, this);
}

void Apps::NavigationFinished(paf::Timer *timer, paf::ui::AnimListener *listener,
                              void *widget, void *userdata, void *unused)
{
    (void)timer;
    (void)listener;
    (void)widget;
    (void)unused;
    Apps *apps = static_cast<Apps *>(userdata);
    if (apps && apps->m_transitioning && apps->m_navigation_pending > 0) {
        --apps->m_navigation_pending;
    }
}

void Apps::NavigationTask(void *userdata)
{
    Apps *apps = static_cast<Apps *>(userdata);
    if (!apps->m_transitioning || apps->m_navigation_pending != 0) return;
    paf::common::MainThreadCallList::Unregister(NavigationTask, apps);
    apps->m_transitioning = false;
    if (apps->m_closing) {
        /* Defer page destruction until after the native animation callback returns. */
        delete apps;
        return;
    }
    if (Base::GetCurrent() == apps) {
        apps->root->SetActivate(true);
        apps->LaunchRequestedApplication();
    }
}

void Apps::OnBack(int32_t type, paf::ui::Handler *self, paf::ui::Event *event, void *userdata)
{
    (void)type;
    (void)self;
    (void)event;
    Apps *apps = static_cast<Apps *>(userdata);
    if (!apps || Base::GetCurrent() != apps || apps->IsTransitioning() || apps->m_pending_app ||
        MoonlightApp::Instance()->Connection().IsBusy()) return;
    apps->m_pending_app = -1;
    apps->m_transitioning = true;
    apps->root->SetActivate(false);
    MoonlightApp::Instance()->Applications().CancelArtwork();
}

void Apps::RestoreEventCallback() {
    if (MoonlightApp::Instance()->IsInitialized()) {
        MoonlightApp::Instance()->SetEventCallback(OnMoonlightEvent, this);
    }
}

paf::ui::ListItem *Apps::CreateListItem(
    paf::ui::listview::ItemFactory::CreateParam &param) {
    paf::Plugin::TemplateOpenParam tmp;
    g_plugin->TemplateOpen(param.parent, "template_app_list_item", tmp);

    paf::ui::ListItem *item = static_cast<paf::ui::ListItem *>(
        param.parent->GetChild(param.parent->GetChildrenNum() - 1));

    paf::ui::Widget *button = item->FindChild("image_button_app");
    if (!button || param.cell_index < 0 || param.cell_index >= m_app_count) {
        return item;
    }

    const MoonlightApplication &app = m_apps[param.cell_index];
    button->SetName((uint32_t)app.id);
    button->AddEventCallback(
        paf::ui::ButtonBase::CB_BTN_DECIDE,
        OnAppButton,
        this);

    button->SetString(
        paf::common::string_util::ToWString(
            app.name[0] ? app.name : ui_text("msg_application").c_str()));

    UpdateArtwork(item, param.cell_index);
    return item;
}

void Apps::OnAppButton(int32_t type,
                       paf::ui::Handler *self,
                       paf::ui::Event *event,
                       void *userdata) {
    (void)type;
    (void)event;

    Apps *apps = static_cast<Apps *>(userdata);
    paf::ui::Widget *button = static_cast<paf::ui::Widget *>(self);
    if (!apps || !button) return;

    const uint32_t app_id = button->GetName().GetIDHash();
    for (int i = 0; i < apps->m_app_count; ++i) {
        if ((uint32_t)apps->m_apps[i].id == app_id) {
            apps->SelectApp(i);
            return;
        }
    }
}

void Apps::SelectApp(int index) {
    if (m_transitioning || Base::GetCurrent() != this || m_launching ||
        MoonlightApp::Instance()->Connection().IsBusy() ||
        index < 0 || index >= m_app_count) return;

    if (m_pending_app) return;
    if (m_apps[index].id <= 0) {
        MoonlightApp::Instance()->Connection().ShowError(ui_text("msg_error_launch_app").c_str());
        return;
    }
    m_pending_app = m_apps[index].id;
    m_transitioning = true;
    root->SetActivate(false);
    MoonlightApp::Instance()->Applications().CancelArtwork();
}

void Apps::StartSelectedApp(int index)
{
    m_launching = true;
    HideStatus();

    int result = MoonlightApp::Instance()->Connection().Start(
        m_apps[index].id);

    if (result != 0) {
        m_launching = false;
        MoonlightApp::Instance()->Connection().ShowError(ui_text("msg_error_launch_app").c_str(), result);
        ShowEmptyState();
        return;
    }
}

void Apps::LaunchRequestedApplication()
{
    if (m_transitioning || !m_apps_ready) return;
    const int requested = m_livearea_application_id;
    m_livearea_application_id = 0; /* One attempt; never replay after failure/Back. */
    if (requested <= 0) return;
    for (int i = 0; i < m_app_count; ++i) {
        if (m_apps[i].id == requested) {
            SelectApp(i);
            return;
        }
    }
    MoonlightApp::Instance()->Connection().ShowError(
        ui_text("msg_app_unavailable").c_str());
}

void Apps::ShowEmptyState() {
    if (!root) return;
    paf::ui::Widget *widget = root->FindChild("text_apps_status");
    if (!widget) return;
    if (m_app_count == 0) {
        widget->Show(paf::common::transition::Type_Reset);
    } else {
        widget->Hide(paf::common::transition::Type_Reset);
    }
}

void Apps::HideStatus() {
    if (!root) return;

    paf::ui::Widget *widget = root->FindChild("text_apps_status");
    if (widget) {
        widget->Hide(paf::common::transition::Type_Reset);
    }
}

void Apps::ShowApps(int count) {
    if (!root || !m_list) return;

    ClearArtwork();
    m_apps_ready = false;
    const int existing = m_list->GetCellNum(0);
    if (existing > 0) {
        /* DeleteCell's third argument is a cell count, not the last index. */
        m_list->DeleteCell(0, 0, existing);
    }
    const int cells_after_delete = m_list->GetCellNum(0);

    /* Remove the old cells before changing their backing data. */
    m_app_count = 0;
    m_apps.clear();
    if (count < 0 || count > MOONLIGHT_MAX_APPLICATIONS) {
        MoonlightApp::Instance()->Connection().ShowError(ui_text("msg_error_load_apps").c_str());
        ShowEmptyState();
        return;
    }

    /* GetAll(NULL, 0) starts a network refresh, so an empty ready result needs no copy. */
    if (count > 0) {
        m_apps.resize(count);
        m_app_count = MoonlightApp::Instance()->Applications().GetAll(
            m_apps.data(), count);
        if (m_app_count < 0 || m_app_count > count) {
            m_app_count = 0;
            m_apps.clear();
            MoonlightApp::Instance()->Connection().ShowError(ui_text("msg_error_load_apps").c_str());
            ShowEmptyState();
            return;
        }
        m_apps.resize(m_app_count);
    }

    m_artwork_attempted.resize(m_app_count);
    for (int i = 0; i < m_app_count; ++i) m_artwork_attempted[i] = false;
    if (m_app_count > 0) {
        m_list->InsertCell(0, 0, m_app_count);

        /*
         * The status text is centred on the list and was drawn over the second
         * row. Keep this static text only for the empty state.
         */
        HideStatus();
    } else {
        ShowEmptyState();
    }

    m_apps_ready = true;
    vita_debug_log("[Apps] ShowApps count=%d cells before=%d after_delete=%d after_insert=%d",
        m_app_count, existing, cells_after_delete, m_list->GetCellNum(0));
}

int Apps::FindArtwork(int application_id) const
{
    for (int i = 0; i < ArtworkCacheSize; ++i)
        if (m_artwork[i].application_id == application_id) return i;
    return -1;
}

void Apps::UpdateArtwork(paf::ui::Widget *item, int index)
{
    if (!item || index < 0 || index >= m_app_count) return;
    paf::ui::Widget *cover = item->FindChild("plane_app_cover");
    if (!cover) return;
    int cached = FindArtwork(m_apps[index].id);
    if (cached >= 0 && m_artwork[cached].surface.get()) {
        cover->SetTexture(m_artwork[cached].surface);
        cover->SetSize(paf::math::v4(m_artwork[cached].width, m_artwork[cached].height));
        paf::ui::Widget *fallback = item->FindChild("plane_app_fallback");
        if (fallback) fallback->Hide();
    }
}

void Apps::ClearArtwork()
{
    if (MoonlightApp::Instance()) MoonlightApp::Instance()->Applications().CancelArtwork();
    /* Drop widget references too: Apps remains behind Stream while video needs the pool. */
    for (int i = 0; m_list && i < m_app_count; ++i) {
        paf::ui::ListItem *item = m_list->GetListItem(0, i);
        paf::ui::Widget *cover = item ? item->FindChild("plane_app_cover") : NULL;
        if (cover) {
            cover->SetTexture(paf::intrusive_ptr<paf::graph::Surface>());
            cover->SetSize(paf::math::v4(90.0f, 90.0f));
            paf::ui::Widget *fallback = item->FindChild("plane_app_fallback");
            if (fallback) fallback->Show();
        }
    }
    for (int i = 0; i < ArtworkCacheSize; ++i) {
        m_artwork[i].surface.clear();
        m_artwork[i].application_id = 0;
    }
    for (size_t i = 0; i < m_artwork_attempted.size(); ++i) m_artwork_attempted[i] = false;
}

void Apps::CompleteArtworkAction()
{
    if (!m_pending_app || !MoonlightApp::Instance()->Applications().IsArtworkIdle()) return;
    int pending = m_pending_app;
    m_pending_app = 0;
    m_transitioning = false;
    ClearArtwork();
    if (Base::GetCurrent() != this) return;
    if (pending == -1) { StartNavigation(true); return; }
    root->SetActivate(true);
    for (int i = 0; i < m_app_count; ++i) {
        if (m_apps[i].id == pending) { StartSelectedApp(i); return; }
    }
}

void Apps::ArtworkTask(void *userdata)
{
    Apps *apps = static_cast<Apps *>(userdata);
    ApplicationService &service = MoonlightApp::Instance()->Applications();
    int id = 0, width = 0, height = 0;
    paf::intrusive_ptr<paf::graph::Surface> surface;
    bool received = service.TakeArtwork(&id, &surface, &width, &height);
    if (apps->m_pending_app) {
        apps->CompleteArtworkAction();
        return;
    }
    if (!apps->m_apps_ready || !apps->m_list || apps->m_transitioning || apps->m_launching ||
        Base::GetCurrent() != apps || MoonlightApp::Instance()->Connection().IsBusy()) {
        service.CancelArtwork();
        return;
    }
    if (received && id > 0) {
        int index = -1;
        for (int i = 0; i < apps->m_app_count; ++i)
            if (apps->m_apps[i].id == id) { index = i; break; }
        if (index >= 0) {
            apps->m_artwork_attempted[index] = true;
            if (surface.get()) {
                int slot = -1;
                /* Retain at most twelve thumbnails; evict only rows PAF no longer generates. */
                for (int j = 0; j < ArtworkCacheSize; ++j) {
                    if (!apps->m_artwork[j].application_id) { slot = j; break; }
                }
                for (int j = 0; j < ArtworkCacheSize && slot < 0; ++j) {
                    bool generated = false;
                    for (int k = 0; k < apps->m_app_count; ++k) {
                        if (apps->m_apps[k].id == apps->m_artwork[j].application_id &&
                            apps->m_list->GetListItem(0, k)) { generated = true; break; }
                    }
                    if (!generated) slot = j;
                }
                if (slot >= 0) {
                    int evicted = apps->m_artwork[slot].application_id;
                    for (int k = 0; k < apps->m_app_count; ++k)
                        if (apps->m_apps[k].id == evicted) apps->m_artwork_attempted[k] = false;
                    apps->m_artwork[slot].application_id = id;
                    apps->m_artwork[slot].surface = surface;
                    apps->m_artwork[slot].width = width;
                    apps->m_artwork[slot].height = height;
                    apps->UpdateArtwork(apps->m_list->GetListItem(0, index), index);
                }
            }
        }
    }
    if (!service.IsArtworkIdle()) return;
    for (int i = 0; i < apps->m_app_count; ++i) {
        if (!apps->m_artwork_attempted[i] && apps->m_list->GetListItem(0, i)) {
            if (!service.RequestArtwork(apps->m_apps[i].id)) apps->m_artwork_attempted[i] = true;
            return;
        }
    }
}

void Apps::OnMoonlightEvent(
    const MoonlightEvent *event,
    void *userdata) {
    Apps *apps = (Apps *)userdata;
    if (!apps || !event) return;

    switch (event->type) {
    case MOONLIGHT_EVENT_APPLICATIONS_READY:
        apps->ShowApps(event->result);
        if (!apps->m_apps_ready) apps->m_livearea_application_id = 0;
        apps->LaunchRequestedApplication();
        break;

    case MOONLIGHT_EVENT_APPLICATIONS_FAILED: {
        apps->m_livearea_application_id = 0;
        MoonlightApp::Instance()->Connection().ShowError(ui_text("msg_error_load_apps").c_str(), event->result);
        apps->ShowEmptyState();
        break;
    }

    case MOONLIGHT_EVENT_CONNECTION_FAILED:
    case MOONLIGHT_EVENT_CONNECTION_CLOSED:
        apps->ClearArtwork();
        apps->m_apps_ready = false;
        if (apps->m_pending_app) {
            apps->m_transitioning = false;
            apps->root->SetActivate(Base::GetCurrent() == apps);
        }
        apps->m_pending_app = 0;
        apps->m_livearea_application_id = 0;
        break;

    case MOONLIGHT_EVENT_STREAM_STARTED: {
        if (!Base::IsOpen("page_stream")) {
            Stream *stream = new Stream();
            if (!stream->IsValid()) {
                delete stream;
                MoonlightApp::Instance()->Connection().ShowError(ui_text("msg_error_open_stream").c_str());
            }
        }

        apps->HideStatus();
        break;
    }

    case MOONLIGHT_EVENT_STREAM_STOPPED:
        if (Base::IsOpen("page_stream")) {
            Base *stream = Base::Find("page_stream");
            delete stream;
        }

        Stream::ScheduleFrameBufferRelease();
        apps->m_launching = false;
        apps->ShowEmptyState();
        break;

    case MOONLIGHT_EVENT_STREAM_FAILED: {
        /* Failed/cancelled setup may have created buffers without publishing STARTED. */
        Stream::ScheduleFrameBufferRelease();
        apps->m_launching = false;
        /* ConnectionService owns launch errors and remote-quit confirmation. */
        apps->ShowEmptyState();
        break;
    }

    default:
        break;
    }
}

}
