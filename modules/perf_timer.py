import time


def perf_timer(func):
    def wrapper(*args, **kwargs):
        start = time.ticks_us()
        func(*args, **kwargs)
        end = time.ticks_us()
        delta = time.ticks_diff(end, start)
        print(f"{func.__name__} took {delta} us")
    return wrapper

class PerfTimer:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.start = time.ticks_us()

    def __exit__(self, exc_type, exc_value, exc_tb):
        delta = time.ticks_diff(time.ticks_us(), self.start)
        print(f"{self.name} took {delta} us")