#ifndef TILDAGON_I2C_MANAGER_H
#define TILDAGON_I2C_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Fixed-size job table - keeps this simple and allocation-free. Currently
 * used by the IMU (accel/gyro, temperature, steps, compass) plus the
 * generic step-based jobs below; the remaining slots are available for
 * future hexpansion sensors. */
#define TILDAGON_I2C_MGR_MAX_JOBS   (10)

/* Of those, a fixed sub-range is reserved for lightweight "callback" jobs -
 * a bare function pointer plus scheduling state, no step/cache storage, so
 * they don't pay for step-job storage they never use. This is currently
 * only used internally by the AW9523B and IMU drivers (accel/gyro, temperature, steps -
 * one per continuously-polled sensor group; the compass is optional and
 * registers as a step-based job instead, see qmc6309.c). Handles below this
 * value are callback jobs, the rest are step-based - see
 * tildagon_i2c_mgr_register() vs tildagon_i2c_mgr_register_steps(). Bump
 * this (and the matching _Static_assert next to the IMU's registration
 * calls) if a new callback-based sensor group is ever added. */
#define TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS (4)
#define TILDAGON_I2C_MGR_MAX_STEP_JOBS     (TILDAGON_I2C_MGR_MAX_JOBS - TILDAGON_I2C_MGR_MAX_CALLBACK_JOBS)

/* Sentinel period meaning "do not poll this job". */
#define TILDAGON_I2C_MGR_PERIOD_OFF (UINT16_MAX)
#define TILDAGON_I2C_MGR_MAX_PERIOD_MS (UINT16_MAX - 1U)

/* Recurring jobs must not monopolise the shared I2C bus. */
#define TILDAGON_I2C_MGR_MIN_PERIOD_MS (10U)

/* Limits for generic step-based jobs (see tildagon_i2c_mgr_register_steps). */
#define TILDAGON_I2C_MGR_MAX_STEPS      (5)
#define TILDAGON_I2C_MGR_MAX_STEP_BYTES (4)
#define TILDAGON_I2C_MGR_MAX_JOB_CACHE  (32)

/* A job callback is responsible for performing its own I2C transaction(s)
 * (e.g. via tildagon_mux_i2c_transaction / tildagon_i2c_reg_read) and
 * caching the result; the manager only decides when to call it. */
typedef void (*tildagon_i2c_mgr_job_fn_t)( void );

typedef enum
{
    TILDAGON_I2C_MGR_PHASE_RUN,
    TILDAGON_I2C_MGR_PHASE_COMPLETE,
} tildagon_i2c_mgr_phase_t;

typedef void (*tildagon_i2c_mgr_phased_job_fn_t)( tildagon_i2c_mgr_phase_t phase );

typedef enum
{
    TILDAGON_I2C_MGR_STEP_READ = 0,
    TILDAGON_I2C_MGR_STEP_WRITE = 1,
    TILDAGON_I2C_MGR_STEP_CHECK = 2,
    TILDAGON_I2C_MGR_STEP_READ16 = 3,
    TILDAGON_I2C_MGR_STEP_WRITE16 = 4,
} tildagon_i2c_mgr_step_type_t;

typedef enum
{
    TILDAGON_I2C_MGR_STATUS_IDLE = 0,
    TILDAGON_I2C_MGR_STATUS_PENDING = 1,
    TILDAGON_I2C_MGR_STATUS_SUCCESS = 2,
    TILDAGON_I2C_MGR_STATUS_CHECK_ABORTED = 3,
    TILDAGON_I2C_MGR_STATUS_I2C_ERROR = 4,
} tildagon_i2c_mgr_status_t;

/* One step of a generic multi-step job (see tildagon_i2c_mgr_register_steps
 * below). Field meaning depends on `type`:
 *   READ:     a = register address (low 8 bits used), b = number of bytes to
 *             read; the bytes are appended to the job's cache after any earlier
 *             READ steps' bytes.
 *   READ16:   a = 16-bit register address, b = number of bytes to read.
 *   WRITE:    a = register address (low 8 bits used), b = number of bytes to
 *             write, data[0..b-1] = the bytes to write.
 *   WRITE16:  a = 16-bit register address, b = number of bytes to write.
 *   CHECK:    a = byte offset into the cache so far (from an earlier READ step
 *             in this same job), b = mask, data[0] = comparison value. If
 *             (cache[a] & b) == data[0], the rest of the job is skipped for
 *             this poll - the published cache and sequence number are left
 *             untouched (this is not treated as an error). */
typedef struct
{
    uint8_t type;
    uint8_t b;
    uint16_t a;
    uint8_t data[TILDAGON_I2C_MGR_MAX_STEP_BYTES];
} tildagon_i2c_mgr_step_t;

/* Starts the manager's background task. Must be called once at board init,
 * before any jobs are registered. */
extern void tildagon_i2c_mgr_init( void );

/* Registers a new job with an initial period. A recurring period must be at
 * least TILDAGON_I2C_MGR_MIN_PERIOD_MS and is due immediately after
 * registration; use TILDAGON_I2C_MGR_PERIOD_OFF to leave it idle. Due high
 * priority jobs run before due low priority jobs, but do not interrupt a
 * transaction already in progress. Returns a handle >= 0 on success, or -1
 * if the period is invalid or the job table is full. */
extern int tildagon_i2c_mgr_register( tildagon_i2c_mgr_job_fn_t callback,
                                      uint16_t period_ms, bool high_priority );

/* As above, but invokes callback first with TILDAGON_I2C_MGR_PHASE_RUN, then
 * with TILDAGON_I2C_MGR_PHASE_COMPLETE after the manager has published the
 * final status and made a one-shot job re-armable. */
extern int tildagon_i2c_mgr_register_phased( tildagon_i2c_mgr_phased_job_fn_t callback,
                                             uint16_t period_ms, bool high_priority );

/* Registers a generic multi-step job (for hexpansion sensors etc.) that the
 * manager's background task executes directly - no per-sensor C code
 * required. `steps` is copied, so the caller's array does not need to
 * outlive this call. All steps run against the same (port, i2c_addr) each
 * time the job's period elapses; if any READ/WRITE fails or a CHECK step
 * aborts the poll, the job's previously published cache and sequence number
 * are left untouched. Returns a handle >= 0 on success, or -1 if the job
 * table is full, num_steps is 0 or > TILDAGON_I2C_MGR_MAX_STEPS, or the
 * period is invalid, or the steps' total READ bytes exceed
 * TILDAGON_I2C_MGR_MAX_JOB_CACHE. Scheduling follows the same immediate
 * first execution and high-before-low rules as callback jobs. */
extern int tildagon_i2c_mgr_register_steps( uint8_t port, uint8_t i2c_addr,
                                             const tildagon_i2c_mgr_step_t *steps, uint8_t num_steps,
                                             uint16_t period_ms, bool high_priority );

/* Frees a job's slot so it can be reused by tildagon_i2c_mgr_register()/
 * tildagon_i2c_mgr_register_steps(). */
extern void tildagon_i2c_mgr_unregister( int handle );

/* Requests a new period for a job. Recurring periods below
 * TILDAGON_I2C_MGR_MIN_PERIOD_MS are rejected. By default only requests that
 * reduce the period (poll more often) are accepted; pass force=true to also
 * allow increasing it, or to set TILDAGON_I2C_MGR_PERIOD_OFF to stop polling.
 * There is no per-caller tracking - this is a simple "reduce unless forced"
 * rule shared by every caller. Returns false if the handle or period is
 * invalid; otherwise true, whether or not the period actually changed (e.g.
 * it was already running at or faster than the requested period). */
extern bool tildagon_i2c_mgr_set_period( int handle, uint16_t period_ms, bool force );

/* Returns a job's current period, or TILDAGON_I2C_MGR_PERIOD_OFF if the
 * handle is invalid. */
extern uint16_t tildagon_i2c_mgr_get_period( int handle );

/* Requests exactly one execution of an idle job. The job's period must be
 * TILDAGON_I2C_MGR_PERIOD_OFF. There are no automatic retries, and only one
 * execution may be pending. Returns false if the handle is invalid, the job
 * is recurring, or a one-shot is already pending. */
extern bool tildagon_i2c_mgr_run_once( int handle );

/* Reads a job's current status. Returns -1 if the handle is invalid, or a
 * TILDAGON_I2C_MGR_STATUS_* value for a valid callback or step-based job. */
extern int tildagon_i2c_mgr_get_status( int handle );

/* Copies a step-based job's most recently published cache into dest (dest_len
 * must be >= the job's total READ byte count) and returns the sequence
 * number that data corresponds to. Returns -1 if the handle is invalid, is
 * not a step-based job, dest_len is too small, or no poll has completed
 * successfully yet - dest is left untouched in that case. The copy and the
 * returned sequence are taken under the same lock the background task uses
 * when publishing new data, so they always correspond to each other exactly
 * (comparing sequence numbers from two separate calls would not be safe). */
extern int64_t tildagon_i2c_mgr_read_into( int handle, uint8_t *dest, size_t dest_len );

/* Called (from the manager's background task, not the registering thread)
 * once after every poll that successfully publishes new cache data - never
 * for a failed or CHECK-aborted poll. Do the minimum possible work here and
 * hand off the rest; this runs on a 4KB FreeRTOS task stack, not the caller's. */
typedef void (*tildagon_i2c_mgr_notify_fn_t)( int handle );

/* Registers (fn non-NULL) or clears (fn NULL) a step-based job's data-ready
 * notification, replacing any previous one for this handle. Returns false if
 * the handle is invalid or not a step-based job. */
extern bool tildagon_i2c_mgr_set_notify( int handle, tildagon_i2c_mgr_notify_fn_t fn);

#endif /* TILDAGON_I2C_MANAGER_H */
