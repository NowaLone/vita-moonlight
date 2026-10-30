#include <paf.h>
#include <paf/graphics/graphics.h>
#include <psp2/gxm.h>
#include <stdlib.h>
#include <stddef.h>

#include "moonlight/app_artwork.h"
#include "debug.h"

#include "services/application_service.h"
#include "services/connection_service.h"

namespace {

/* Native Music's option constructor stores resize_type at 0x6c and image_order
 * at 0x84. Small enums also break inline Surface geometry/sizeof(new Surface). */
static_assert(sizeof(paf::graph::Surface::LoadOption) == 0x98, "Native PAF LoadOption size");
static_assert(sizeof(ImageMode) == 4, "Native PAF ImageMode width");
static_assert(sizeof(ImageOrder) == 4, "Native PAF ImageOrder width");
static_assert(offsetof(paf::graph::Surface::LoadOption, resize_type) == 0x6c,
              "Native PAF resize_type offset");
static_assert(offsetof(paf::graph::Surface::LoadOption, image_order) == 0x84,
              "Native PAF image_order offset");

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
          width(0), height(0), pool(paf::gutil::GetDefaultSurfacePool()) {}

    virtual void Run()
    {
        char *body = NULL;
        size_t length = 0;
        int w = 0, h = 0;
        int phase = 0, decoded = -1;
        vita_debug_log("[Artwork] fetch app=%d", id);
        int result = backend.GetApplicationArtwork(id, &cancel, &body, &length);
        int png = moonlight_artwork_extent((const unsigned char *)body, length, &w, &h);
        vita_debug_log("[Artwork] response app=%d result=%d bytes=%u png=%d source=%dx%d pool=%d",
                       id, result, (unsigned int)length, png, w, h, pool ? 1 : 0);
        if (result == 0 && !moonlight_is_cancelled(&cancel) && pool && png) {
            moonlight_artwork_fit(w, h, &width, &height);
            /* Load owns decoder setup/default heaps. DecodeImage is an internal stage,
             * not a loader for an independently opened/lazily resized Image. */
            paf::graph::Surface::LoadOption option;
            option.image_order = ImageOrder_Linear;
            /* Check room for a conservatively padded source and allocator overhead.
             * A large cover may fall back to the icon when the shared pool is busy. */
            size_t required = (size_t)((w + 63) & ~63) * ((h + 63) & ~63) * 4 + 65536;
            unsigned char *pixels = NULL;
            ImageMode mode = ImageMode_RGBA8888;
            size_t available = pool->GetFreeSize();
            vita_debug_log("[Artwork] memory app=%d free=%u required=%u", id,
                           (unsigned int)available, (unsigned int)required);
            if (available >= required) {
                phase = 1;
                paf::intrusive_ptr<paf::graph::Surface> source = paf::graph::Surface::Load(
                    pool, body, (SceInt64)length, &option);
                decoded = option.error;
                vita_debug_log("[Artwork] loaded app=%d surface=%d error=0x%08X size=%dx%d stride=%d format=0x%08X",
                    id, source.get() ? 1 : 0, (unsigned int)decoded,
                    source.get() ? source->GetWidth() : 0, source.get() ? source->GetHeight() : 0,
                    source.get() ? source->GetStride() : 0,
                    source.get() ? (unsigned int)sceGxmTextureGetFormat(source->GetRawTexture()) : 0);
                if (source.get() && decoded >= 0 && !moonlight_is_cancelled(&cancel) &&
                    source->GetWidth() == w && source->GetHeight() == h && source->GetPageSize() > 0 &&
                    (sceGxmTextureGetType(source->GetRawTexture()) == SCE_GXM_TEXTURE_LINEAR ||
                     sceGxmTextureGetType(source->GetRawTexture()) == SCE_GXM_TEXTURE_LINEAR_STRIDED)) {
                    phase = 2;
                    uint32_t format = sceGxmTextureGetFormat(source->GetRawTexture());
                    bool indexed = format == SCE_GXM_TEXTURE_FORMAT_P8_ABGR ||
                                   format == SCE_GXM_TEXTURE_FORMAT_P8_ARGB;
                    const unsigned char *palette = indexed ?
                        (const unsigned char *)sceGxmTextureGetPalette(source->GetRawTexture()) : NULL;
                    if (indexed && !palette)
                        vita_debug_log("[Artwork] missing palette app=%d format=0x%08X", id, (unsigned int)format);
                    if ((format == SCE_GXM_TEXTURE_FORMAT_A8B8G8R8 ||
                         format == SCE_GXM_TEXTURE_FORMAT_A8R8G8B8 || indexed) &&
                        (!indexed || palette)) {
                        mode = (format == SCE_GXM_TEXTURE_FORMAT_A8B8G8R8 ||
                                format == SCE_GXM_TEXTURE_FORMAT_P8_ABGR) ?
                               ImageMode_RGBA8888 : ImageMode_BGRA8888;
                        pixels = (unsigned char *)malloc((size_t)width * height * 4);
                        if (pixels) {
                            const unsigned char *data = (const unsigned char *)source->Lock();
                            int reduced = moonlight_artwork_reduce(data, source->GetPageSize(),
                                w, h, source->GetStride(), palette, pixels, width, height);
                            if (data) source->Unlock();
                            if (!reduced) { free(pixels); pixels = NULL; }
                            else phase = 3;
                        }
                    }
                }
                source.clear();
            } /* Release the full-size surface before allocating/caching the thumbnail. */
            if (pixels && !moonlight_is_cancelled(&cancel)) {
                phase = 4;
                surface = new paf::graph::Surface(pool, width, height, mode,
                    ImageOrder_Linear, 1, 1, false);
                if (surface.get() && surface->GetPagePtr(0)) {
                    decoded = surface->Copy(0, pixels, ImageOrder_Linear, width * 4, 0);
                    if (decoded < 0) surface.clear();
                } else surface.clear();
            }
            free(pixels);
        }
        free(body);
        if (moonlight_is_cancelled(&cancel)) surface.clear();
        vita_debug_log("[Artwork] complete app=%d cancelled=%d surface=%d phase=%d decode=0x%08X size=%dx%d",
                       id, moonlight_is_cancelled(&cancel) ? 1 : 0, surface.get() ? 1 : 0,
                       phase, (unsigned int)decoded,
                       surface.get() ? surface->GetWidth() : 0,
                       surface.get() ? surface->GetHeight() : 0);
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
