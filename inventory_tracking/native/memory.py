"""Small read-only memory probes; never attach or write to the target."""

import ctypes
import errno
import os

from inventory_tracking.common import error


class IOVec(ctypes.Structure):
    _fields_ = [('iov_base', ctypes.c_void_p), ('iov_len', ctypes.c_size_t)]


def vm_read(pid, address, size):
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        fn = libc.process_vm_readv
    except AttributeError:
        return {'error': 'process_vm_readv unavailable in libc'}
    fn.argtypes = [
        ctypes.c_int,
        ctypes.POINTER(IOVec),
        ctypes.c_ulong,
        ctypes.POINTER(IOVec),
        ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    fn.restype = ctypes.c_ssize_t
    buffer = ctypes.create_string_buffer(size)
    local = IOVec(ctypes.cast(buffer, ctypes.c_void_p), size)
    remote = IOVec(address, size)
    count = fn(pid, ctypes.byref(local), 1, ctypes.byref(remote), 1, 0)
    if count < 0:
        number = ctypes.get_errno()
        return error(OSError(number, os.strerror(number)))
    return {'bytes_read': count, 'requested': size, 'ok': count == size}


IOV_MAX = 1024  # iovecs per process_vm_readv call (Linux UIO_MAXIOV)
REFUSED = frozenset((errno.EPERM, errno.EACCES, errno.ENOSYS))  # the kernel will not do it for this process


def vm_call():
    """libc's process_vm_readv, bound once for many reads (`vm_read_spans`), or None where it cannot be had."""
    try:
        call = ctypes.CDLL(None, use_errno=True).process_vm_readv
    except OSError, AttributeError:
        return None
    call.restype = ctypes.c_ssize_t
    pointer = ctypes.POINTER(IOVec)
    call.argtypes = (ctypes.c_int, pointer, ctypes.c_ulong, pointer, ctypes.c_ulong, ctypes.c_ulong)
    return call


def vm_read_spans(call, pid: int, spans) -> list[bytes | None] | None:
    """Each span (address, size) of process `pid`, None where unreadable, in as few calls as the kernel's partial
    reads allow (a read stops at the first span it cannot read: that one is None, the rest are asked again). None
    when the kernel refuses the call altogether."""
    out: list[bytes | None] = [None] * len(spans)
    start = 0
    while start < len(spans):
        chunk = spans[start : start + IOV_MAX]
        total = sum(size for _, size in chunk)
        buffer = ctypes.create_string_buffer(total)
        local = IOVec(ctypes.addressof(buffer), total)
        remote = (IOVec * len(chunk))(*(IOVec(address, size) for address, size in chunk))
        got = call(pid, ctypes.byref(local), 1, remote, len(chunk), 0)
        if got < 0:
            code = ctypes.get_errno()
            if code in REFUSED:
                return None
            if code == errno.ESRCH:
                return out  # the game is gone
            got = 0  # EFAULT: the first span is unreadable
        raw, offset, done = buffer.raw, 0, 0
        for _, size in chunk:
            if offset + size > got:
                break
            out[start + done] = raw[offset : offset + size]
            offset, done = offset + size, done + 1
        start += done + (done < len(chunk))  # past the span the read stopped at
    return out


def proc_read(pid, address, size):
    try:
        fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
        try:
            count = len(os.pread(fd, size, address))
        finally:
            os.close(fd)
        return {'bytes_read': count, 'requested': size, 'ok': count == size}
    except OSError as exc:
        return error(exc)
