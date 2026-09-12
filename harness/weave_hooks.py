"""Weave tracing hooks — active when WANDB_API_KEY is set, no-ops otherwise.

Call init_weave() once at process start (pipeline.main / loop.main). Tracing
is opt-out: TIEOUT_WEAVE=0 disables even when a key is present. WEAVE_PROJECT
env sets the Weave project ("entity/project" or bare "project"), default
"tieout". All wrappers check enabled() at call time so import order doesn't
matter.
"""

import functools
import os

_ENABLED = None
_OPS: dict = {}


def init_weave() -> bool:
    global _ENABLED
    if _ENABLED is not None:
        return _ENABLED
    if os.environ.get("TIEOUT_WEAVE", "1").lower() in (
        "0",
        "false",
        "off",
    ) or not os.environ.get("WANDB_API_KEY"):
        _ENABLED = False
    else:
        try:
            import weave

            weave.init(os.environ.get("WEAVE_PROJECT", "tieout"))
            _ENABLED = True
        except Exception:  # noqa: BLE001 — tracing must never break the pipeline
            _ENABLED = False
    return _ENABLED


def enabled() -> bool:
    return bool(_ENABLED)


def _wop(fn, name):
    key = (id(fn), name)
    if key not in _OPS:
        import weave

        _OPS[key] = weave.op(name=name or getattr(fn, "__name__", "op"))(fn)
    return _OPS[key]


def traceable(name=None):
    """Decorate an async fn: logged as a Weave op when tracing is on."""

    def deco(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            if enabled():
                return await _wop(fn, name)(*args, **kwargs)
            return await fn(*args, **kwargs)

        return wrapper

    return deco


def traceable_call(fn, name=None):
    """Wrap an async callable (adapter `complete`) the same way, keeping attrs."""

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        if enabled():
            return await _wop(fn, name)(*args, **kwargs)
        return await fn(*args, **kwargs)

    for attr in ("model_name", "temperature"):
        if hasattr(fn, attr):
            setattr(wrapper, attr, getattr(fn, attr))
    return wrapper
