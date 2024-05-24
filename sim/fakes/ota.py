def update(cb, url):
    for i in range(100):
        print(i)
        cb("1.0.1", i)
    return True

def get_version():
    return "1.0.0"