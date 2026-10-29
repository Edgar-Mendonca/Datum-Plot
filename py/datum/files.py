"""Writing files safely: a temporary file next to the target, flushed to disk, then renamed over it, so a
crash or a full disk never leaves a half-written export (FAMILY §11)."""
import contextlib
import os


@contextlib.contextmanager
def atomic(path):
    """`with atomic(path) as tmp:` write to tmp; it becomes `path` only when the block finishes."""
    d, name = os.path.split(os.path.abspath(path))
    tmp = os.path.join(d, f".{name}.{os.getpid()}.tmp")
    try:
        yield tmp
        with open(tmp, "rb+") as f:
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def write_bytes(path, data):
    with atomic(path) as tmp:
        with open(tmp, "wb") as f:
            f.write(data)


def safe_text(v):
    """Text for a CSV cell that a spreadsheet will not run as a formula: a leading = + - @ gets a ' before it."""
    return "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") else v
