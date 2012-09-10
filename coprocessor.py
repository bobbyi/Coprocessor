#!/usr/bin/env python
import sys
sys.dont_write_bytecode = True
try:
    import cPickle as pickle
except ImportError:
    import pickle
import importlib
import os
from socket import socket
import subprocess


PYTHON = '/usr/local/bin/pypy'

MSG_CLOSE = 0
MSG_IMPORT = 1
MSG_CALL = 2
MSG_FUNC_RET = 3 
MSG_EXC = 4
MSG_OK = 5


class Module(object):
    def __init__(self, co, mod_name):
        self.co = co
        self.mod_name = mod_name

    def __getattr__(self, func_name):
        def func(*args, **kw):
            return self.co.call_function(self.mod_name, func_name, *args, **kw)
        return func


class Unpickleable(pickle.PickleError):
    pass


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
        data = self.recv()
        try:
            return pickle.loads(data)
        except Exception:
            raise Unpickleable()

    def send_obj(self, obj):
        try:
            data = pickle.dumps(obj)
        except Exception:
            raise Unpickleable()
        return self.send(data)

    def send_message(self, message_type, *args):
        msg = (message_type, args)
        self.send_obj(msg)

    def send_exception(self, err):
        try:
            self.send_message(MSG_EXC, err)
        except Unpickleable:
            try:
                msg = str(err)
            except Exception:
                msg = 'Failure in coprocess. Error is unpickleable.'
            err = Exception(msg)
            self.send_message(MSG_EXC, err)

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
        msg_type, args = self.recv_obj()
        if msg_type == MSG_OK:
            return Module(self, mod_name)
        elif msg_type == MSG_EXC:
            [exc] = args
            raise exc
        else:
            raise TypeError('Unknown message type %s' % msg_type)

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
    while True:
        msg_type, args = co.recv_obj()
        if msg_type == MSG_CLOSE:
            co.close()
            return
        elif msg_type == MSG_IMPORT:
            [mod_name] = args
            try:
                importlib.import_module(mod_name)
            except Exception as err:
                co.send_exception(err)
            else:
                co.send_message(MSG_OK)
        elif msg_type == MSG_CALL:
            mod_name, func_name, args, kw = args
            try:
                module = importlib.import_module(mod_name)
                func = getattr(module, func_name)
                ret = func(*args, **kw)
                co.send_message(MSG_FUNC_RET, ret)
            except Exception as err:
                co.send_exception(err)
        else:
            raise TypeError('Unknown message type %s' % msg_type)


if __name__ == '__main__':
    main()
