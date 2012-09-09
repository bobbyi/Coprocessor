import operator


def square(x):
    return x * x


def add(x, y):
    return x + y


def product(*args):
    return reduce(operator.mul, args)
