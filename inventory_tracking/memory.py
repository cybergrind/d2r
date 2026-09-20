"""Small read-only memory probes; never attach or write to the target."""

import ctypes
import os

from .common import error


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
