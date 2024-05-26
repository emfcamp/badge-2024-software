import asyncio
import sys
import _thread

if hasattr(sys.implementation, "_machine"):  # MicroPython
    from threadsafe import Message
else:

    class Message:
        def __init__(self):
            self._data = None
            self.finished = False

        def set(self, value):
            self._data = value
            self.finished = True

        async def wait(self):
            while not self.finished:
                await asyncio.sleep(0.1)
            return self._data

        def __iter__(self):
            yield from self.wait()
            return self._data


# Thanks to https://github.com/peterhinch/micropython-async/blob/master/v3/docs/THREADING.md
async def unblock(func, periodic_func, *args, **kwargs):
    def wrap(func, message, args, kwargs):
        nonlocal running
        print("In thread")
        try:
            print(func, args, kwargs)
            result = func(*args, **kwargs)
        except Exception as e:
            result = e
        print(result)
        running = False
        message.set(result)  # Run the blocking function.

    running = True

    async def periodic():
        while running:
            print("Periodic")
            await periodic_func()
            await asyncio.sleep(0.1)

    msg = Message()
    print("Starting thread")
    # _thread.start_new_thread(print, ("Test", ))
    _thread.start_new_thread(wrap, (func, msg, args, kwargs))
    # print(tid)
    # time.sleep(1)
    # result = func(*args, **kwargs)
    # await periodic_func()
    periodic = asyncio.create_task(periodic())
    result, _ = await asyncio.gather(msg.wait(), periodic)

    print(result)
    if isinstance(result, Exception):
        raise result
    else:
        return result
