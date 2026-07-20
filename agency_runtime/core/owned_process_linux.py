"""Dedicated Linux subreaper protocol for strongly owned subprocess trees."""

from __future__ import annotations

import base64
import ctypes
import json
import os
import select
import subprocess
import sys
import time
from collections.abc import Sequence
from contextlib import suppress
from typing import Any

from agency_runtime.core.process_argv import (
    PreparedProcessArgv,
    freeze_process_argv,
    prepare_process_argv,
)

READY_SECONDS = 5.0
STATUS_LIMIT = 4096
STATUS_ENV = "_AGENCY_OWNED_PROCESS_STATUS_FD"
PARENT_ENV = "_AGENCY_OWNED_PROCESS_PARENT_PID"
GO_ENV = "_AGENCY_OWNED_PROCESS_GO_FD"


class DescriptorOwner:
    """Own one descriptor through alias-safe, idempotent handoffs.

    A raw descriptor cannot safely exist in both a local and a process
    attribute: an asynchronous exception can run cleanup for both aliases,
    and the second close may target a newly recycled descriptor.  Every alias
    to this object instead observes the descriptor being claimed before the
    interruptible native close.
    """

    __slots__ = ("_index", "_storage")

    def __init__(self, descriptor: int) -> None:
        if not isinstance(descriptor, int) or descriptor < 0:
            raise ValueError("owned descriptor must be a non-negative integer")
        self._index = 0
        self._storage = (ctypes.c_int * 1)(descriptor)

    @classmethod
    def from_storage(cls, storage: Any, index: int) -> DescriptorOwner:
        """Own one slot populated by a native descriptor-producing call."""

        owner = cls.__new__(cls)
        owner._index = index
        owner._storage = storage
        return owner

    def fileno(self) -> int:
        descriptor = int(self._storage[self._index])
        if descriptor < 0:
            raise OSError("owned descriptor is closed")
        return descriptor

    def close(self) -> None:
        descriptor = int(self._storage[self._index])
        if descriptor < 0:
            return
        self._storage[self._index] = -1
        os.close(descriptor)

    def __del__(self) -> None:
        with suppress(BaseException):
            self.close()


def descriptor_number(value: object) -> int | None:
    """Return an open descriptor from either current or legacy process state."""

    if isinstance(value, DescriptorOwner):
        return value.fileno()
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _clear_process_descriptor(
    process: subprocess.Popen[Any],
    attribute: str,
    value: object,
) -> None:
    if getattr(process, attribute, None) is value:
        setattr(process, attribute, None)


def _close_process_descriptor(
    process: subprocess.Popen[Any],
    attribute: str,
) -> None:
    value = getattr(process, attribute, None)
    if isinstance(value, DescriptorOwner):
        try:
            value.close()
        finally:
            _clear_process_descriptor(process, attribute, value)
        return
    if isinstance(value, int) and value >= 0:
        try:
            os.close(value)
        finally:
            _clear_process_descriptor(process, attribute, value)


def _write_process_descriptor(
    process: subprocess.Popen[Any],
    attribute: str,
    payload: bytes,
) -> None:
    value = getattr(process, attribute, None)
    descriptor = descriptor_number(value)
    if descriptor is None:
        raise OSError("Linux process supervisor GO gate is unavailable")
    try:
        if os.write(descriptor, payload) != len(payload):
            raise OSError("Linux process supervisor GO receipt was partial")
    except BaseException as exc:
        try:
            _close_process_descriptor(process, attribute)
        except BaseException as close_error:
            add_note = getattr(exc, "add_note", None)
            if callable(add_note):  # pragma: no branch - Python 3.10 compatibility
                add_note(f"descriptor close failed: {close_error}")
        raise
    else:
        _close_process_descriptor(process, attribute)


def release_go(process: subprocess.Popen[Any]) -> None:
    """Commit an exact GO receipt and irrevocably close its descriptor."""

    _write_process_descriptor(process, "_agency_supervisor_go_fd", b"GO\n")


def cancel_go(process: subprocess.Popen[Any]) -> None:
    """Best-effort cancellation of a target that has not crossed the GO gate."""

    value = getattr(process, "_agency_supervisor_go_fd", None)
    descriptor = descriptor_number(value)
    if descriptor is None:
        return
    try:
        with suppress(OSError):
            os.write(descriptor, b"CANCEL\n")
    finally:
        with suppress(OSError):
            _close_process_descriptor(process, "_agency_supervisor_go_fd")


def close_go(process: subprocess.Popen[Any]) -> None:
    """Idempotently close the GO descriptor without relying on cancellation."""

    _close_process_descriptor(process, "_agency_supervisor_go_fd")


SUPERVISOR_SOURCE = r"""
import base64
import ctypes
import errno
import json
import os
import select
import signal
import sys
import time

STATUS_FD = int(os.environ.pop("_AGENCY_OWNED_PROCESS_STATUS_FD"))
EXPECTED_LAUNCHER_PID = int(os.environ.pop("_AGENCY_OWNED_PROCESS_PARENT_PID"))
GO_FD = int(os.environ.pop("_AGENCY_OWNED_PROCESS_GO_FD"))
TARGET_PAYLOAD = sys.argv[1:]
TARGET = ()
PR_SET_PDEATHSIG = 1
PR_SET_DUMPABLE = 4
PR_SET_SECCOMP = 22
PR_SET_CHILD_SUBREAPER = 36
PR_SET_NO_NEW_PRIVS = 38
SECCOMP_MODE_FILTER = 2
SECCOMP_RET_KILL_PROCESS = 0x80000000
SECCOMP_RET_ERRNO = 0x00050000
SECCOMP_RET_ALLOW = 0x7FFF0000
BPF_LD_W_ABS = 0x20
BPF_JMP_JEQ_K = 0x15
BPF_JMP_JGE_K = 0x35
BPF_RET_K = 0x06
SECCOMP_NR_OFFSET = 0
SECCOMP_ARCH_OFFSET = 4
SECCOMP_ARGUMENT_OFFSET = 16
X32_SYSCALL_BIT = 0x40000000
GRACE_SECONDS = 0.5
POLICY_SECONDS = 2.0
POLICY_LIMIT = 256
GO_SECONDS = 5.0
CHILDREN_LIMIT = 1024 * 1024
TARGET_LIMIT = 1024 * 1024
TARGET_ITEMS_LIMIT = 4096
stop_signal = 0
root_pid = 0
root_status = None
launcher_pid = os.getppid()
supervisor_pid = os.getpid()
children_fd = -1
policy_read_fd = -1
policy_write_fd = -1


class SockFilter(ctypes.Structure):
    _fields_ = [
        ("code", ctypes.c_ushort),
        ("jt", ctypes.c_ubyte),
        ("jf", ctypes.c_ubyte),
        ("k", ctypes.c_uint),
    ]


class SockFprog(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ushort),
        ("instructions", ctypes.POINTER(SockFilter)),
    ]


PROCESS_CONTROL_SYSCALLS = {
    "x86_64": (
        0xC000003E,
        {
            "kill": 62,
            "tkill": 200,
            "tgkill": 234,
            "rt_sigqueueinfo": 129,
            "rt_tgsigqueueinfo": 297,
            "pidfd_open": 434,
            "prlimit64": 302,
            "sched_setparam": 142,
            "sched_setscheduler": 144,
            "sched_setaffinity": 203,
            "sched_setattr": 314,
            "setpriority": 141,
            "ioprio_set": 251,
        },
        True,
    ),
    "amd64": (
        0xC000003E,
        {
            "kill": 62,
            "tkill": 200,
            "tgkill": 234,
            "rt_sigqueueinfo": 129,
            "rt_tgsigqueueinfo": 297,
            "pidfd_open": 434,
            "prlimit64": 302,
            "sched_setparam": 142,
            "sched_setscheduler": 144,
            "sched_setaffinity": 203,
            "sched_setattr": 314,
            "setpriority": 141,
            "ioprio_set": 251,
        },
        True,
    ),
    "aarch64": (
        0xC00000B7,
        {
            "kill": 129,
            "tkill": 130,
            "tgkill": 131,
            "rt_sigqueueinfo": 138,
            "rt_tgsigqueueinfo": 240,
            "pidfd_open": 434,
            "prlimit64": 261,
            "sched_setparam": 118,
            "sched_setscheduler": 119,
            "sched_setaffinity": 122,
            "sched_setattr": 274,
            "setpriority": 140,
            "ioprio_set": 30,
        },
        False,
    ),
    "arm64": (
        0xC00000B7,
        {
            "kill": 129,
            "tkill": 130,
            "tgkill": 131,
            "rt_sigqueueinfo": 138,
            "rt_tgsigqueueinfo": 240,
            "pidfd_open": 434,
            "prlimit64": 261,
            "sched_setparam": 118,
            "sched_setscheduler": 119,
            "sched_setaffinity": 122,
            "sched_setattr": 274,
            "setpriority": 140,
            "ioprio_set": 30,
        },
        False,
    ),
    "riscv64": (
        0xC00000F3,
        {
            "kill": 129,
            "tkill": 130,
            "tgkill": 131,
            "rt_sigqueueinfo": 138,
            "rt_tgsigqueueinfo": 240,
            "pidfd_open": 434,
            "prlimit64": 261,
            "sched_setparam": 118,
            "sched_setscheduler": 119,
            "sched_setaffinity": 122,
            "sched_setattr": 274,
            "setpriority": 140,
            "ioprio_set": 30,
        },
        False,
    ),
}


def emit(message):
    payload = (message + "\n").encode("ascii", "strict")
    try:
        os.write(STATUS_FD, payload)
    except OSError:
        return False
    return True


def fail(message, code=125):
    emit("ERROR:" + message)
    try:
        os.close(STATUS_FD)
    except OSError:
        pass
    os._exit(code)


def decode_target():
    if len(TARGET_PAYLOAD) != 1 or len(TARGET_PAYLOAD[0]) > TARGET_LIMIT * 2:
        fail("invalid-target-envelope")
    try:
        encoded = TARGET_PAYLOAD[0].encode("ascii", "strict")
        payload = base64.b64decode(encoded, altchars=b"-_", validate=True)
        value = json.loads(payload)
    except (UnicodeError, ValueError):
        fail("invalid-target-envelope")
    if (
        len(payload) > TARGET_LIMIT
        or not isinstance(value, list)
        or not 1 <= len(value) <= TARGET_ITEMS_LIMIT
        or any(
            not isinstance(item, str) or not item or "\x00" in item
            for item in value
        )
    ):
        fail("invalid-target-envelope")
    return tuple(value)


TARGET = decode_target()


def handle(signum, _frame):
    global stop_signal
    stop_signal = signum


def bpf_statement(code, value):
    return SockFilter(code, 0, 0, value & 0xFFFFFFFF)


def bpf_jump(code, value, jump_true, jump_false):
    return SockFilter(code, jump_true, jump_false, value & 0xFFFFFFFF)


def guarded_process_handler(argument_index, denied_values):
    handler = [
        bpf_statement(
            BPF_LD_W_ABS,
            SECCOMP_ARGUMENT_OFFSET + argument_index * 8,
        )
    ]
    for value in dict.fromkeys(denied_values):
        handler.extend(
            (
                bpf_jump(BPF_JMP_JEQ_K, value, 0, 1),
                bpf_statement(BPF_RET_K, SECCOMP_RET_ERRNO | errno.EPERM),
            )
        )
    handler.append(bpf_statement(BPF_RET_K, SECCOMP_RET_ALLOW))
    return handler


def guarded_selector_handler(
    *,
    selector_index,
    process_index,
    process_selector,
    group_selector,
    user_selector,
):
    # User-wide resource mutations necessarily include the same-UID supervisor,
    # regardless of the selector's ``who`` value.  Process and process-group
    # mutations are denied only when they name the supervisor (which is also
    # the leader of its private process group).
    handler = [
        bpf_statement(
            BPF_LD_W_ABS,
            SECCOMP_ARGUMENT_OFFSET + selector_index * 8,
        ),
        bpf_jump(BPF_JMP_JEQ_K, user_selector, 0, 1),
        bpf_statement(BPF_RET_K, SECCOMP_RET_ERRNO | errno.EPERM),
    ]
    for selector in (process_selector, group_selector):
        process_handler = [
            bpf_statement(
                BPF_LD_W_ABS,
                SECCOMP_ARGUMENT_OFFSET + process_index * 8,
            ),
            bpf_jump(BPF_JMP_JEQ_K, supervisor_pid, 0, 1),
            bpf_statement(BPF_RET_K, SECCOMP_RET_ERRNO | errno.EPERM),
        ]
        handler.append(
            bpf_jump(
                BPF_JMP_JEQ_K,
                selector,
                0,
                len(process_handler),
            )
        )
        handler.extend(process_handler)
    handler.append(bpf_statement(BPF_RET_K, SECCOMP_RET_ALLOW))
    return handler


def append_syscall_rule(program, syscall_number, handler):
    if len(handler) > 255:
        raise OSError(errno.E2BIG, "process-control guard rule is too large")
    program.append(
        bpf_jump(
            BPF_JMP_JEQ_K,
            syscall_number,
            0,
            len(handler),
        )
    )
    program.extend(handler)


def process_control_guard_program():
    machine = os.uname().machine.casefold()
    configuration = PROCESS_CONTROL_SYSCALLS.get(machine)
    if configuration is None:
        raise OSError(errno.EOPNOTSUPP, "unsupported process-control architecture")
    audit_arch, syscalls, rejects_x32 = configuration
    deny = bpf_statement(BPF_RET_K, SECCOMP_RET_ERRNO | errno.EPERM)
    program = [
        bpf_statement(BPF_LD_W_ABS, SECCOMP_ARCH_OFFSET),
        bpf_jump(BPF_JMP_JEQ_K, audit_arch, 1, 0),
        bpf_statement(BPF_RET_K, SECCOMP_RET_KILL_PROCESS),
        bpf_statement(BPF_LD_W_ABS, SECCOMP_NR_OFFSET),
    ]
    if rejects_x32:
        program.extend(
            (
                bpf_jump(BPF_JMP_JGE_K, X32_SYSCALL_BIT, 0, 1),
                deny,
            )
        )

    supervisor_group = (-supervisor_pid) & 0xFFFFFFFF
    broadcast = (-1) & 0xFFFFFFFF
    process_denials = (supervisor_pid, supervisor_group, broadcast)
    append_syscall_rule(
        program,
        syscalls["kill"],
        guarded_process_handler(0, process_denials),
    )
    append_syscall_rule(
        program,
        syscalls["rt_sigqueueinfo"],
        guarded_process_handler(0, process_denials),
    )
    append_syscall_rule(
        program,
        syscalls["tkill"],
        guarded_process_handler(0, (supervisor_pid,)),
    )
    append_syscall_rule(
        program,
        syscalls["tgkill"],
        guarded_process_handler(0, (supervisor_pid,)),
    )
    append_syscall_rule(
        program,
        syscalls["rt_tgsigqueueinfo"],
        guarded_process_handler(0, (supervisor_pid,)),
    )
    append_syscall_rule(
        program,
        syscalls["pidfd_open"],
        guarded_process_handler(0, (supervisor_pid,)),
    )
    for syscall_name in (
        "prlimit64",
        "sched_setparam",
        "sched_setscheduler",
        "sched_setaffinity",
        "sched_setattr",
    ):
        append_syscall_rule(
            program,
            syscalls[syscall_name],
            guarded_process_handler(0, (supervisor_pid,)),
        )
    append_syscall_rule(
        program,
        syscalls["setpriority"],
        guarded_selector_handler(
            selector_index=0,
            process_index=1,
            process_selector=0,
            group_selector=1,
            user_selector=2,
        ),
    )
    append_syscall_rule(
        program,
        syscalls["ioprio_set"],
        guarded_selector_handler(
            selector_index=0,
            process_index=1,
            process_selector=1,
            group_selector=2,
            user_selector=3,
        ),
    )
    program.append(bpf_statement(BPF_RET_K, SECCOMP_RET_ALLOW))
    return program


def install_process_control_guard():
    instructions = process_control_guard_program()
    array_type = SockFilter * len(instructions)
    array = array_type(*instructions)
    descriptor = SockFprog(
        len(instructions),
        ctypes.cast(array, ctypes.POINTER(SockFilter)),
    )
    if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, "no-new-privileges setup failed")
    if libc.prctl(
        PR_SET_SECCOMP,
        SECCOMP_MODE_FILTER,
        ctypes.addressof(descriptor),
        0,
        0,
    ) != 0:
        error = ctypes.get_errno()
        raise OSError(error, "seccomp process-control guard setup failed")


def child_policy_fail(descriptor, message):
    payload = ("ERROR:" + message + "\n").encode("ascii", "replace")[:POLICY_LIMIT]
    try:
        os.write(descriptor, payload)
    except OSError:
        pass
    os._exit(125)


def read_child_policy():
    deadline = time.monotonic() + POLICY_SECONDS
    payload = bytearray()
    while b"\n" not in payload:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return "policy-timeout"
        readable, _, _ = select.select((policy_read_fd,), (), (), remaining)
        if not readable:
            return "policy-timeout"
        try:
            chunk = os.read(policy_read_fd, POLICY_LIMIT - len(payload))
        except OSError as exc:
            return "policy-read-{}".format(exc.errno)
        if not chunk:
            return "policy-child-exited"
        payload.extend(chunk)
        if len(payload) >= POLICY_LIMIT:
            return "policy-receipt-limit"
    first, remainder = bytes(payload).split(b"\n", 1)
    if remainder:
        return "policy-receipt-trailing"
    try:
        message = first.decode("ascii", "strict")
    except UnicodeDecodeError:
        return "policy-receipt-invalid"
    return message


def read_go():
    deadline = time.monotonic() + GO_SECONDS
    payload = bytearray()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return "go-timeout"
        readable, _, _ = select.select((GO_FD,), (), (), remaining)
        if not readable:
            return "go-timeout"
        try:
            chunk = os.read(GO_FD, 8 - len(payload))
        except OSError as exc:
            return "go-read-{}".format(exc.errno)
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > len(b"CANCEL\n"):
            return "go-invalid"
    if bytes(payload) != b"GO\n":
        return "go-cancelled" if bytes(payload) == b"CANCEL\n" else "go-invalid"
    return None


def read_policy_completion():
    deadline = time.monotonic() + POLICY_SECONDS
    payload = bytearray()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return "policy-terminal-timeout"
        readable, _, _ = select.select((policy_read_fd,), (), (), remaining)
        if not readable:
            return "policy-terminal-timeout"
        try:
            chunk = os.read(policy_read_fd, POLICY_LIMIT - len(payload))
        except OSError as exc:
            return "policy-terminal-read-{}".format(exc.errno)
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) >= POLICY_LIMIT:
            return "policy-terminal-limit"
    if not payload:
        return None
    if not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        return "policy-terminal-invalid"
    try:
        message = payload[:-1].decode("ascii", "strict")
    except UnicodeDecodeError:
        return "policy-terminal-invalid"
    if not message.startswith("ERROR:") or len(message) <= len("ERROR:"):
        return "policy-terminal-invalid"
    return message


def direct_child_pids():
    if children_fd < 0:
        fail("proc-children-unavailable")
    try:
        os.lseek(children_fd, 0, os.SEEK_SET)
        payload = bytearray()
        while len(payload) <= CHILDREN_LIMIT:
            chunk = os.read(
                children_fd,
                min(64 * 1024, CHILDREN_LIMIT + 1 - len(payload)),
            )
            if not chunk:
                break
            payload.extend(chunk)
    except OSError as exc:
        fail("proc-children-{}".format(exc.errno))
    if len(payload) > CHILDREN_LIMIT:
        fail("proc-children-limit")
    try:
        return [int(value) for value in payload.split()]
    except ValueError:
        fail("invalid-proc-children")


def signal_pid(pid, signum):
    try:
        descriptor = os.pidfd_open(pid, 0)
    except ProcessLookupError:
        return
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return
        fail("pidfd-open-{}".format(exc.errno))
    try:
        signal.pidfd_send_signal(descriptor, signum, None, 0)
    except ProcessLookupError:
        pass
    except OSError as exc:
        if exc.errno != errno.ESRCH:
            fail("pidfd-signal-{}".format(exc.errno))
    finally:
        os.close(descriptor)


def reap():
    global root_status
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return False
        if pid == 0:
            return True
        if pid == root_pid:
            root_status = status


def terminate_descendants():
    deadline = time.monotonic() + 0.25
    while True:
        # Read only the subreaper's direct children from the descriptor opened
        # before any target code ran.  Killing one generation reparents the
        # next generation here, so repeated passes drain setsid/double-fork
        # trees without reopening attacker-raceable /proc paths.
        pids = direct_child_pids()
        for pid in pids:
            signal_pid(pid, signal.SIGTERM)
        if not reap():
            return
        if time.monotonic() >= deadline:
            break
        time.sleep(0.01)
    deadline = time.monotonic() + 2.0
    while True:
        pids = direct_child_pids()
        for pid in pids:
            signal_pid(pid, signal.SIGKILL)
        if not reap():
            return
        if time.monotonic() >= deadline:
            fail("descendants-not-reaped")
        time.sleep(0.01)


def fail_after_fork(message):
    terminate_descendants()
    fail(message)


if not TARGET:
    fail("missing-target")
if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
    fail("pidfd-unavailable")
if not os.path.isdir("/proc/self/task"):
    fail("procfs-unavailable")
if launcher_pid != EXPECTED_LAUNCHER_PID:
    fail("launcher-parent-changed")
try:
    os.set_inheritable(GO_FD, False)
except OSError as exc:
    fail("go-descriptor-{}".format(exc.errno))

libc = ctypes.CDLL(None, use_errno=True)
libc.prctl.argtypes = [
    ctypes.c_int,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_ulong,
]
libc.prctl.restype = ctypes.c_int
signal.signal(signal.SIGTERM, handle)
signal.signal(signal.SIGINT, handle)
signal.signal(signal.SIGHUP, handle)
if libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
    fail("subreaper-{}".format(ctypes.get_errno()))
if libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0) != 0:
    fail("parent-death-signal-{}".format(ctypes.get_errno()))
if os.getppid() != launcher_pid:
    fail("launcher-exited")
if libc.prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) != 0:
    fail("non-dumpable-{}".format(ctypes.get_errno()))
try:
    children_fd = os.open(
        "/proc/self/task/{}/children".format(supervisor_pid),
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0),
    )
    os.set_inheritable(children_fd, False)
    direct_child_pids()
except OSError as exc:
    fail("proc-children-open-{}".format(exc.errno))
try:
    probe = os.pidfd_open(os.getpid(), 0)
    os.close(probe)
except OSError as exc:
    fail("pidfd-probe-{}".format(exc.errno))
if stop_signal:
    fail("launcher-exited")
try:
    policy_read_fd, policy_write_fd = os.pipe()
    os.set_inheritable(policy_read_fd, False)
    os.set_inheritable(policy_write_fd, False)
except OSError as exc:
    fail("policy-pipe-{}".format(exc.errno))

try:
    root_pid = os.fork()
except OSError as exc:
    fail("fork-{}".format(exc.errno))

if root_pid == 0:
    try:
        os.close(policy_read_fd)
    except OSError as exc:
        child_policy_fail(policy_write_fd, "policy-read-close-{}".format(exc.errno))
    if os.getppid() != supervisor_pid:
        child_policy_fail(policy_write_fd, "supervisor-parent-changed")
    try:
        os.close(children_fd)
    except OSError as exc:
        child_policy_fail(policy_write_fd, "children-close-{}".format(exc.errno))
    try:
        os.close(STATUS_FD)
    except OSError:
        pass
    restored_signals = (
        signal.SIGTERM,
        signal.SIGINT,
        signal.SIGHUP,
        signal.SIGPIPE,
        getattr(signal, "SIGXFSZ", getattr(signal, "SIGXFZ", None)),
    )
    for signum in restored_signals:
        if signum is not None:
            signal.signal(signum, signal.SIG_DFL)
    try:
        os.setsid()
    except OSError as exc:
        child_policy_fail(policy_write_fd, "setsid-{}".format(exc.errno))
    if libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL, 0, 0, 0) != 0:
        child_policy_fail(
            policy_write_fd,
            "parent-death-signal-{}".format(ctypes.get_errno()),
        )
    if os.getppid() != supervisor_pid:
        child_policy_fail(policy_write_fd, "supervisor-exited")
    try:
        install_process_control_guard()
    except OSError as exc:
        child_policy_fail(policy_write_fd, "process-control-guard-{}".format(exc.errno))
    try:
        if os.write(policy_write_fd, b"READY\n") != len(b"READY\n"):
            child_policy_fail(policy_write_fd, "policy-receipt-partial")
    except OSError as exc:
        child_policy_fail(policy_write_fd, "policy-write-{}".format(exc.errno))
    go_error = read_go()
    try:
        os.close(GO_FD)
    except OSError as exc:
        child_policy_fail(policy_write_fd, "go-close-{}".format(exc.errno))
    if go_error is not None:
        if go_error == "go-cancelled":
            try:
                os.close(policy_write_fd)
            except OSError:
                pass
            os._exit(125)
        child_policy_fail(policy_write_fd, go_error)
    if os.getppid() != supervisor_pid:
        child_policy_fail(policy_write_fd, "supervisor-exited")
    try:
        os.execvpe(TARGET[0], TARGET, os.environ)
    except OSError as exc:
        child_policy_fail(policy_write_fd, "exec-{}".format(exc.errno))

try:
    os.close(GO_FD)
    GO_FD = -1
except OSError as exc:
    fail_after_fork("go-reader-close-{}".format(exc.errno))
try:
    os.close(policy_write_fd)
    policy_write_fd = -1
except OSError as exc:
    fail_after_fork("policy-writer-close-{}".format(exc.errno))
policy_receipt = read_child_policy()
if policy_receipt != "READY":
    fail_after_fork("target-{}".format(policy_receipt))
if stop_signal:
    fail_after_fork("launcher-exited")
if not emit("READY"):
    fail_after_fork("status-pipe-unavailable")

grace_deadline = None
while True:
    has_children = reap()
    if stop_signal:
        emit("TERMINATED:{}".format(stop_signal))
        terminate_descendants()
        root_status = root_status if root_status is not None else (stop_signal & 0x7f)
        break
    if root_status is not None:
        if not has_children:
            break
        if grace_deadline is None:
            grace_deadline = time.monotonic() + GRACE_SECONDS
        if time.monotonic() >= grace_deadline:
            emit("DESCENDANTS")
            terminate_descendants()
            break
    time.sleep(0.01)

if root_status is None:
    fail("missing-root-status")
policy_completion = read_policy_completion()
if policy_completion is not None:
    if policy_completion.startswith("ERROR:"):
        emit("ERROR:target-{}".format(policy_completion.removeprefix("ERROR:")))
    else:
        emit("ERROR:target-{}".format(policy_completion))
try:
    os.close(policy_read_fd)
    policy_read_fd = -1
except OSError as exc:
    emit("ERROR:policy-reader-close-{}".format(exc.errno))
try:
    os.close(children_fd)
    children_fd = -1
except OSError as exc:
    fail("children-close-{}".format(exc.errno))
if not emit("COMPLETE"):
    os._exit(125)
try:
    os.close(STATUS_FD)
except OSError:
    os._exit(125)
if os.WIFEXITED(root_status):
    os._exit(os.WEXITSTATUS(root_status))
signum = os.WTERMSIG(root_status)
signal.signal(signum, signal.SIG_DFL)
os.kill(os.getpid(), signum)
os._exit(128 + signum)
"""


def supervisor_command(
    target: PreparedProcessArgv,
    *,
    forbidden_roots: Sequence[str | os.PathLike[str]],
) -> PreparedProcessArgv:
    """Freeze the trusted interpreter used by the dedicated Linux subreaper."""

    interpreter = str(getattr(sys, "_base_executable", "") or sys.executable)
    prepared = prepare_process_argv([interpreter])
    if not isinstance(prepared, PreparedProcessArgv):
        prepared = PreparedProcessArgv(prepared, artifact_paths=(prepared[0],))
    frozen = freeze_process_argv(prepared, forbidden_roots=forbidden_roots)
    target_payload = base64.urlsafe_b64encode(
        json.dumps(list(target), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return frozen.bind("-I", "-S", "-c", SUPERVISOR_SOURCE, target_payload)


def read_ready(
    descriptor: int,
    process: subprocess.Popen[Any],
) -> tuple[list[str], bytes]:
    """Require a bounded READY receipt before accepting a Linux child."""

    deadline = time.monotonic() + READY_SECONDS
    payload = bytearray()
    while b"\n" not in payload:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OSError("Linux process supervisor did not become ready")
        readable, _, _ = select.select((descriptor,), (), (), remaining)
        if not readable:
            raise OSError("Linux process supervisor did not become ready")
        chunk = os.read(descriptor, STATUS_LIMIT - len(payload))
        if not chunk:
            raise OSError("Linux process supervisor exited before containment")
        payload.extend(chunk)
        if len(payload) >= STATUS_LIMIT:
            raise OSError("Linux process supervisor status exceeded its limit")
    first, remainder = bytes(payload).split(b"\n", 1)
    try:
        message = first.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise OSError("Linux process supervisor returned invalid status") from exc
    if message != "READY":
        raise OSError(f"Linux process supervisor failed closed: {message}")
    if process.poll() is not None and process.returncode not in (None, 0):
        raise OSError("Linux process supervisor exited during containment setup")
    return [message], remainder


def close_status(process: subprocess.Popen[Any]) -> None:
    with suppress(OSError):
        _close_process_descriptor(process, "_agency_supervisor_status_fd")


def _validate_status_protocol(messages: Sequence[str]) -> tuple[str, ...]:
    """Require one READY, bounded informational records, then one COMPLETE."""

    receipt = tuple(messages)
    if not receipt or receipt[0] != "READY" or receipt.count("READY") != 1:
        raise OSError("Linux process supervisor status is missing its unique READY receipt")
    complete_count = receipt.count("COMPLETE")
    if complete_count == 0:
        raise OSError("Linux process supervisor did not report terminal completion")
    if complete_count != 1 or receipt[-1] != "COMPLETE":
        raise OSError("Linux process supervisor returned an invalid terminal status sequence")
    seen: set[str] = set()
    for message in receipt[1:-1]:
        if message == "DESCENDANTS":
            category = "DESCENDANTS"
        elif message.startswith("TERMINATED:") and message.removeprefix("TERMINATED:").isdecimal():
            category = "TERMINATED"
        elif message.startswith("ERROR:") and len(message) > len("ERROR:"):
            category = "ERROR"
        else:
            raise OSError(f"Linux process supervisor returned invalid status: {message}")
        if category in seen:
            raise OSError(
                f"Linux process supervisor returned duplicate informational status: {category}"
            )
        seen.add(category)
    failures = [message for message in receipt if message.startswith("ERROR:")]
    if failures:
        raise OSError(f"Linux process supervisor failed closed: {failures[-1]}")
    return receipt


def collect_status(process: subprocess.Popen[Any]) -> tuple[str, ...]:
    """Read the final bounded status receipt after a supervised process exits."""

    descriptor = descriptor_number(getattr(process, "_agency_supervisor_status_fd", None))
    messages = list(getattr(process, "_agency_supervisor_messages", ()))
    payload = bytearray(getattr(process, "_agency_supervisor_status_buffer", b""))
    if not isinstance(descriptor, int):
        return _validate_status_protocol(messages)
    try:
        while len(payload) < STATUS_LIMIT:
            chunk = os.read(descriptor, STATUS_LIMIT - len(payload))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) >= STATUS_LIMIT:
            raise OSError("Linux process supervisor status exceeded its limit")
    finally:
        close_status(process)
    if payload:
        if not payload.endswith(b"\n"):
            raise OSError("Linux process supervisor returned a truncated terminal status")
        try:
            decoded = payload.decode("ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise OSError("Linux process supervisor returned invalid status") from exc
        messages.extend(item for item in decoded.splitlines() if item)
    process._agency_supervisor_messages = messages
    process._agency_supervisor_status_buffer = b""
    return _validate_status_protocol(messages)


__all__ = [
    "GO_ENV",
    "PARENT_ENV",
    "READY_SECONDS",
    "STATUS_ENV",
    "STATUS_LIMIT",
    "SUPERVISOR_SOURCE",
    "DescriptorOwner",
    "cancel_go",
    "close_go",
    "close_status",
    "collect_status",
    "descriptor_number",
    "read_ready",
    "release_go",
    "supervisor_command",
]
