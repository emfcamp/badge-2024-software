import requests


def mkmock(fn):
    def mocked(*args, **kwargs):
        kwargs["stream"] = True
        if kwargs.get("headers"):
            if not kwargs["headers"].get("Accept-Encoding"):
                kwargs["headers"]["Accept-Encoding"] = "identity"
        else:
            kwargs["headers"] = {"Accept-Encoding": "identity"}
        return fn(*args, **kwargs)

    return mocked


request = mkmock(requests.request)
head = mkmock(requests.head)
get = mkmock(requests.get)
post = mkmock(requests.post)
put = mkmock(requests.put)
patch = mkmock(requests.patch)
delete = mkmock(requests.delete)
Response = requests.Response
