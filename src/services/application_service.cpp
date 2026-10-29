#include <paf.h>
#include <paf/image/image.h>
#include <paf/graphics/graphics.h>
#include <paf/memory/heap_allocator.h>
#include <stdlib.h>

#include "moonlight/app_artwork.h"
#include "debug.h"

#include "services/application_service.h"
#include "services/connection_service.h"

namespace {

class RefreshAppsJob : public paf::job::JobItem {
public:
    RefreshAppsJob(MoonlightBackend &backend, ConnectionService &connection)
        : paf::job::JobItem("ApplicationService::RefreshAppsJob", NULL),
          m_backend(backend), m_connection(connection)
    {
    }

    virtual ~RefreshAppsJob() {}

    virtual void Run()
    {
        int result = m_backend.GetApplications(NULL, 0);
        m_connection.RecordWorkerResult(result);
    }

    virtual void Finish() {}

private:
    MoonlightBackend &m_backend;
    ConnectionService &m_connection;
};

}

ApplicationService::ApplicationService(MoonlightBackend &backend, ConnectionService &connection)
    : m_artwork_queue(NULL), m_backend(backend), m_connection(connection)
{
}

int ApplicationService::GetAll(MoonlightApplication *out, int capacity)
{
    return m_backend.GetApplications(out, capacity);
}

int ApplicationService::Refresh()
{
    if (paf::job::JobQueue::default_queue == NULL) {
        return -1;
    }

    int result = m_connection.BeginOperation(ConnectionService::Operation_Applications);
    if (result != 0) return result;

    paf::common::SharedPtr<paf::job::JobItem> item(new RefreshAppsJob(m_backend, m_connection));
    result = paf::job::JobQueue::default_queue->Enqueue(item);
    if (result != 0) m_connection.FinishUnstartedOperation();
    return result;
}

/* The job owns its token, compressed response and decoded image. Never retain a page/widget. */
class ApplicationService::ArtworkJob : public paf::job::JobItem {
public:
    ArtworkJob(MoonlightBackend &backend, int id)
        : JobItem("Application artwork", NULL), backend(backend), id(id), cancel(), done(0),
          width(0), height(0), pool(paf::gutil::GetDefaultSurfacePool()),
          heap(paf::memory::GetGlobalHeapAllocator()) {}

    virtual void Run()
    {
        char *body = NULL;
        size_t length = 0;
        int w = 0, h = 0;
        int phase = 0, decoded = -1, native_width = 0, native_height = 0;
        vita_debug_log("[Artwork] fetch app=%d", id);
        int result = backend.GetApplicationArtwork(id, &cancel, &body, &length);
        int png = moonlight_artwork_extent((const unsigned char *)body, length, &w, &h);
        vita_debug_log("[Artwork] response app=%d result=%d bytes=%u png=%d source=%dx%d pool=%d",
                       id, result, (unsigned int)length, png, w, h, pool ? 1 : 0);
        if (result == 0 && !moonlight_is_cancelled(&cancel) && pool && png) {
            phase = 1;
            moonlight_artwork_fit(w, h, &width, &height);
            paf::common::SharedPtr<paf::image::Image> image = paf::image::Image::Open(
                body, length, heap, paf::image::ImageFormat_Png);
            if (image.get()) {
                phase = 2;
                image = image->Resize(paf::image::ImageExtent(width, height),
                                      paf::image::ImageResizeType_Linear);
                if (image.get() && !moonlight_is_cancelled(&cancel)) {
                    phase = 3;
                    paf::graph::Surface::LoadOption option;
                    option.decode_heap = heap;
                    decoded = paf::graph::Surface::DecodeImage(pool, &option, surface, image);
                    if (surface.get()) {
                        native_width = surface->GetWidth();
                        native_height = surface->GetHeight();
                    }
                    if (decoded < 0) surface.clear();
                    if (surface.get() && (surface->GetWidth() > MOONLIGHT_ARTWORK_THUMB_SIZE ||
                                          surface->GetHeight() > MOONLIGHT_ARTWORK_THUMB_SIZE))
                        surface.clear();
                }
            }
        }
        free(body);
        if (moonlight_is_cancelled(&cancel)) surface.clear();
        vita_debug_log("[Artwork] complete app=%d cancelled=%d surface=%d phase=%d decode=0x%08X size=%dx%d",
                       id, moonlight_is_cancelled(&cancel) ? 1 : 0, surface.get() ? 1 : 0,
                       phase, (unsigned int)decoded, native_width, native_height);
        __atomic_store_n(&done, 1, __ATOMIC_RELEASE);
    }
    virtual void Finish() {}

    MoonlightBackend &backend;
    const int id;
    MoonlightCancellation cancel;
    int done;
    int width, height;
    paf::intrusive_ptr<paf::graph::Surface> surface;
    paf::graph::SurfacePool *pool;
    paf::memory::HeapAllocator *heap;
};

ApplicationService::~ApplicationService()
{
    Shutdown();
}

bool ApplicationService::RequestArtwork(int application_id)
{
    if (application_id <= 0 || m_artwork_job.get() || m_connection.IsBusy()) {
        vita_debug_log("[Artwork] request rejected app=%d job=%d busy=%d", application_id,
                       m_artwork_job.get() ? 1 : 0, m_connection.IsBusy() ? 1 : 0);
        return false;
    }
    if (!m_artwork_queue) {
        paf::job::JobQueue::Option option;
        option.workerNum = 1;
        option.workerStackSize = 256 * 1024; /* libcurl/OpenSSL and native image decoding. */
        m_artwork_queue = new paf::job::JobQueue("Application artwork", &option);
        if (!m_artwork_queue) {
            vita_debug_log("[Artwork] queue allocation failed");
            return false;
        }
    }
    m_artwork_job = paf::common::SharedPtr<paf::job::JobItem>(new ArtworkJob(m_backend, application_id));
    if (!m_artwork_job.get()) {
        vita_debug_log("[Artwork] job allocation failed app=%d", application_id);
        return false;
    }
    int result = m_artwork_queue->Enqueue(m_artwork_job);
    vita_debug_log("[Artwork] queued app=%d result=0x%08X", application_id, (unsigned int)result);
    if (result < 0) {
        m_artwork_job.reset();
        return false;
    }
    return true;
}

bool ApplicationService::TakeArtwork(int *application_id,
    paf::intrusive_ptr<paf::graph::Surface> *surface, int *width, int *height)
{
    ArtworkJob *job = static_cast<ArtworkJob *>(m_artwork_job.get());
    if (!job || !__atomic_load_n(&job->done, __ATOMIC_ACQUIRE)) return false;
    *application_id = moonlight_is_cancelled(&job->cancel) ? 0 : job->id;
    if (*application_id) *surface = job->surface;
    else surface->clear();
    job->surface.clear(); /* Release job/queue ownership before a pending stream launch. */
    *width = job->width;
    *height = job->height;
    m_artwork_job.reset();
    return true;
}

void ApplicationService::CancelArtwork()
{
    ArtworkJob *job = static_cast<ArtworkJob *>(m_artwork_job.get());
    if (job) moonlight_cancel(&job->cancel);
}

bool ApplicationService::IsArtworkIdle() const
{
    ArtworkJob *job = static_cast<ArtworkJob *>(m_artwork_job.get());
    return !job || __atomic_load_n(&job->done, __ATOMIC_ACQUIRE);
}

void ApplicationService::Shutdown()
{
    CancelArtwork();
    /* Final application teardown only; ordinary UI actions poll IsArtworkIdle(). */
    if (m_artwork_queue) {
        m_artwork_queue->WaitEmpty();
        delete m_artwork_queue;
        m_artwork_queue = NULL;
    }
    m_artwork_job.reset();
}
