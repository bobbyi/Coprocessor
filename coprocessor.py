#!/usr/bin/env python
import contextlib
import functools
import imp
import inspect
import os
from socket import socket
import subprocess
import sys

PYTHON = '/home/bobby/Spatial_Pattern_Analysis/pypy-c-jit-56812-028b65a5a45f-linux64/bin/pypy'


class Module(object):
    def __init__(self, co, mod_name):
        self.co = co
        self.mod_name = mod_name

    def __getattr__(self, func_name):
        def func(*args, **kw):
            return self.co.call_function(self.mod_name, func_name, *args, **kw)
        return func


class CoProcessor(object):
    def __init__(self):
        self.proc = self.conn = None

    def start_proc(self):
        if self.proc is not None:
            return
        sock = socket()
        sock.bind(('', 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        cmd = [PYTHON, __file__, str(port)]
        env = dict(os.environ, in_subproc='TRUE')
        self.proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE)
        self.conn, addr = sock.accept()

    def connect(self, port):
        self.conn = socket()
        self.conn.connect(('', port))

    def send(self, msg):
        self.conn.sendall(msg + '\n')

    def recv(self):
        msg = ''
        while not msg.endswith('\n'):
            msg += self.conn.recv(1)
        msg = msg[:-1]
        if not msg:
            raise EOFError
        return msg

    def recv_obj(self):
        return eval(self.recv())

    def send_obj(self, obj):
        return self.send(repr(obj))

    def close(self):
        if self.proc is not None:
            self.send('')
            assert self.proc.wait() == 0, 'Subprocess failed'
        if self.conn is not None:
            self.conn.close()
        self.conn = self.proc = None

    def import_module(self, mod_name):
        self.start_proc()
        mod = __import__(mod_name)
        source_file_path = inspect.getsourcefile(mod)
        self.send(source_file_path)
        assert self.recv() == 'ok'
        return Module(self, mod_name)

    def call_function(self, mod_name, func_name, *args, **kw):
        self.send_obj((func_name, args, kw))
        return self.recv_obj()


def main():
    co = CoProcessor()
    port = int(sys.argv[1])
    co.connect(port)
    source_file_path = co.recv()
    assert os.path.exists(source_file_path), source_file_path
    co.send('ok')
    module = imp.load_source('magic!', source_file_path)
    with contextlib.closing(co):
        while True:
            try:
                func_name, args, kw = co.recv_obj()
            except EOFError:
                return
            func = getattr(module, func_name)
            ret = func(*args, **kw)
            co.send_obj(ret)


if __name__ == '__main__':
    main()
