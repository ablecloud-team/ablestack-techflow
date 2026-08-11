#!/usr/bin/env python3
"""Run an Issue #46 command on the TechFlow test server.

Credentials are accepted only through process environment variables so they are
never written to the repository, command output, or generated evidence.
"""

from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
import sys

import paramiko


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?")
    parser.add_argument("--command-base64", default=None)
    parser.add_argument("--put", nargs=2, metavar=("LOCAL", "REMOTE"))
    parser.add_argument("--get", nargs=2, metavar=("REMOTE", "LOCAL"))
    parser.add_argument("--stdin-file", default=None)
    parser.add_argument("--host", default=os.getenv("TECHFLOW_SSH_HOST", "211.115.222.251"))
    parser.add_argument("--port", type=int, default=int(os.getenv("TECHFLOW_SSH_PORT", "10023")))
    parser.add_argument("--user", default=os.getenv("TECHFLOW_SSH_USER", "ablecloud"))
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    command = args.command
    if args.command_base64:
        command = base64.b64decode(args.command_base64).decode("utf-8")
    if not command and not args.put and not args.get:
        parser.error("command, --put, or --get is required")

    password = os.getenv("TECHFLOW_SSH_PASSWORD")
    if not password:
        raise SystemExit("TECHFLOW_SSH_PASSWORD is required")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        args.host,
        port=args.port,
        username=args.user,
        password=password,
        timeout=20,
        banner_timeout=20,
        auth_timeout=20,
    )
    try:
        if args.put:
            local_path, remote_path = args.put
            with client.open_sftp() as sftp:
                sftp.put(local_path, remote_path)
        if args.get:
            remote_path, local_path = args.get
            with client.open_sftp() as sftp:
                sftp.get(remote_path, local_path)
        if not command:
            return 0
        stdin, stdout, stderr = client.exec_command(command, timeout=args.timeout)
        if args.stdin_file:
            stdin.write(Path(args.stdin_file).read_bytes())
            stdin.flush()
            stdin.channel.shutdown_write()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        if out:
            sys.stdout.write(out)
        if err:
            sys.stderr.write(err)
        return stdout.channel.recv_exit_status()
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
