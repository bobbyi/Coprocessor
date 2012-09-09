import operator
from coprocesor import pypy


@pypy
def square(x):
    return x * x


@pypy
def add(x, y):
    return x + y


@pypy
def product(*args):
    return reduce(operator.mul, args)
