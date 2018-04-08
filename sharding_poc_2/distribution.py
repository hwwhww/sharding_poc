# https://github.com/ethereum/research/blob/master/old_casper_poc3/distributions.py
import random


def normal_distribution(mean, standev):
    def f():
        return int(random.normalvariate(mean, standev))

    return f


def transform(dist, xformer):
    def f():
        return xformer(dist())

    return f
