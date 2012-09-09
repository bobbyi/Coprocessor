#!/usr/bin/env python
import sys
sys.dont_write_bytecode = True
import contextlib
try:
    import cPickle as pickle
except ImportError:
    import pickle
import os
from socket import socket
import subprocess


PYTHON = '/home/bobby/Spatial_Pattern_Analysis/pypy-c-jit-56812-028b65a5a45f-linux64/bin/pypy'
MSG_CLOSE = 0
MSG_IMPORT = 1
MSG_CALL = 2
MSG_FUNC_RET = 3 
MSG_EXC = 4


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
        self.proc = subprocess.Popen(cmd, env=env)
        self.conn, addr = sock.accept()

    def connect(self, port):
        self.conn = socket()
        self.conn.connect(('', port))

    def send(self, msg):
        self.conn.sendall(msg + '\0')

    def poll(self):
        if self.proc is not None:
            ret = self.proc.poll()
            if ret is not None:
                self.conn = self.proc = None
                raise Exception('Subprocess died')

    def recv(self):
        msg = ''
        while not msg.endswith('\0'):
            self.poll()
            msg += self.conn.recv(1)
        msg = msg[:-1]
        return msg

    def recv_obj(self):
        return pickle.loads(self.recv())

    def send_obj(self, obj):
        return self.send(pickle.dumps(obj))

    def send_message(self, message_type, *args):
        msg = (message_type, args)
        self.send_obj(msg)

    def close(self):
        if self.proc is not None:
            self.send_message(MSG_CLOSE)
            assert self.proc.wait() == 0, 'Subprocess failed'
        if self.conn is not None:
            self.conn.close()
        self.conn = self.proc = None

    def import_module(self, mod_name):
        self.start_proc()
        self.send_message(MSG_IMPORT, mod_name)
        assert self.recv() == 'ok'
        return Module(self, mod_name)

    def call_function(self, mod_name, func_name, *args, **kw):
        self.start_proc()
        self.send_message(MSG_CALL, mod_name, func_name, args, kw)
        msg_type, args = self.recv_obj()
        if msg_type == MSG_FUNC_RET:
            [ret] = args
            return ret
        elif msg_type == MSG_EXC:
            [exc] = args
            raise exc
        else:
            raise TypeError('Unknown message type %s' % msg_type)


def main():
    co = CoProcessor()
    port = int(sys.argv[1])
    co.connect(port)
    with contextlib.closing(co):
        while True:
            msg_type, args = co.recv_obj()
            if msg_type == MSG_CLOSE:
                return
            if msg_type == MSG_IMPORT:
                [mod_name] = args
                if mod_name not in sys.modules:
                    sys.modules[mod_name] = __import__(mod_name)
                co.send('ok')
            elif msg_type == MSG_CALL:
                mod_name, func_name, args, kw = args
                module = sys.modules[mod_name]
                func = getattr(module, func_name)
                try:
                    ret = func(*args, **kw)
                    co.send_message(MSG_FUNC_RET, ret)
                except Exception as err:
                    co.send_message(MSG_EXC, err)
            else:
                raise TypeError('Unknown message type %s' % msg_type)


if __name__ == '__main__':
    main()
