#ifdef __SNC__
#include <kernel.h>
#else
#include <psp2/kernel/clib.h>
#endif

#include <paf.h>

#include "app/moonlight_app.h"
#include "common.h"
#include "debug.h"

static int s_startup_result = -1;
static MoonlightApp *s_startup_app = NULL;

static void loadPluginCB(paf::Plugin *plugin)
{
    s_startup_app = MoonlightApp::Instance();
    if (s_startup_app) s_startup_result = s_startup_app->Start(plugin);
}

static void StartupErrorTask(void *userdata)
{
    MoonlightApp *app = static_cast<MoonlightApp *>(userdata);
    if (app->Connection().IsBusy()) return;
    paf::common::MainThreadCallList::Unregister(StartupErrorTask, userdata);
    paf::Framework::Instance()->RequestShutdown();
}

static Locale interface_locale(Locale system_locale)
{
    return system_locale == Locale_RU ? Locale_RU : Locale_EN;
}

int paf_runtime_main(void)
{
    paf::Framework::InitParam fwParam;
    fwParam.mode = paf::Framework::Mode_Normal;
    paf::Framework::SampleInit(&fwParam);
#ifdef MOONLIGHT_SYSTEM_APP
    // Apps needs one full-size source while producing bounded cover thumbnails.
    // Keep the text pool small to retain room for Moonlight's separate newlib heap.
    fwParam.mode = paf::Framework::Mode_Application;
    fwParam.surface_pool_size = 8 * 1024 * 1024;
    fwParam.text_surface_pool_size = 1 * 1024 * 1024;
#endif
    fwParam.graphics_option = 7;

    paf::Framework *paf_fw = new paf::Framework(fwParam);
    if (paf_fw == NULL) {
        return -1;
    }

    paf_fw->LoadCommonResourceSync();

    paf::Plugin::InitParam pluginParam;
    pluginParam.name = "vita_moonlight_ui";
    pluginParam.caller_name = "__main__";
    pluginParam.resource_file = "app0:/vita_moonlight_ui.rco";
    // Keep common/system UI in the system locale; select a complete app dictionary.
    pluginParam.locale = interface_locale(paf_fw->GetLocale());
    pluginParam.init_func = NULL;
    pluginParam.start_func = loadPluginCB;
    pluginParam.stop_func = NULL;
    pluginParam.exit_func = NULL;

    s_startup_result = -1;
    s_startup_app = NULL;
    paf::Plugin::LoadSync(pluginParam);
    if (s_startup_result != 0) {
        vita_debug_log("[App] startup failed result=0x%08X", (unsigned int)s_startup_result);
        if (s_startup_app && paf::Plugin::Find("vita_moonlight_ui")) {
            s_startup_app->Connection().ShowError(ui_text("msg_error_startup").c_str(), s_startup_result);
            paf::common::MainThreadCallList::Register(StartupErrorTask, s_startup_app);
        } else {
            paf_fw->RequestShutdown();
        }
    }
    paf_fw->Run();
    if (s_startup_app) s_startup_app->Shutdown();
    return s_startup_result;
}
