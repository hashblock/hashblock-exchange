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

from apps.hashblock_rest.config.hb_rest_config import load_config
from modules.address import Address
from modules.decode import decode_from_leaf

LOGGER = logging.getLogger(__name__)

application = Flask(__name__)
api = Api(application,
          version='0.1.0',
          title='#B REST',
          description='REST-API for hashblock-exchange')

ns = api.namespace('hashblock', description='#B operations')


@ns.route('/resource-settings/<string:address>')
@ns.param('address', 'The address to decode')
class RASDecode(Resource):
    """Responsible for fetching data and decoding it
    """
    @ns.doc(id='Get the decoded result of an block address')
    def get(self, address):
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/resource-proposals/<string:address>')
@ns.param('address', 'The address to decode')
class RAPDecode(Resource):
    """Responsible for fetching data and decoding it
    """
    @ns.doc(id='Get the decoded result of an block address')
    def get(self, address):
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/resources/<string:address>')
@ns.param('address', 'The address to decode')
class RADecode(Resource):
    """Responsible for fetching data and decoding it
    """
    @ns.doc(id='Get the decoded result of an block address')
    def get(self, address):
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/unit-settings/<string:address>')
@ns.param('address', 'The address to decode')
class UASDecode(Resource):
    """Responsible for fetching data and decoding it
    """
    @ns.doc(id='Get the decoded result of an block address')
    def get(self, address):
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/unit-proposals/<string:address>')
@ns.param('address', 'The address to decode')
class UAPDecode(Resource):
    """Responsible for fetching data and decoding it
    """
    @ns.doc(id='Get the decoded result of an block address')
    def get(self, address):
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/units/<string:address>')
@ns.param('address', 'The address to decode')
class UADecode(Resource):
    """Responsible for fetching data and decoding it
    """
    @ns.doc(id='Get the decoded result of an block address')
    def get(self, address):
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/utxqs/<string:address>')
@ns.param('address', 'The address to decode')
class UTXQDecode(Resource):
    """Responsible for fetching data and decoding it
    """
    @ns.doc(id='Get the decoded result of an block address')
    def get(self, address):
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/mtxqs/<string:address>')
@ns.param('address', 'The address to decode')
class MTXQDecode(Resource):
    """Responsible for fetching data and decoding it
    """
    @ns.doc(id='Get the decoded result of an block address')
    def get(self, address):
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


if __name__ == '__main__':
    print("Loading hasblock REST application")
    load_config('hb_rest.yaml')
    application.run(debug=True)
