#!/usr/bin/env python
import functools
import imp
import inspect
import os
from socket import socket
import subprocess
import sys

PYTHON = '/home/bobby/Spatial_Pattern_Analysis/pypy-c-jit-56812-028b65a5a45f-linux64/bin/pypy'


def pypy(func):
    if os.getenv('in_subproc'):
        return func
    source_file = inspect.getsourcefile(inspect.getmodule(func))
    func_name = func.func_name
    sock = socket()
    sock.bind(('', 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    cmd = [PYTHON, __file__, str(port)]

    @functools.wraps(func)
    def inner(*args, **kw):
        env = dict(os.environ, in_subproc='TRUE')
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE)
        conn, addr = sock.accept()
        msg = repr([source_file, func_name, args, kw])
        conn.sendall(msg)
        msg = conn.recv(1000)
        conn.close()
        retcode = proc.wait()
        assert retcode == 0, 'Subprocess failed'
        return eval(msg)
    return inner


def main():
    port = int(sys.argv[1])
    sock = socket()
    sock.connect(('', port))
    msg = sock.recv(1000)
    source_file, func_name, args, kw = eval(msg)
    module = imp.load_source('magic!', source_file)
    func = getattr(module, func_name)
    msg = repr(func(*args, **kw))
    sock.sendall(msg)
    sock.close()


if __name__ == '__main__':
    main()
