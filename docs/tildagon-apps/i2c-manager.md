# Using the I2C manager

The badge has one I2C bus behind a multiplexer, and it is shared by everything:
the IMU, the touch/button controller, the power management chips, every
hexpansion, and every app that talks to a sensor. The I2C manager is a
background service that owns that bus and polls devices on your behalf, so
apps ask for *data at a rate* instead of performing transactions by hand.

## Why use the manager instead of direct I2C calls?

Talking to a sensor directly from an app is easy to write and surprisingly hard
to get right. A typical app ends up doing a blocking register read inside
`update()`, once per frame, forever. That approach has a number of problems
that the manager solves for you:

**Your app stops blocking on the bus.** The ESP32-S3 performs I2C transactions
in hardware, but when a direct read/write happens on the MicroPython thread
(e.g. by calling `i2c.readfrom_mem()` or similar) it blocks until the transaction
completes. An I2C transaction takes a few hundred microseconds to several
milliseconds, and a sensor that clock-stretches or NAKs can take much longer.
Every one of those microseconds is stolen not only from your frame time but all
other micropython tasks as well. Whereas the manager performs the transaction on
its own background FreeRTOS task, allowing micropython to continue while the
hardware takes care of the i2C transfer and your app only ever copies bytes out
of a cache.

**Polling rate stops depending on frame rate.** If you read a sensor in
`update()`, your sample rate is whatever your frame rate happens to be — which
changes when another app is running, when the garbage collector runs, or when
you draw something expensive. The manager polls from a timer, so a job asked to
run every 50 ms runs every 50 ms regardless of what the UI is doing.

**Reads are consistent and never torn.** Each successful poll publishes its
whole cache atomically along with a sequence number. You either see all of the
old sample or all of the new one, never half of each.

**Failures degrade gracefully.** If a poll fails, or a "data ready" check says
the sensor has nothing new, the previously published data and sequence number
are left untouched. Your app keeps reading the last good sample instead of
seeing an exception or a block of zeroes.

**No allocation on the polling path.** Job execution happens entirely in C with
fixed-size buffers. Nothing is allocated on the MicroPython heap to poll a
sensor, so polling continues normally during a GC pause and does not contribute
to heap fragmentation.

!!! tip "Rule of thumb"
    If you want a value *repeatedly*, use the manager. Direct I2C calls are
    still the right tool for one-off configuration during setup, or for
    exploratory work such as scanning a bus.

## Quick start: using an existing sensor

The IMU sensors are already registered with the manager, so the simplest thing
you can do is ask for the compass at a rate that suits your app:

```python
import imu

imu.set_period(imu.COMPASS, 100)   # ask for a compass sample every 100 ms

x, y, z = imu.mag_read()           # returns the most recently cached sample
```

`mag_read()` returns whatever the background task cached most recently, so it is
cheap enough to call every frame.

## Existing sensors

The IMU exposes four independently scheduled types of sensor data:

| Name | Read with | Default rate when first used |
| --- | --- | --- |
| `imu.ACCEL_GYRO` | `imu.acc_read()`, `imu.gyro_read()` | 40 ms |
| `imu.COMPASS` | `imu.mag_read()` | 40 ms |
| `imu.TEMPERATURE` | `imu.temperature_read()` | 1000 ms |
| `imu.STEPS` | `imu.step_counter_read()` | 1000 ms |

Every sensor starts with polling switched **off**. A sensor starts being polled either
when you set a period explicitly, or automatically at the default rate above the first
time anything reads it. That auto-start keeps older apps working unchanged.

### `imu.set_period(sensor_type, period_ms, force=False)`

Requests a polling rate for a type of sensor data. `period_ms` must be `None` (meaning "off")
or an integer between 10 and 65534 milliseconds; anything else raises
`ValueError`.

Returns `True` if the group exists and the request was accepted, and `False` if
the type of sensor data is not registered — for example, the compass on a badge with no 2026
frontboard fitted. Note that `True` does **not** mean the rate changed; see
below.

### `imu.get_period(sensor_type)`

Returns the current period in milliseconds, or `None` if the type of sensor data is not
currently being polled. This is the call you use to record state before you
change it.

```python
previous = imu.get_period(imu.COMPASS)   # e.g. None, or 40, or 250
```

## The `force` flag

This is the most important thing to understand about the manager, because it is
what makes sharing safe.

By default, `set_period()` **only accepts requests that make polling faster**.
A request for a slower rate, or for `None` (off), is silently ignored unless you
pass `force=True`.

```python
imu.set_period(imu.COMPASS, 50)                 # 200ms -> 50ms: applied
imu.set_period(imu.COMPASS, 500)                # 50ms -> 500ms: ignored
imu.set_period(imu.COMPASS, 500, force=True)    # 50ms -> 500ms: applied
imu.set_period(imu.COMPASS, None, force=True)   # stops polling entirely
```

The reason is that there is **no per-caller tracking**. The manager stores a
single period per job, not a list of every requester's wishes. Under that
design, "fastest wins" is the only rule that can be applied safely without
bookkeeping:

- If another app needs the compass every 50 ms and you ask for 200 ms, honouring
  your request would silently break the other app. Ignoring it costs you
  nothing, because a 50 ms rate already satisfies your 200 ms requirement.
- If you ask for 20 ms and something else wanted 200 ms, speeding the job up
  still satisfies both.

So an unforced call means *"I need data at least this often"*, and the manager
guarantees it without ever degrading anyone else. A forced call means *"set it
to exactly this, whatever anyone else asked for"* — which is precisely what you
need when you are turning a sensor **down** or **off**, and exactly why slowing
down and switching off both require `force=True`.

!!! warning "`True` does not mean 'changed'"
    `set_period()` returns whether the handle was valid, not whether the period
    moved. A request that was ignored because the job is already faster still
    returns `True`. If you need to know the rate that is actually in effect,
    call `get_period()` afterwards.

Because a forced call overrides other users, treat it as something you do
deliberately — normally only to your own jobs, or when tidying up on exit, which
brings us to the next section.

## Being a good citizen on exit

Your app is not necessarily the only user of a sensor. Other apps run in the
background on the badge, and the firmware itself uses the IMU. If your app turns
the compass up to 20 ms and then forces it off when the user quits, you may have
just broken another app that was relying on it.

There is no single correct answer, so **ask the user**. The recommended pattern
is to record the previous state on entry, and on exit offer the choice between
leaving your rate in place or restoring what was there before:

```python
COMPASS_UPDATE_PERIOD_MS = 100

def start(self):
    # Remember what the rest of the system had configured before we interfere.
    self.previous_period = imu.get_period(imu.COMPASS)
    if self.previous_period is None or self.previous_period != COMPASS_UPDATE_PERIOD_MS:
        if imu.set_period(imu.COMPASS, COMPASS_UPDATE_PERIOD_MS):
            self.changed = True


def exit(self, restore):
    if restore and self.changed:
        # force=True is required: we are (probably) slowing it down or
        # switching it off, and previous_period may be None.
        imu.set_period(imu.COMPASS, self.previous_period, force=True)
```

Note that `get_period()` returns `None` when a group is off, and `set_period()`
accepts `None` to mean off, so a saved value can be handed straight back without
any special-casing.

The `spaceagon-test` app does exactly this: pressing cancel offers *"Confirm:
Keep 100ms / Cancel: Restore"*, so a user who is running something else that
wants compass data can leave the faster rate running, while a user who cares
about power consumption or app performance can put it back.

!!! note "Why not just always restore?"
    Because restoring is not automatically the polite option. If another app
    started using the sensor while yours was in the foreground, restoring the
    *old* value forces that app's rate away too. Leaving your setting alone is
    often the safer default, which is why offering the choice is better than
    hard-coding either behaviour.

## Registering a new job for your own sensor

For a sensor the firmware does not already know about — typically on a
hexpansion — you can describe the polling sequence to the manager and let it run
it for you. No C code is required.

```python
import i2c_mgr

PORT = 1        # hexpansion slot 1
ADDR = 0x29     # the sensor's 7-bit address

job = i2c_mgr.add_job(
    PORT,
    ADDR,
    (
        (i2c_mgr.READ, 0x14, 6),    # read 6 bytes starting at register 0x14
    ),
    period_ms=100,
)
```

`add_job()` returns a `Job` object, or `None` if the job table is full. Always
check for `None`.

Reading the cached result copies it into a buffer you own:

```python
buf = bytearray(6)

sequence = job.read_into(buf)
if sequence is not None:
    distance_mm = (buf[0] << 8) | buf[1]
```

`read_into()` returns the **sequence number** of the data it copied, or `None`
if the buffer is too small or no poll has succeeded yet. The sequence number
increments once per successful poll, so it is how you tell fresh data from a
repeat of the sample you already processed:

```python
def update(self, delta):
    sequence = self.job.read_into(self.buf)
    if sequence is not None and sequence != self.last_sequence:
        self.last_sequence = sequence
        self.process(self.buf)
```

The copy and the returned sequence number are taken together under the same lock
the background task uses to publish, so they always correspond to each other.
(Calling `read_into()` and then separately asking for a sequence number would
not be safe, which is why there is no separate call to do that.)

### Job steps

A job is a short list of steps, executed in order against the same port and
address every time the job's period elapses. There are five kinds:

| Step | Meaning |
| --- | --- |
| `(i2c_mgr.READ, reg, length)` | Read `length` bytes from register `reg`, appending them to the job's cache after any earlier `READ` steps. |
| `(i2c_mgr.WRITE, reg, length, data)` | Write `length` bytes from `data` to register `reg`. `data` must be a bytes-like object of exactly `length` bytes. |
| `(i2c_mgr.READ16, reg, length)` | As `READ`, but send `reg` as a 16-bit address, most-significant byte first. |
| `(i2c_mgr.WRITE16, reg, length, data)` | As `WRITE`, but send `reg` as a 16-bit address, most-significant byte first. |
| `(i2c_mgr.CHECK, offset, mask, value)` | Abort this poll if `(cache[offset] & mask) == value`. |

`WRITE` and `WRITE16` steps are how you re-trigger a sensor that needs a "start
measurement" command each cycle. `CHECK` steps are how you avoid publishing
garbage from a sensor that has not finished converting yet.

The `16` in `READ16` and `WRITE16` describes the register **address**, not the
data. Use these steps for devices such as the SCD4X that send a two-byte command
or register address. `length` still gives the number of data bytes to read or
write, and those bytes are cached unchanged:

```python
job = i2c_mgr.add_job(
    PORT,
    ADDR,
    (
        (i2c_mgr.READ16, 0xE4B8, 3),
        (i2c_mgr.CHECK, 1, 0xFF, 0x00),
        (i2c_mgr.READ16, 0xEC05, 9),
    ),
    period_ms=1000,
)
```

The existing `READ` and `WRITE` steps accept register addresses from `0x00` to
`0xFF`; `READ16` and `WRITE16` accept addresses from `0x0000` to `0xFFFF`.

### A typical single-shot sensor

Many sensors need the same three-part cycle every time: check whether the
previous conversion finished, read the result, then kick off the next
conversion. That is expressible as one job:

```python
job = i2c_mgr.add_job(
    PORT,
    ADDR,
    (
        (i2c_mgr.READ,  0x00, 1),              # 0: status byte -> cache[0]
        (i2c_mgr.CHECK, 0,    0x01, 0x00),     # abort if 'data ready' bit is clear
        (i2c_mgr.READ,  0x02, 2),              # 1: result -> cache[1..2]
        (i2c_mgr.WRITE, 0x01, 1, b"\x01"),     # start the next conversion
    ),
    period_ms=50,
)
```

Read that `CHECK` as "the ready bit is bit 0; if it reads back as 0 the data is
not ready, so give up on this poll". When a `CHECK` aborts:

- the remaining steps are skipped,
- the previously published cache and sequence number are left untouched,
- the status becomes `STATUS_CHECK_ABORTED`.

An aborted poll is *not* an error — it simply means there was nothing new. Your
app carries on seeing the last good sample, and the job tries again next period.
Doing this check inside the job rather than in Python means an unready sensor
costs a single byte on the bus and never wakes your app at all.

!!! note "Cache offsets refer to `READ` bytes only"
    The cache is the concatenation of every `READ` and `READ16` step's bytes, in
    order. `WRITE`, `WRITE16`, and `CHECK` steps contribute nothing to it. In
    the example above the status byte is at offset 0 and the result at offsets
    1 and 2, so the buffer you pass to `read_into()` needs to be 3 bytes.

### One-shot jobs

A job registered with no period (or with its period set to `None`) is idle, and
can be run on demand instead. This suits a sensor you only need occasionally —
you get the manager's bus arbitration without the cost of continuous polling.

```python
job = i2c_mgr.add_job(PORT, ADDR, steps)      # period_ms defaults to None
job.run_once()
```

`run_once()` returns `True` if the one-shot was armed, or `False` if the
handle is invalid, the job is recurring, or a one-shot is already pending.
Arming sets the status to `STATUS_PENDING` immediately, so polling
`get_status()` until it stops reporting `STATUS_PENDING` tells you your
request has been serviced:

```python
status = job.get_status()

if status == i2c_mgr.STATUS_SUCCESS:
    job.read_into(buf)
elif status == i2c_mgr.STATUS_I2C_ERROR:
    ...
```

There are no automatic retries: if a one-shot fails, arm another one.

### Getting notified of new data

Polling `get_status()` or `read_into()`'s sequence number every frame works,
but if you would rather react only when there is something to react to, a job
can call a handler for you instead:

```python
def on_data(job):
    job.read_into(buf)
    ...

job.irq(on_data)
```

`irq(handler)` calls `handler(job)` once after every poll that *successfully*
publishes new data — never for a failed or `CHECK`-aborted one, since those
leave the previous sample untouched anyway. Pass `None` (the default) to stop
being notified; this also happens automatically on `job.unregister()`. The
same mechanism works for one-shot jobs too, as an alternative to polling
`get_status()` for completion.

The handler runs like any other scheduled callback (the same mechanism behind
`Pin.irq()`), so it can run any time after the poll that triggered it, and the
usual scheduling rules apply: keep it short, and don't assume it can't be
interrupted by another callback.

!!! note "Bursts of data are coalesced, not queued"
    If several polls complete before your handler gets to run, you still only
    get one call, not one per poll. The job's cache only ever holds the most
    recent sample, so an intermediate one you never got notified about was
    already lost the moment the next poll overwrote it — there was nothing to
    gain by queuing up a notification for it. Always re-read the latest data
    in your handler rather than assuming one call means exactly one new
    sample.

### Priority

`add_job(..., high_priority=True)` marks a job as high priority. When several
jobs are due at the same moment, high priority ones are dispatched first. This
does **not** interrupt a transaction already in progress, and it does not make a
job run more often. Reserve it for genuinely latency-sensitive data such as user
input; ordinary sensors should stay at the default.

### Releasing a job

The job table is a small fixed-size array shared by the whole badge, so free
your slot when your app shuts down:

```python
job.unregister()
```

After this the `Job` object is inert and its slot can be reused.

## API reference

### Module `i2c_mgr`

| Name | Description |
| --- | --- |
| `add_job(port, addr, steps, period_ms=None, high_priority=False)` | Registers a step-based job. Returns a `Job`, or `None` if the table is full. |
| `READ`, `WRITE`, `READ16`, `WRITE16`, `CHECK` | Step type constants. `READ16` and `WRITE16` use 16-bit register addresses. |
| `OFF` | Sentinel meaning "not polled". Equivalent to passing `None`. |
| `MIN_PERIOD_MS` | Minimum recurring period (10 ms). |
| `STATUS_IDLE`, `STATUS_PENDING`, `STATUS_SUCCESS`, `STATUS_CHECK_ABORTED`, `STATUS_I2C_ERROR` | Values returned by `Job.get_status()`. |

`port` is the multiplexer port: `0` is the frontboard/top bus, `1`–`6` are
hexpansion slots 1–6, and `7` is the internal system bus. `addr` is a 7-bit
address.

### Class `Job`

`Job` objects are only produced by `add_job()` and cannot be constructed
directly.

| Method | Description |
| --- | --- |
| `read_into(buf)` | Copies the latest published cache into `buf` and returns its sequence number, or `None` if `buf` is too small or no poll has succeeded yet. |
| `set_period(period_ms, force=False)` | Requests a new period. Returns `True` if the handle is valid. |
| `get_period()` | Returns the current period in ms, or `None` if the job is not being polled. |
| `run_once()` | Arms a single execution of an idle job. Returns `True` if armed. |
| `get_status()` | Returns the job's current status, or `None` if the handle is invalid. |
| `irq(handler)` | Calls `handler(job)` after every poll that publishes new data. `handler=None` disables it. |
| `unregister()` | Frees the job's slot. |

`Job.set_period()` follows exactly the same reduce-unless-forced rule as
[`imu.set_period()`](#the-force-flag).

### Module `imu`

| Name | Description |
| --- | --- |
| `set_period(group, period_ms, force=False)` | Requests a polling rate for a sensor group. |
| `get_period(group)` | Returns the group's period in ms, or `None` if it is off. |
| `ACCEL_GYRO`, `TEMPERATURE`, `STEPS`, `COMPASS` | Sensor group constants. |
| `OFF` | Sentinel meaning "not polled". |

## Limits

The manager is deliberately allocation-free, so everything is a fixed size:

| Limit | Value |
| --- | --- |
| Total jobs on the badge | 10 (shared with the firmware's own jobs) |
| Steps per job | 5 |
| Bytes per `WRITE` or `WRITE16` step | 4 |
| Total `READ` and `READ16` bytes per job (cache size) | 32 |
| Period range | 10–65534 ms, or `None` for off |

`add_job()` raises `ValueError` for a bad step count, a malformed step tuple, a
`WRITE` or `WRITE16` whose data length does not match its declared length, a
register address outside the range for its step type, a port outside 0–7, or a
device address that is not 7-bit. It returns `None` — rather than raising — when
the job table is full, so check the result.

## Writing apps that also run on older firmware

The manager and the period-control functions are not present in older BadgeOS
releases, and the simulator's `imu` module does not implement them either. If
your app needs to run in both places, detect the capability rather than assuming
it, and fall back to plain reads:

```python
import imu

try:
    imu.set_period(imu.COMPASS, 100, force=True)
    have_manager = True
except AttributeError:
    have_manager = False       # older firmware: mag_read() still works

x, y, z = imu.mag_read()
```

The same applies to the `i2c_mgr` module itself, which will fail to import
entirely on older firmware:

```python
try:
    import i2c_mgr
except ImportError:
    i2c_mgr = None
```

If you only offer the "keep or restore polling rate" choice when
`have_manager` is true, the app behaves sensibly everywhere: on new firmware the
user gets the choice, and on old firmware exit is a single button press because
there is no background polling to leave behind.
