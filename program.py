import operator


def square(x):
    return x * x


def add(x, y):
    return x + y


def product(*args):
    return reduce(operator.mul, args)


def raise_unpickleable():
    raise Exception(lambda : 3)


def raise_unpickleable2():
    class Hidden(Exception):
        pass
    raise Hidden
