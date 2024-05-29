Tildagon badge simulator
===

This is a little simulator that allows quicker development iteration on Python code.

It's a (C)Python application which sets up its environment so that it appears similar enough to the Badge's micropython environment.

All C-implemented functions are implemented (or maybe just stubbed out) by 'fakes' in the fakes directory. Please try to keep this in sync with the real usermodule implementation.

Of particular interest is how we provide a `ctx`-compatible API: we compile it using emscripten to a WebAssembly bundle, which we then execute using wasmer.

Setting up
---

You need Python3.10 and Pipenv installed.

Run:
```
pipenv install
```

Running
---

From the main firmware code:

```
cd sim
pipenv run python run.py
```

Known Issues
---

## ModuleNotFoundError: No module named '_contextvars'

Try using non-precompiled Python.

## No module named 'wasmer'

Try using Python 3.9 as suggested [in this issue](https://github.com/wasmerio/wasmer-python/issues/539):

```sh
pipenv shell
pip3.9 install wasmer wasmer_compiler_cranelift pygame
python3.9 run.py
```

Support
---

No support for most things.

Acknowledgements
---

Thank you to the flow3r team, whose simulator this is forked from.
