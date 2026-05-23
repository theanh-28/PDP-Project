"""Small compatibility layer for optional Numba acceleration."""

try:
    from numba import njit as _numba_njit

    NUMBA_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without numba installed
    NUMBA_AVAILABLE = False

    def njit(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]

        def decorator(func):
            return func

        return decorator
else:

    def njit(*args, **kwargs):
        return _numba_njit(*args, **kwargs)
