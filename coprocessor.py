#!/usr/bin/env python
import sys
sys.dont_write_bytecode = True
try:
    import cPickle as pickle
except ImportError:
    import pickle
import atexit
import imp
import importlib
import os
from socket import socket
import subprocess
import threading


PYTHON = '/usr/local/bin/pypy'

MSG_CLOSE = 0
MSG_OK = 1
MSG_EXC = 2
MSG_IMPORT = 3
MSG_CALL = 4


class Importer(object):
    def find_module(self, fullname, path=None):
        if fullname == 'pypy':
            return self
        if fullname.startswith('pypy.'):
            return self

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
        if fullname == 'pypy':
            module = imp.new_module(fullname)
        else:
            name = fullname.replace('pypy.', '', 1)
            co = PyPy.start()
            module = co.import_module(name)
        module.__loader__ = self
        module.__file__ = __file__
        module.__path__ = []
        sys.modules[fullname] = module
        return module


class PyPy(object):
    co = None
    lock = threading.Lock()

    @classmethod
    def start(cls):
        if cls.co is None:
            with cls.lock:
                if cls.co is None:
                    cls.co = CoProcessor()
                    atexit.register(cls.stop)
        return cls.co

    @classmethod
    def stop(cls):
        with cls.lock:
            if cls.co is not None:
                cls.co.close()
            cls.co = None


sys.meta_path.append(Importer())


class Module(object):
    def __init__(self, mod_name):
        self.mod_name = mod_name

    def __getattr__(self, func_name):
        def func(*args, **kw):
            co = PyPy.start()
            return co.call_function(self.mod_name, func_name, *args, **kw)
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

    def poll(self):
        if self.proc is not None:
            ret = self.proc.poll()
            if ret is not None:
                self.conn = self.proc = None
                raise Exception('Subprocess died')

    def send(self, msg):
        self.conn.sendall(msg + '\0')

    def recv(self):
        msg = ''
        while not msg.endswith('\0'):
            self.poll()
            msg += self.conn.recv(1)
        msg = msg[:-1]
        return msg

    def send_obj(self, obj):
        try:
            data = pickle.dumps(obj)
        except Exception:
            raise Unpickleable()
        return self.send(data)

    def recv_obj(self):
        data = self.recv()
        try:
            return pickle.loads(data)
        except Exception:
            raise Unpickleable()

    def send_message(self, message_type, *args):
        msg = (message_type, args)
        self.send_obj(msg)

    def send_exception(self, err):
        try:
            self.send_message(MSG_EXC, err)
        except pickle.PickleError:
            try:
                msg = str(err)
            except Exception:
                msg = 'Failure in coprocess. Error is unpickleable.'
            err = Exception(msg)
            self.send_message(MSG_EXC, err)

    def recv_response(self):
        msg_type, args = self.recv_obj()
        if msg_type == MSG_EXC:
            [exc] = args
            raise exc
        assert msg_type == MSG_OK
        return args

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
        self.recv_response()
        return Module(mod_name)

    def call_function(self, mod_name, func_name, *args, **kw):
        self.start_proc()
        self.send_message(MSG_CALL, mod_name, func_name, args, kw)
        ret, = self.recv_response()
        return ret


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
                co.send_message(MSG_OK, ret)
            except Exception as err:
                co.send_exception(err)
        else:
            raise TypeError('Unknown message type %s' % msg_type)


if __name__ == '__main__':
    main()
