Tildagon badge simulator
===

This is a little simulator that allows quicker development iteration on Python code.

It's a (C)Python application which sets up its environment so that it appears similar enough to the Badge's micropython environment.

All C-implemented functions are implemented (or maybe just stubbed out) by 'fakes' in the fakes directory. Please try to keep this in sync with the real usermodule implementation.

Of particular interest is how we provide a `ctx`-compatible API: we compile it using emscripten to a WebAssembly bundle, which we then execute using wasmtime.

Setting up
---

You need Python3.10 and Pipenv installed. On MacOS you will need to install a SDL related
dependencies to get pygame to work. 

Run:
```
brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf pkg-config
```
You may need to install sdl2 on Linux via your package manager. 


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

## ModuleNotFoundError: No module named 'aiorepl'

The simulator no longer requires `aiorepl` to start. If `aiorepl` is missing, the REPL task is skipped.

If you run `pipenv install aiorepl`, Pipenv may fail to lock with:

`No matching distribution found for aiorepl`

In that case, do not add it to the lockfile; run the simulator normally with:

```sh
pipenv run python run.py
```

## Dependencies

All dependencies are pinned to specific versions to ensure reproducible builds. If you encounter issues with missing dependencies, ensure you're using Python 3.10 and run:

```sh
pipenv install
```


Support
---

No support for most things.

Acknowledgements
---

Thank you to the flow3r team, whose simulator this is forked from.
