#ifndef VITA_MOONLIGHT_PAGE_APPS_H
#define VITA_MOONLIGHT_PAGE_APPS_H

#include "pages/page.h"
#include "moonlight/types.h"

namespace page {

class Apps : public Base {
public:
    class ListViewFactory : public paf::ui::listview::ItemFactory {
    public:
        explicit ListViewFactory(Apps *parent) : m_parent(parent) {}
        virtual paf::ui::ListItem *Create(CreateParam &param) {
            return m_parent->CreateListItem(param);
        }
    private:
        Apps *m_parent;
    };

    explicit Apps(int application_id = 0);
    virtual ~Apps();

    void RestoreEventCallback();
    paf::ui::ListItem *CreateListItem(paf::ui::listview::ItemFactory::CreateParam &param);

private:
    static void OnBack(int32_t type, paf::ui::Handler *self, paf::ui::Event *event, void *userdata);
    static void NavigationFinished(paf::Timer *timer, paf::ui::AnimListener *listener,
                                   void *widget, void *userdata, void *unused);
    static void NavigationTask(void *userdata);
    void StartNavigation(bool closing);
    static void OnAppButton(int32_t type, paf::ui::Handler *self, paf::ui::Event *event, void *userdata);
    static void OnMoonlightEvent(const MoonlightEvent *event, void *userdata);
    void ShowEmptyState();
    void HideStatus();
    void ShowApps(int count);
    void SelectApp(int index);
    void LaunchRequestedApplication();

    paf::vector<MoonlightApplication> m_apps;
    int m_app_count;
    int m_livearea_application_id;
    bool m_launching;
    bool m_apps_ready;
    bool m_closing;
    int m_navigation_pending;
    paf::ui::Widget *m_content;
    paf::ui::Widget *m_main_content;
    paf::ui::ListView *m_list;

};

}

#endif
