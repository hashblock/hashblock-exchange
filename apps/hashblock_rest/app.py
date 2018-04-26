# ------------------------------------------------------------------------------
# Copyright 2018 Frank V. Castellucci and Arthur Greef
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

import logging

from flask import Flask
from flask_restplus import Resource, Api

from hashblock_rest.config.hb_rest_config import load_config
from shared.address import Address
from shared.decode import decode_from_leaf

LOGGER = logging.getLogger(__name__)

application = Flask(__name__)
api = Api(application,
          version='0.1.0',
          title='#B REST',
          description='REST-API for hashblock-exchange')

ns = api.namespace('hashblock', description='#B operations')


@ns.route('/decode/<string:address>')
@ns.param('address', 'The address to decode')
class Decode(Resource):
    """Responsible for fetching data and decoding it
    """
    @ns.doc(id='Get the decoded result of an block address')
    def get(self, address):
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "invalid leaf address provided",
                "data": ""}, 400


@ns.route('/asset/proposal/')
class Asset(Resource):
    """Responsible for fetching data and decoding it
    """
    def get(self):
        # Call decode for an address, get back a map
        # structure with family, address, dimension, data
        return {
            'family': 'asset',
            'dimension': 'all',
            'data': '5 bags of peanuts'}, 200


if __name__ == '__main__':
    LOGGER.debug("Loading hasblock REST application")
    load_config('hb_rest.yaml')
    application.run(debug=True)
