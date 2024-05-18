import asyncio
import sys

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
        print("In thread")
        try:
            print(func, args, kwargs)
            result = func(*args, **kwargs)
        except Exception as e:
            result = e
        print(result)
        message.set(result)  # Run the blocking function.

    # msg = Message()
    print("Starting thread")
    # _thread.start_new_thread(print, ("Test", ))
    # tid = _thread.start_new_thread(wrap, (func, msg, args, kwargs))
    # print(tid)
    # time.sleep(1)
    result = func(*args, **kwargs)
    print("async unblock")
    await periodic_func()
    # result = await msg.wait()
    print(result)
    if isinstance(result, Exception):
        raise result
    else:
        return result
