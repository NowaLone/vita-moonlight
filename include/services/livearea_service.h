#ifndef VITA_MOONLIGHT_LIVEAREA_SERVICE_H
#define VITA_MOONLIGHT_LIVEAREA_SERVICE_H

#include "moonlight/types.h"

/* Owned and driven by MoonlightApp on the PAF main thread. */
class LiveAreaService {
public:
    LiveAreaService();
    void Connected(const MoonlightHost *host);
    void Applications(const MoonlightApplication *apps, int count);
    /* Decode only our versioned target, never an address supplied by a URI. */
    static int ParseTarget(const char *parameter, MoonlightHost *identity, int *application_id);
    void Poll(bool allow_submit);
    void Shutdown();

private:
    char m_labels[7][256];
    char m_host_key[65];
    int m_application_ids[6];
    unsigned int m_dirty;
    int m_pending_frame;
    int m_module_state;
    bool m_has_host;
};

#endif
