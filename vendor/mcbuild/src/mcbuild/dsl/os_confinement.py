"""Fail-closed Linux syscall restrictions for untrusted blueprint execution.

After trusted DSL initialization, block all new file opens, network operations, and
process creation. Blueprints do not need file or socket I/O. This is a kernel-enforced
reduction in available syscalls, NOT a general-purpose container or VM sandbox: for
example, inherited descriptors and kernel attack surface still require scrutiny.
"""

from __future__ import annotations

import ctypes
import errno
import platform
import sys

_PR_SET_NO_NEW_PRIVS = 38
_PR_SET_SECCOMP = 22
_SECCOMP_MODE_FILTER = 2
_BPF_LOAD_ABS = 0x20
_BPF_JEQ = 0x15
_BPF_JGE = 0x35
_BPF_RET = 0x06
_SECCOMP_RET_ALLOW = 0x7FFF0000
_SECCOMP_RET_ERRNO = 0x00050000
_AUDIT_ARCH_X86_64 = 0xC000003E

# Verified architecture: Linux x86_64. Block alternate file-opening interfaces,
# network syscalls, process spawning, inspection of peer processes, and routes
# that could bypass the file-open prohibition. Unknown architectures fail closed.
_DENIED_X86_64 = frozenset(
    {
        2, 85, 257, 304, 437,  # open, creat, openat, open_by_handle_at, openat2
        41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55,
        288, 299, 307,  # networking, including socketpair and accept4
        56, 57, 58, 59, 322, 435,  # clone, fork, vfork, execve, execveat, clone3
        101, 310, 311, 438,  # ptrace, process_vm_* and pidfd_getfd
        321, 298, 425, 426, 427, 323,  # bpf, perf_event_open, io_uring*, userfaultfd
        165, 166, 155, 161, 272, 308,  # mount, umount2, pivot_root, chroot, unshare, setns
        428, 429, 430, 431, 432, 433,  # open_tree, move_mount, fsopen, fsconfig, fsmount, fspick
        76, 77, 82, 83, 84, 86, 87, 88, 90, 91, 92, 93, 94, 133,
        132, 235, 258, 259, 260, 261, 263, 264, 265, 266, 268, 280, 316,
        248, 249, 250,  # kernel keyrings
    }
)


class _SockFilter(ctypes.Structure):
    _fields_ = [
        ("code", ctypes.c_ushort),
        ("jt", ctypes.c_ubyte),
        ("jf", ctypes.c_ubyte),
        ("k", ctypes.c_uint32),
    ]


class _SockFProg(ctypes.Structure):
    _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.POINTER(_SockFilter))]


def install() -> None:
    """Restrict this process and all descendants; raise on unsupported hosts or failures.

    The restriction is irreversible and inherited. Install only inside a disposable
    blueprint child, after trusted Python package imports and JSON request decoding.
    """
    if sys.platform != "linux" or platform.machine() != "x86_64":
        raise OSError(errno.ENOSYS, "seccomp syscall restrictions are only verified on Linux x86_64")

    program = [
        _SockFilter(_BPF_LOAD_ABS, 0, 0, 4),  # seccomp_data.arch
        _SockFilter(_BPF_JEQ, 1, 0, _AUDIT_ARCH_X86_64),
        _SockFilter(_BPF_RET, 0, 0, _SECCOMP_RET_ERRNO | errno.EPERM),
        _SockFilter(_BPF_LOAD_ABS, 0, 0, 0),  # seccomp_data.nr
        _SockFilter(_BPF_JGE, 0, 1, 0x40000000),  # reject x32 ABI
        _SockFilter(_BPF_RET, 0, 0, _SECCOMP_RET_ERRNO | errno.EPERM),
    ]
    for number in sorted(_DENIED_X86_64):
        program.extend(
            (
                _SockFilter(_BPF_JEQ, 0, 1, number),
                _SockFilter(_BPF_RET, 0, 0, _SECCOMP_RET_ERRNO | errno.EPERM),
            )
        )
    program.append(_SockFilter(_BPF_RET, 0, 0, _SECCOMP_RET_ALLOW))

    filters = (_SockFilter * len(program))(*program)
    rules = _SockFProg(len(program), filters)
    libc = ctypes.CDLL(None, use_errno=True)

    if libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        code = ctypes.get_errno()
        raise OSError(code, "could not set no-new-privileges")
    if libc.prctl(_PR_SET_SECCOMP, _SECCOMP_MODE_FILTER, ctypes.byref(rules), 0, 0) != 0:
        code = ctypes.get_errno()
        raise OSError(code, "could not install seccomp filter")


def _probe(path: str) -> dict[str, bool]:
    """Harmless real-syscall probe for tests, never called by production blueprints."""
    import os
    import socket

    install()
    file_denied = False
    network_denied = False
    spawn_denied = False
    try:
        with open(path, "rb") as stream:
            stream.read(1)
    except PermissionError:
        file_denied = True
    try:
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except PermissionError:
        network_denied = True
    try:
        os.fork()
    except PermissionError:
        spawn_denied = True
    return {
        "file_denied": file_denied,
        "network_denied": network_denied,
        "spawn_denied": spawn_denied,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(_probe(sys.argv[1])), flush=True)
