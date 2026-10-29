#ifndef VITA_MOONLIGHT_APPLICATION_SERVICE_H
#define VITA_MOONLIGHT_APPLICATION_SERVICE_H

#include <paf.h>
#include "backend/moonlight_backend.h"

class ConnectionService;

class ApplicationService {
public:
    ApplicationService(MoonlightBackend &backend, ConnectionService &connection);

    ~ApplicationService();

    int GetAll(MoonlightApplication *out, int capacity);
    int Refresh();

    /* One optional image job; control/navigation cancels and polls idle before proceeding. */
    bool RequestArtwork(int application_id);
    bool TakeArtwork(int *application_id, paf::intrusive_ptr<paf::graph::Surface> *surface,
                     int *width, int *height);
    void CancelArtwork();
    bool IsArtworkIdle() const;
    void Shutdown();

private:
    class ArtworkJob;
    paf::job::JobQueue *m_artwork_queue;
    paf::common::SharedPtr<paf::job::JobItem> m_artwork_job;
    MoonlightBackend &m_backend;
    ConnectionService &m_connection;
};

#endif
