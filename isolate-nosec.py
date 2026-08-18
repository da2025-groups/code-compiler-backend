#!/usr/bin/env python3
"""
Isolate no-sandbox wrapper for macOS ARM Docker (QEMU emulation).

Setuid and clone() namespaces both fail under QEMU x86_64 on ARM64.
This wrapper replaces isolate entirely — no calls to isolate.real.
Box directories are created under /tmp/piston-boxes (writable by all).
"""
import sys
import os
import subprocess
import time
import signal as _sig
import shutil

BOX_BASE = '/tmp/piston-boxes'


def cmd_init(box_id):
    box_root = os.path.join(BOX_BASE, str(box_id))
    box_dir = os.path.join(box_root, 'box')
    os.makedirs(box_dir, mode=0o755, exist_ok=True)
    print(box_root)  # isolate --init prints the box root; job.js reads this


def cmd_cleanup(box_id):
    box_root = os.path.join(BOX_BASE, str(box_id))
    if os.path.exists(box_root):
        shutil.rmtree(box_root, ignore_errors=True)


def cmd_run(box_id, meta_file, env_vars, wall_time, chdir_path, cmd):
    box_dir = os.path.join(BOX_BASE, str(box_id), 'box')

    # /box/submission inside sandbox → box_dir/submission
    if chdir_path.startswith('/box'):
        work_dir = box_dir + chdir_path[4:]
    else:
        work_dir = box_dir

    if not os.path.isdir(work_dir):
        work_dir = box_dir

    run_env = {
        'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
    }
    run_env.update(env_vars)

    t0 = time.monotonic()
    exit_code = 0
    sig_num = None
    status_str = None

    try:
        proc = subprocess.run(cmd, cwd=work_dir, env=run_env, timeout=wall_time)
        elapsed = time.monotonic() - t0
        exit_code = proc.returncode
        if exit_code < 0:
            sig_num = -exit_code
            status_str = 'SG'
        elif exit_code != 0:
            status_str = 'RE'
    except subprocess.TimeoutExpired:
        elapsed = wall_time
        exit_code = 137
        sig_num = _sig.SIGKILL.value
        status_str = 'TO'
    except Exception as exc:
        elapsed = time.monotonic() - t0
        exit_code = 1
        status_str = 'RE'
        sys.stderr.write(f'isolate-wrapper: {exc}\n')

    if meta_file:
        try:
            with open(meta_file, 'w') as f:
                f.write(f'exitcode:{exit_code}\n')
                if sig_num is not None:
                    f.write(f'exitsig:{sig_num}\n')
                if status_str:
                    f.write(f'status:{status_str}\n')
                f.write(f'time:{elapsed:.3f}\n')
                f.write(f'time-wall:{elapsed:.3f}\n')
        except OSError as e:
            sys.stderr.write(f'isolate-wrapper: meta write error: {e}\n')

    sys.exit(exit_code)


def main():
    argv = sys.argv[1:]

    mode = None
    box_id = 0
    meta_file = None
    env_vars = {}
    wall_time = 30.0
    chdir_path = '/box'
    cmd = []

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--':
            cmd = argv[i + 1:]
            break
        elif a == '--init':
            mode = 'init'
        elif a == '--cleanup':
            mode = 'cleanup'
        elif a == '--run':
            mode = 'run'
        elif a == '--print-cg-root':
            mode = 'cg-root'
        elif a == '--version':
            mode = 'version'
        elif a in ('--cg', '-s', '--silent', '--share-net', '-D', '--no-default-dirs',
                   '--wait', '--inherit-fds', '--tty-hack', '--special-files'):
            pass  # ignored flags
        elif a.startswith('-b'):
            box_id = int(a[2:])
        elif a.startswith('--box-id='):
            box_id = int(a.split('=', 1)[1])
        elif a.startswith('--meta='):
            meta_file = a[7:]
        elif a in ('-E', '--env'):
            i += 1
            if i < len(argv):
                kv = argv[i]
                k, _, v = kv.partition('=')
                env_vars[k] = v if _ else os.environ.get(k, '')
        elif a.startswith('--env='):
            kv = a[6:]
            k, _, v = kv.partition('=')
            env_vars[k] = v
        elif a in ('-c', '--chdir'):
            i += 1
            if i < len(argv):
                chdir_path = argv[i]
        elif a.startswith('-c') and len(a) > 2:
            chdir_path = a[2:]
        elif a.startswith('--chdir='):
            chdir_path = a[8:]
        elif a.startswith('--wall-time='):
            wall_time = float(a[12:])
        # --processes, --open-files, --fsize, --time, --extra-time,
        # --cg-mem, --dir, --mem, --stack, --core, --quota, --as-uid, etc.
        # → all ignored (no sandboxing)
        i += 1

    if mode == 'init':
        cmd_init(box_id)
    elif mode == 'cleanup':
        cmd_cleanup(box_id)
    elif mode == 'run':
        if not cmd:
            sys.stderr.write('isolate-wrapper: no command after --\n')
            sys.exit(1)
        cmd_run(box_id, meta_file, env_vars, wall_time, chdir_path, cmd)
    elif mode == 'cg-root':
        print('/sys/fs/cgroup')
    elif mode == 'version':
        print('The process isolator 2.0 (nosec-wrapper)')
    else:
        sys.stderr.write(f'isolate-wrapper: unknown args: {argv}\n')
        sys.exit(1)


if __name__ == '__main__':
    main()
