# ------------------------------------------------------------------------------
# Copyright 2018 Frank V. Castellucci
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------


from abc import ABC, abstractmethod


class HashblockAst(ABC):
    """Base abstract ast class"""

    @abstractmethod
    def eval(self):
        pass


class Initiate(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        for t in self.value:
            t.eval()


class Reciprocate(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Reciprocate")
        for t in self.value:
            t.eval()


class Partner(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Partner: {}".format(self.value))


class Verb(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Verb: {}".format(self.value))


class Conjunction(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Conjunction: {}".format(self.value))


class Ratio(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Ratio: { ")
        print(" Numerator => ", end='')
        self.value[0].eval()
        print(" Denominator =>  ", end='')
        self.value[1].eval()
        print("}")


class Quantity(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Quantity: {", end='')
        for t in self.value:
            t.eval()
        print("}")


class Magnitude(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Magnitude: {} ".format(self.value), end='')


class Unit(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print(" Unit: ", end='')
        self.value[0].eval()


class Asset(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print(" Asset: ", end='')
        self.value[0].eval()


class QSymbol(HashblockAst):
    def __init__(self, ns, term):
        self.ns = ns
        self.term = term

    def eval(self):
        print("[namespace: {} term: {}]".format(self.ns, self.term), end='')


class Address(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("For Initiate: {}".format(self.value))


def ast_trace(el, indent=1):
    print("Trace: {}> {}".format(
        '-' * indent, el.__class__.__name__))
    if hasattr(el, 'value'):
        if type(el.value) is list:
            for i in el.value:
                indent += 1
                ast_trace(i, indent)
                indent -= 1
        else:
            pass
    else:
        pass
