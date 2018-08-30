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

import enum
from pprint import pprint


@enum.unique
class ExchangeType(enum.Enum):
    INITIATE = enum.auto()
    PARTNER = enum.auto()
    VERB = enum.auto()


class exchange_obj(object):
    def __init__(self, type_id, d):
        setattr(self, 'type', type_id)
        for a, b in d.items():
            if isinstance(b, (list, tuple)):
                setattr(
                    self,
                    a,
                    [exchange_obj(x) if isinstance(x, dict) else x for x in b])
            else:
                setattr(
                    self,
                    a,
                    exchange_obj(b) if isinstance(b, dict) else b)

    def __repr__(self):
        return '<%s>' % \
            str('\n '.join(
                '%s : %s' % (k, repr(v)) for (k, v) in self.__dict__.items()))


def main():
    dict1 = {'a': 1, 'b': 2}
    o1 = exchange_obj(ExchangeType.INITIATE, dict1)
    o1.a = 3
    dict2 = {'a': 1, 'o': o1}
    o2 = exchange_obj(ExchangeType.PARTNER, dict2)
    print("o1 = {}".format(o1.a))
    print("o2 = {}".format(o2.o.b))
    print("o1 type = {}".format(o1.type))
    print("o2 type = {}".format(o2.type))
    pprint(o1)
    pprint(o2)


if __name__ == '__main__':
    main()
