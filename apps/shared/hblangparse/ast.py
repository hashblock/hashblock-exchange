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

    @abstractmethod
    def to_dict(self, map=None):
        pass


class Initiate(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        for t in self.value:
            t.eval()

    def to_dict(self, map=None):
        result = {
            "plus": self.value[0].value,
            "operation": self.value[1].value,
            "minus": self.value[2].value
        }
        for t in self.value[3:]:
            t.to_dict(result)
        return result


class Reciprocate(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Reciprocate")
        for t in self.value:
            t.eval()

    def to_dict(self, map=None):
        result = {
            "plus": self.value[0].value,
            "operation": self.value[1].value,
            "minus": self.value[2].value
        }
        for t in self.value[3:]:
            t.to_dict(result)
        return result


class Partner(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Partner: {}".format(self.value))

    def to_dict(self, map=None):
        pass


class Verb(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Verb: {}".format(self.value))

    def to_dict(self, map=None):
        pass


class Conjunction(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Conjunction: {}".format(self.value))

    def to_dict(self, map=None):
        map['object'] = self.value


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

    def to_dict(self, map=None):
        r = {}
        self.value[0].to_dict(r)
        r['numerator'] = r.pop('quantity')
        self.value[1].to_dict(r)
        r['denominator'] = r.pop('quantity')
        map['ratio'] = r


class Quantity(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Quantity: {", end='')
        for t in self.value:
            t.eval()
        print("}")

    def to_dict(self, map=None):
        q = {}
        for t in self.value:
            t.to_dict(q)
        map['quantity'] = q


class Magnitude(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("Magnitude: {} ".format(self.value), end='')

    def to_dict(self, map=None):
        map['value'] = self.value


class Unit(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print(" Unit: ", end='')
        self.value[0].eval()

    def to_dict(self, map=None):
        u = {}
        for t in self.value:
            t.to_dict(u)
        map['unit'] = u


class Asset(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print(" Asset: ", end='')
        self.value[0].eval()

    def to_dict(self, map=None):
        a = {}
        for t in self.value:
            t.to_dict(a)
        map['asset'] = a


class QSymbol(HashblockAst):
    def __init__(self, ns, term):
        self.ns = ns
        self.term = term

    def eval(self):
        print("[namespace: {} term: {}]".format(self.ns, self.term), end='')

    def to_dict(self, map=None):
        map['system'] = self.ns
        map['key'] = self.term


class Address(HashblockAst):
    def __init__(self, value):
        self.value = value

    def eval(self):
        print("For Initiate: {}".format(self.value))

    def to_dict(self, map=None):
        map['utxq_address'] = self.value


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
