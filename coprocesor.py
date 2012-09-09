#!/usr/bin/env python
import tempfile
import imp
import inspect
import os
import subprocess
import sys

PYTHON = '/home/bobby/Spatial_Pattern_Analysis/pypy-c-jit-56812-028b65a5a45f-linux64/bin/pypy'

def pypy(func):
    if os.getenv('in_subproc'):
        return func
    source_file = inspect.getsourcefile(inspect.getmodule(func))
    func_name = func.func_name
    argpath = tempfile.mkstemp()[1]
    cmd = [PYTHON, __file__, source_file, func_name, argpath]
    def inner(*args, **kw):
        env = dict(os.environ)
        env['in_subproc'] = 'TRUE'
        with open(argpath, 'w') as arg_file:
            args = (args, kw)
            arg_file.write(repr(args))
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        return eval(stdout)
    return inner


def main():
    source_file, func_name, argpath = sys.argv[1:]
    module = imp.load_source('magic!', source_file)
    func = getattr(module, func_name)
    with open(argpath) as arg_file:
        args, kw = eval(arg_file.read())
    print func(*args, **kw)


if __name__ == '__main__':
    main()
