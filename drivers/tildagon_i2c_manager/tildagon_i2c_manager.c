#include "tildagon_i2c_manager.h"
#include "tildagon_i2c_mpless.h"

#include "esp_log.h"
#include "esp_timer.h"
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include <string.h>

static const char *TAG = "i2c_mgr";

typedef struct
{
    uint32_t sequence;
    tildagon_i2c_mgr_step_t steps[TILDAGON_I2C_MGR_MAX_STEPS];
    uint8_t cache[TILDAGON_I2C_MGR_MAX_JOB_CACHE];
    uint8_t port;
    uint8_t i2c_addr;
    uint8_t num_steps;
    uint8_t cache_len;
} i2c_mgr_step_job_t;

/* Scheduling state common to both job kinds below. */
typedef struct
{
    uint32_t next_due_us;
    uint16_t period_ms;
    uint8_t flags;
} i2c_mgr_job_hdr_t;

/* A callback job is just a function pointer - no cache/step storage, so it
 * gets its own (much smaller) slot type rather than sharing a union with
 * i2c_mgr_step_job_t, which would force every callback job to pay for
 * step-job storage it never uses. */
typedef union
{
    tildagon_i2c_mgr_job_fn_t callback;
    tildagon_i2c_mgr_phased_job_fn_t phased_callback;
} i2c_mgr_callback_fn_t;

typedef struct
{
    i2c_mgr_job_hdr_t hdr;
    i2c_mgr_callback_fn_t fn;
} i2c_mgr_callback_job_t;

typedef struct
{
    i2c_mgr_job_hdr_t hdr;
    i2c_mgr_step_job_t step;
} i2c_mgr_step_slot_t;


/* Job state, priority, and three-bit status share one byte. Job kind
 * (callback vs step-based) is implied by which handle range a handle falls
 * in, not a flag bit - see i2c_mgr_is_step_handle(). */
#define JOB_FLAG_IN_USE          (1U << 0)
#define JOB_FLAG_PHASED_CALLBACK (1U << 1)
#define JOB_FLAG_VALID           (1U << 2)
#define JOB_FLAG_RUN_ONCE_PENDING (1U << 3)
#define JOB_STATUS_SHIFT         (4U)
#define JOB_STATUS_MASK          (7U << JOB_STATUS_SHIFT)
#define JOB_FLAG_HIGH_PRIORITY   (1U << 7)

/* Zero-initialised: every slot starts free. Handles [0, MAX_CALLBACK_JOBS)
 * index callback_jobs; handles [MAX_CALLBACK_JOBS, MAX_JOBS) index
 * step_jobs, offset by MAX_CALLBACK_JOBS - see i2c_mgr_hdr(). */
static i2c_mgr_callback_job_t callback_jobs[TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS];
static i2c_mgr_step_slot_t step_jobs[TILDAGON_I2C_MGR_MAX_STEP_JOBS];

/* Data-ready notification per step job (callback jobs have no notify - the
 * caller supplies its own callback directly), kept separate so the MP
 * binding layer can freely store/clear these without touching job state.
 * Indexed by step-job index (handle - MAX_CALLBACK_JOBS), not by handle. */
static tildagon_i2c_mgr_notify_fn_t notify_fn[TILDAGON_I2C_MGR_MAX_STEP_JOBS];

/* Protects scheduling state and cache publication. I2C runs unlocked; an
 * executing slot is withheld from reuse until its transaction completes. */
static SemaphoreHandle_t job_mu;
static TaskHandle_t manager_task;
static int8_t running_handle = -1;
#define JOB_LOCK   xSemaphoreTake( job_mu, portMAX_DELAY )
#define JOB_UNLOCK xSemaphoreGive( job_mu )

static inline bool i2c_mgr_is_step_handle( int handle )
{
    return handle >= TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS;
}

/* Returns the scheduling header for any handle, callback or step-based. */
static inline i2c_mgr_job_hdr_t *i2c_mgr_hdr( int handle )
{
    if ( !i2c_mgr_is_step_handle( handle ) )
    {
        return &callback_jobs[handle].hdr;
    }
    return &step_jobs[handle - TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS].hdr;
}

static bool i2c_mgr_period_valid( uint16_t period_ms )
{
    return period_ms == TILDAGON_I2C_MGR_PERIOD_OFF ||
           period_ms >= TILDAGON_I2C_MGR_MIN_PERIOD_MS;
}

static inline bool i2c_mgr_job_flag( const i2c_mgr_job_hdr_t *hdr, uint8_t flag )
{
    return (hdr->flags & flag) == flag;
}

static inline void i2c_mgr_set_status( i2c_mgr_job_hdr_t *hdr, uint8_t status )
{
    hdr->flags = (hdr->flags & ~JOB_STATUS_MASK) |
                 ((status << JOB_STATUS_SHIFT) & JOB_STATUS_MASK);
}

static inline uint8_t i2c_mgr_get_job_status( const i2c_mgr_job_hdr_t *hdr )
{
    return (hdr->flags & JOB_STATUS_MASK) >> JOB_STATUS_SHIFT;
}

static inline bool i2c_mgr_time_due( uint32_t now_us, uint32_t due_us )
{
    return (int32_t)(now_us - due_us) >= 0;
}

static inline void i2c_mgr_wake_task( void )
{
    if ( manager_task != NULL )
    {
        xTaskNotifyGive( manager_task );
    }
}

static void i2c_mgr_finish_attempt( i2c_mgr_job_hdr_t *hdr, tildagon_i2c_mgr_status_t status )
{
    JOB_LOCK;
    i2c_mgr_set_status( hdr, status );
    JOB_UNLOCK;
}

/* Runs every step of a generic job in order. On success (every step
 * completes and no CHECK step aborts), publishes the new cache and bumps
 * the sequence number; otherwise leaves the previously published data
 * untouched. */
static void i2c_mgr_run_step_job( int handle, i2c_mgr_step_slot_t *slot )
{
    i2c_mgr_step_job_t *step_job = &slot->step;
    uint8_t local_cache[TILDAGON_I2C_MGR_MAX_JOB_CACHE];
    uint8_t offset = 0;

    for ( int s = 0; s < step_job->num_steps; s++ )
    {
        const tildagon_i2c_mgr_step_t *step = &step_job->steps[s];

        switch ( (tildagon_i2c_mgr_step_type_t)step->type )
        {
            case TILDAGON_I2C_MGR_STEP_READ:
            {
                esp_err_t err = tildagon_i2c_reg_read( step_job->port, step_job->i2c_addr, (uint8_t)step->a,
                                                        &local_cache[offset], step->b );
                if ( err != ESP_OK )
                {
                    /*
                    ESP_LOGI( TAG, "job %d step %d READ reg 0x%02X len %d failed: 0x%x",
                              handle, s, step->a, step->b, err );
                    */
                    i2c_mgr_finish_attempt( &slot->hdr, TILDAGON_I2C_MGR_STATUS_I2C_ERROR );
                    return;
                }
                offset += step->b;
                break;
            }
            case TILDAGON_I2C_MGR_STEP_READ16:
            {
                esp_err_t err = tildagon_i2c_reg16_read( step_job->port, step_job->i2c_addr, step->a,
                                                         &local_cache[offset], step->b );
                if ( err != ESP_OK )
                {
                    i2c_mgr_finish_attempt( &slot->hdr, TILDAGON_I2C_MGR_STATUS_I2C_ERROR );
                    return;
                }
                offset += step->b;
                break;
            }
            case TILDAGON_I2C_MGR_STEP_WRITE:
            {
                esp_err_t err = tildagon_i2c_reg_write( step_job->port, step_job->i2c_addr, (uint8_t)step->a,
                                                         step->data, step->b );
                if ( err != ESP_OK )
                {
                    /*
                    ESP_LOGI( TAG, "job %d step %d WRITE reg 0x%02X len %d failed: 0x%x",
                              handle, s, step->a, step->b, err );
                    */
                    i2c_mgr_finish_attempt( &slot->hdr, TILDAGON_I2C_MGR_STATUS_I2C_ERROR );
                    return;
                }
                break;
            }
            case TILDAGON_I2C_MGR_STEP_WRITE16:
            {
                esp_err_t err = tildagon_i2c_reg16_write( step_job->port, step_job->i2c_addr, step->a,
                                                          step->data, step->b );
                if ( err != ESP_OK )
                {
                    i2c_mgr_finish_attempt( &slot->hdr, TILDAGON_I2C_MGR_STATUS_I2C_ERROR );
                    return;
                }
                break;
            }
            case TILDAGON_I2C_MGR_STEP_CHECK:
            {
                uint8_t val = local_cache[step->a];
                if ( (val & step->b) == step->data[0] )
                {
                    /*
                    ESP_LOGI( TAG, "job %d step %d CHECK not ready (byte=0x%02X mask=0x%02X val=0x%02X) - skipping poll",
                              handle, s, val, step->b, step->data[0] );
                    */
                    i2c_mgr_finish_attempt( &slot->hdr, TILDAGON_I2C_MGR_STATUS_CHECK_ABORTED );
                    return;
                }
                break;
            }
        }
    }

    int step_idx = handle - TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS;
    JOB_LOCK;
    memcpy( step_job->cache, local_cache, offset );
    step_job->cache_len = offset;
    step_job->sequence++;
    slot->hdr.flags |= JOB_FLAG_VALID;
    i2c_mgr_set_status( &slot->hdr, TILDAGON_I2C_MGR_STATUS_SUCCESS );
    tildagon_i2c_mgr_notify_fn_t fn = notify_fn[step_idx];
    JOB_UNLOCK;

    if ( fn != NULL )
    {
        fn( handle );
    }

    /*
    ESP_LOGI( TAG, "job %d poll ok, seq=%u, %d bytes", handle,
              (unsigned)step_job->sequence, offset );
    */
}

static inline void i2c_mgr_run_job( int handle )
{
    if ( !i2c_mgr_is_step_handle( handle ) )
    {
        JOB_LOCK;
        i2c_mgr_set_status( &callback_jobs[handle].hdr, TILDAGON_I2C_MGR_STATUS_PENDING );
        bool phased = i2c_mgr_job_flag( &callback_jobs[handle].hdr, JOB_FLAG_PHASED_CALLBACK );
        JOB_UNLOCK;

        if ( phased )
        {
            callback_jobs[handle].fn.phased_callback( TILDAGON_I2C_MGR_PHASE_RUN );
        }
        else
        {
            callback_jobs[handle].fn.callback();
        }
        i2c_mgr_finish_attempt( &callback_jobs[handle].hdr, TILDAGON_I2C_MGR_STATUS_SUCCESS );
    }
    else
    {
        i2c_mgr_run_step_job( handle, &step_jobs[handle - TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS] );
    }
}

static TickType_t i2c_mgr_next_delay( void )
{
    uint32_t now_us = (uint32_t)esp_timer_get_time();
    uint32_t shortest_us = UINT32_MAX;
    bool have_deadline = false;

    JOB_LOCK;
    for ( int i = 0; i < TILDAGON_I2C_MGR_MAX_JOBS; i++ )
    {
        i2c_mgr_job_hdr_t *hdr = i2c_mgr_hdr( i );
        if ( !i2c_mgr_job_flag( hdr, JOB_FLAG_IN_USE ) )
        {
            continue;
        }
        if ( i2c_mgr_job_flag( hdr, JOB_FLAG_RUN_ONCE_PENDING ) ||
             (hdr->period_ms != TILDAGON_I2C_MGR_PERIOD_OFF &&
              i2c_mgr_time_due( now_us, hdr->next_due_us )) )
        {
            shortest_us = 0;
            have_deadline = true;
            break;
        }
        if ( hdr->period_ms != TILDAGON_I2C_MGR_PERIOD_OFF )
        {
            uint32_t remaining_us = hdr->next_due_us - now_us;
            if ( !have_deadline || remaining_us < shortest_us )
            {
                shortest_us = remaining_us;
                have_deadline = true;
            }
        }
    }
    JOB_UNLOCK;

    if ( !have_deadline )
    {
        return portMAX_DELAY;
    }
    if ( shortest_us == 0 )
    {
        return 0;
    }

    uint32_t delay_ms = (shortest_us + 999U) / 1000U;
    TickType_t delay_ticks = pdMS_TO_TICKS( delay_ms );
    return delay_ticks == 0 ? 1 : delay_ticks;
}

static void i2c_mgr_task( void* arg )
{
    ESP_LOGI( TAG, "task started" );

    while (1)
    {
        for ( int priority = 1; priority >= 0; priority-- )
        {
            for ( int i = 0; i < TILDAGON_I2C_MGR_MAX_JOBS; i++ )
            {
                bool run_job = false;
                bool run_once = false;
                uint32_t now_us = (uint32_t)esp_timer_get_time();

                JOB_LOCK;
                i2c_mgr_job_hdr_t *hdr = i2c_mgr_hdr( i );
                bool high_priority = i2c_mgr_job_flag( hdr, JOB_FLAG_HIGH_PRIORITY );
                if ( i2c_mgr_job_flag( hdr, JOB_FLAG_IN_USE ) &&
                     high_priority == (priority != 0) )
                {
                    run_once = i2c_mgr_job_flag( hdr, JOB_FLAG_RUN_ONCE_PENDING );
                    bool recurring_due = hdr->period_ms != TILDAGON_I2C_MGR_PERIOD_OFF &&
                                         i2c_mgr_time_due( now_us, hdr->next_due_us );
                    if ( run_once || recurring_due )
                    {
                        if ( recurring_due )
                        {
                            uint32_t period_us = (uint32_t)hdr->period_ms * 1000U;
                            uint32_t late_us = now_us - hdr->next_due_us;
                            hdr->next_due_us += ((late_us / period_us) + 1U) * period_us;
                        }
                        running_handle = i;
                        run_job = true;
                    }
                }
                JOB_UNLOCK;

                if ( run_job )
                {
                    i2c_mgr_run_job( i );
                    bool phased_callback = false;
                    JOB_LOCK;
                    if ( run_once )
                    {
                        i2c_mgr_hdr( i )->flags &= ~JOB_FLAG_RUN_ONCE_PENDING;
                    }
                    phased_callback = !i2c_mgr_is_step_handle( i ) &&
                                      i2c_mgr_job_flag( i2c_mgr_hdr( i ), JOB_FLAG_PHASED_CALLBACK );
                    JOB_UNLOCK;

                    if ( phased_callback )
                    {
                        callback_jobs[i].fn.phased_callback( TILDAGON_I2C_MGR_PHASE_COMPLETE );
                    }

                    JOB_LOCK;
                    running_handle = -1;
                    JOB_UNLOCK;
                }
            }
        }

        ulTaskNotifyTake( pdTRUE, i2c_mgr_next_delay() );
    }
}

void tildagon_i2c_mgr_init( void )
{
    /*
    ESP_LOGI( TAG, "init: callback jobs %u bytes x %u slots, step jobs %u bytes x %u slots",
              (unsigned)sizeof(i2c_mgr_callback_job_t), (unsigned)TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS,
              (unsigned)sizeof(i2c_mgr_step_slot_t), (unsigned)TILDAGON_I2C_MGR_MAX_STEP_JOBS );
    */
    job_mu = xSemaphoreCreateMutex();
    xTaskCreate( i2c_mgr_task, "i2c_mgr", 2048, NULL, tskIDLE_PRIORITY + 4,
                 &manager_task );
}

static int i2c_mgr_register_callback( i2c_mgr_callback_fn_t callback, uint16_t period_ms,
                                      bool high_priority, bool phased )
{
    if ( (!phased && callback.callback == NULL) ||
         (phased && callback.phased_callback == NULL) ||
         !i2c_mgr_period_valid( period_ms ) )
    {
        ESP_LOGW( TAG, "register: invalid callback or period %ums", (unsigned)period_ms );
        return -1;
    }

    int handle = -1;
    JOB_LOCK;
    for ( int i = 0; i < TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS; i++ )
    {
        if ( !i2c_mgr_job_flag( &callback_jobs[i].hdr, JOB_FLAG_IN_USE ) && i != running_handle )
        {
            if ( phased )
            {
                callback_jobs[i].fn.phased_callback = callback.phased_callback;
            }
            else
            {
                callback_jobs[i].fn.callback = callback.callback;
            }
            callback_jobs[i].hdr.period_ms = period_ms;
            callback_jobs[i].hdr.next_due_us = (uint32_t)esp_timer_get_time();
            callback_jobs[i].hdr.flags = JOB_FLAG_IN_USE |
                            (high_priority ? JOB_FLAG_HIGH_PRIORITY : 0) |
                            (phased ? JOB_FLAG_PHASED_CALLBACK : 0);
            handle = i;
            break;
        }
    }
    JOB_UNLOCK;
    if ( handle >= 0 )
    {
        /*
        ESP_LOGI( TAG, "job %d reg: cb, period=%ums pri=%s", handle,
                  (unsigned)period_ms, high_priority ? "high" : "low" );
        */
        i2c_mgr_wake_task();
        return handle;
    }
    ESP_LOGW( TAG, "register: callback job table full" );
    return -1;
}

int tildagon_i2c_mgr_register( tildagon_i2c_mgr_job_fn_t callback, uint16_t period_ms,
                               bool high_priority )
{
    i2c_mgr_callback_fn_t callback_fn = { .callback = callback };
    return i2c_mgr_register_callback( callback_fn, period_ms, high_priority, false );
}

int tildagon_i2c_mgr_register_phased( tildagon_i2c_mgr_phased_job_fn_t callback,
                                      uint16_t period_ms, bool high_priority )
{
    i2c_mgr_callback_fn_t callback_fn = { .phased_callback = callback };
    return i2c_mgr_register_callback( callback_fn, period_ms, high_priority, true );
}

int tildagon_i2c_mgr_register_steps( uint8_t port, uint8_t i2c_addr,
                                      const tildagon_i2c_mgr_step_t *steps, uint8_t num_steps,
                                      uint16_t period_ms, bool high_priority )
{
    if ( port > TILDAGON_MAX_I2C_PORT || i2c_addr > 0x7f )
    {
        ESP_LOGW( TAG, "register_steps: invalid port %u or address 0x%02X",
                  port, i2c_addr );
        return -1;
    }
    if ( !i2c_mgr_period_valid( period_ms ) )
    {
        ESP_LOGW( TAG, "register_steps: invalid period %ums", (unsigned)period_ms );
        return -1;
    }
    if ( num_steps == 0 || num_steps > TILDAGON_I2C_MGR_MAX_STEPS )
    {
        ESP_LOGW( TAG, "register_steps: invalid num_steps %d", num_steps );
        return -1;
    }

    uint16_t cache_len = 0;
    for ( int s = 0; s < num_steps; s++ )
    {
        switch ( (tildagon_i2c_mgr_step_type_t)steps[s].type )
        {
            case TILDAGON_I2C_MGR_STEP_READ:
            case TILDAGON_I2C_MGR_STEP_READ16:
                cache_len += steps[s].b;
                break;
            case TILDAGON_I2C_MGR_STEP_WRITE:
            case TILDAGON_I2C_MGR_STEP_WRITE16:
                if ( steps[s].b > TILDAGON_I2C_MGR_MAX_STEP_BYTES )
                {
                    ESP_LOGW( TAG, "register_steps: invalid WRITE length %u", steps[s].b );
                    return -1;
                }
                break;
            case TILDAGON_I2C_MGR_STEP_CHECK:
                if ( steps[s].a >= cache_len )
                {
                    ESP_LOGW( TAG, "register_steps: CHECK offset %u outside cache", steps[s].a );
                    return -1;
                }
                break;
            default:
                ESP_LOGW( TAG, "register_steps: invalid step type %u", steps[s].type );
                return -1;
        }
    }
    if ( cache_len > TILDAGON_I2C_MGR_MAX_JOB_CACHE )
    {
        ESP_LOGW( TAG, "register_steps: %d cache bytes exceeds max %d", cache_len, TILDAGON_I2C_MGR_MAX_JOB_CACHE );
        return -1;
    }

    int handle = -1;
    JOB_LOCK;
    for ( int i = 0; i < TILDAGON_I2C_MGR_MAX_STEP_JOBS; i++ )
    {
        int candidate = TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS + i;
        if ( !i2c_mgr_job_flag( &step_jobs[i].hdr, JOB_FLAG_IN_USE ) && candidate != running_handle )
        {
            i2c_mgr_step_job_t *step_job = &step_jobs[i].step;
            step_job->port = port;
            step_job->i2c_addr = i2c_addr;
            step_job->num_steps = num_steps;
            memcpy( step_job->steps, steps, sizeof(tildagon_i2c_mgr_step_t) * num_steps );
            step_job->cache_len = 0;
            step_job->sequence = 0;
            step_jobs[i].hdr.period_ms = period_ms;
            step_jobs[i].hdr.next_due_us = (uint32_t)esp_timer_get_time();
            step_jobs[i].hdr.flags = JOB_FLAG_IN_USE |
                            (high_priority ? JOB_FLAG_HIGH_PRIORITY : 0);
            i2c_mgr_set_status( &step_jobs[i].hdr, TILDAGON_I2C_MGR_STATUS_IDLE );
            notify_fn[i] = NULL;
            handle = candidate;
            break;
        }
    }
    JOB_UNLOCK;
    if ( handle >= 0 )
    {
        /*
        ESP_LOGI( TAG, "job %d reg: port=%d addr=0x%02X steps=%d cache=%d period=%ums",
                  handle, port, i2c_addr, num_steps, cache_len, (unsigned)period_ms );
        */
        i2c_mgr_wake_task();
        return handle;
    }
    ESP_LOGW( TAG, "register_steps: job table full" );
    return -1;
}

void tildagon_i2c_mgr_unregister( int handle )
{
    if ( handle >= 0 && handle < TILDAGON_I2C_MGR_MAX_JOBS )
    {
        /*
        ESP_LOGI( TAG, "job %d unregistered", handle );
        */
        JOB_LOCK;
        i2c_mgr_hdr( handle )->flags = 0;
        if ( i2c_mgr_is_step_handle( handle ) )
        {
            int idx = handle - TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS;
            notify_fn[idx] = NULL;
        }
        JOB_UNLOCK;
        i2c_mgr_wake_task();
    }
}

bool tildagon_i2c_mgr_set_period( int handle, uint16_t period_ms, bool force )
{
    if ( !i2c_mgr_period_valid( period_ms ) || handle < 0 ||
         handle >= TILDAGON_I2C_MGR_MAX_JOBS )
    {
        return false;
    }

    bool ok = false;
    bool changed = false;
    JOB_LOCK;
    i2c_mgr_job_hdr_t *hdr = i2c_mgr_hdr( handle );
    if ( i2c_mgr_job_flag( hdr, JOB_FLAG_IN_USE ) )
    {
        ok = true;
        if ( (force || period_ms < hdr->period_ms) &&
             period_ms != hdr->period_ms )
        {
            /*
            ESP_LOGI( TAG, "job %d period %ums -> %ums", handle, (unsigned)hdr->period_ms, (unsigned)period_ms );
            */
            hdr->period_ms = period_ms;
            hdr->next_due_us = (uint32_t)esp_timer_get_time();
            changed = true;
        }
    }
    JOB_UNLOCK;
    /* Otherwise leave it alone - already running at least as fast as
     * requested, so the caller's requirement is still met. */

    if ( changed )
    {
        i2c_mgr_wake_task();
    }
    return ok;
}

uint16_t tildagon_i2c_mgr_get_period( int handle )
{
    if ( handle < 0 || handle >= TILDAGON_I2C_MGR_MAX_JOBS )
    {
        return TILDAGON_I2C_MGR_PERIOD_OFF;
    }
    uint16_t period_ms = TILDAGON_I2C_MGR_PERIOD_OFF;
    JOB_LOCK;
    i2c_mgr_job_hdr_t *hdr = i2c_mgr_hdr( handle );
    if ( i2c_mgr_job_flag( hdr, JOB_FLAG_IN_USE ) )
    {
        period_ms = hdr->period_ms;
    }
    JOB_UNLOCK;
    return period_ms;
}

bool tildagon_i2c_mgr_run_once( int handle )
{
    if ( handle < 0 || handle >= TILDAGON_I2C_MGR_MAX_JOBS )
    {
        return false;
    }

    bool armed = false;
    JOB_LOCK;
    i2c_mgr_job_hdr_t *hdr = i2c_mgr_hdr( handle );
    if ( i2c_mgr_job_flag( hdr, JOB_FLAG_IN_USE ) &&
         hdr->period_ms == TILDAGON_I2C_MGR_PERIOD_OFF &&
         !i2c_mgr_job_flag( hdr, JOB_FLAG_RUN_ONCE_PENDING ) )
    {
        hdr->flags |= JOB_FLAG_RUN_ONCE_PENDING;
        i2c_mgr_set_status( hdr, TILDAGON_I2C_MGR_STATUS_PENDING );
        armed = true;
    }
    JOB_UNLOCK;

    if ( armed )
    {
        /*
        ESP_LOGI( TAG, "job %d one-shot armed", handle );
        */
        i2c_mgr_wake_task();
    }
    else
    {
        ESP_LOGW( TAG, "job %d one-shot failed to arm", handle );
    }
    return armed;
}

int tildagon_i2c_mgr_get_status( int handle )
{
    if ( handle < 0 || handle >= TILDAGON_I2C_MGR_MAX_JOBS )
    {
        return -1;
    }

    int status = -1;
    JOB_LOCK;
    i2c_mgr_job_hdr_t *hdr = i2c_mgr_hdr( handle );
    if ( i2c_mgr_job_flag( hdr, JOB_FLAG_IN_USE ) )
    {
        status = i2c_mgr_get_job_status( hdr );
    }
    JOB_UNLOCK;
    return status;
}

bool tildagon_i2c_mgr_set_notify( int handle, tildagon_i2c_mgr_notify_fn_t fn)
{
    if ( handle < 0 || handle >= TILDAGON_I2C_MGR_MAX_JOBS || !i2c_mgr_is_step_handle( handle ) )
    {
        return false;
    }

    bool ok = false;
    JOB_LOCK;
    if ( i2c_mgr_job_flag( i2c_mgr_hdr( handle ), JOB_FLAG_IN_USE ) )
    {
        int idx = handle - TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS;
        notify_fn[idx] = fn;
        ok = true;
    }
    JOB_UNLOCK;
    return ok;
}

int64_t tildagon_i2c_mgr_read_into( int handle, uint8_t *dest, size_t dest_len )
{
    if ( handle < 0 || handle >= TILDAGON_I2C_MGR_MAX_JOBS || !i2c_mgr_is_step_handle( handle ) ||
         !i2c_mgr_job_flag( i2c_mgr_hdr( handle ), JOB_FLAG_IN_USE ) )
    {
        return -1;
    }

    i2c_mgr_step_slot_t *slot = &step_jobs[handle - TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS];
    i2c_mgr_step_job_t *step_job = &slot->step;
    int64_t seq = -1;

    JOB_LOCK;
    if ( i2c_mgr_job_flag( &slot->hdr, JOB_FLAG_VALID ) && step_job->cache_len <= dest_len )
    {
        memcpy( dest, step_job->cache, step_job->cache_len );
        seq = (int64_t)step_job->sequence;
    }
    JOB_UNLOCK;

    return seq;
}
