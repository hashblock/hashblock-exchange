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

from flask import Flask, url_for
from flask_restplus import Resource, Api

from hashblock_rest.config.hb_rest_config import load_config
from modules.address import Address
from modules.decode import decode_from_leaf
from modules.decode import decode_asset_list
from modules.decode import decode_asset_unit_list
from modules.decode import decode_proposals
from modules.decode import decode_settings
from modules.decode import decode_match_dimension
from modules.decode import decode_match_initiate_list
from modules.decode import decode_match_reciprocate_list

LOGGER = logging.getLogger(__name__)

application = Flask(__name__)
api = Api(application,
          version='0.1.0',
          title='#B REST',
          description='REST-API for hashblock-exchange')

ns = api.namespace('hashblock', description='#B operations')

_setting_address = Address(Address.FAMILY_SETTING)
_asset_address = Address(Address.FAMILY_ASSET)
_match_address = Address(Address.FAMILY_MATCH)


def assetlinks(data):
    for element in data:
        addr = element['link']
        baseref = 'asset_' + element['type']
        element['link'] = api.base_url[:-1] + url_for(
            baseref, address=addr)
    return data


def assetunitlinks(data, asset_type):
    for element in data:
        addr = element['link']
        baseref = 'asset_' + asset_type
        element['link'] = api.base_url[:-1] + url_for(
            baseref, address=addr)
    return data


def matchlinks(data, desc_term, url_path):
    new_data = []
    for element in data:
        op, link = element
        new_data.append({
            desc_term: op,
            'link': api.base_url[:-1] +
            url_for(url_path + op, address=link)})
    return new_data


def matchtermlinks(data, url_path):
    new_data = []
    for element in data:
        cargo, address = element
        link = api.base_url[:-1] + url_for(url_path, address=address)
        cargo['link'] = link
        new_data.append(cargo)
    return new_data


@ns.route('/')
class StateDecode(Resource):
    def get(self):
        """Return a list of hashblock entities"""
        return {"data": "TBD"}, 200


@ns.route('/assets')
class ASDecode(Resource):
    def get(self):
        """Returns list of all asset units"""
        result = decode_asset_list(_asset_address.ns_family)
        result['data'] = assetlinks(result['data'])
        return result, 200


@ns.route('/resource-settings')
class RASDecode(Resource):
    def get(self):
        """Returns the resource asset unit settings"""
        return decode_settings(
            _setting_address.settings(Address.DIMENSION_RESOURCE)), 200


@ns.route('/resource-proposals')
class RAPDecode(Resource):
    def get(self):
        """Returns the resource asset unit proposals"""
        return decode_proposals(
            _asset_address.candidates(Address.DIMENSION_RESOURCE)), 200


@ns.route('/resources')
class RADecode(Resource):
    def get(self):
        """Returns all resource asset units"""
        result = decode_asset_unit_list(
            _asset_address.asset_prefix(Address.DIMENSION_RESOURCE))
        result['data'] = assetunitlinks(
            result['data'], Address.DIMENSION_RESOURCE)
        return result, 200


@ns.route('/resource/<string:address>', endpoint='asset_resource')
@ns.param('address', 'The address to decode')
class AU_resource_Decode(Resource):
    def get(self, address):
        """Return resource asset unit details"""
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/unit-settings')
class UASDecode(Resource):
    def get(self):
        """Returns the unit-of-measure asset unit settings"""
        return decode_settings(
            _setting_address.settings(Address.DIMENSION_UNIT)), 200


@ns.route('/unit-proposals')
class UAPDecode(Resource):
    def get(self):
        """Returns the unit-of-measure asset unit proposals"""
        return decode_proposals(
            _asset_address.candidates(Address.DIMENSION_UNIT)), 200


@ns.route('/units')
class UADecode(Resource):
    def get(self):
        """Returns all unit-of-measure asset units"""
        result = decode_asset_unit_list(
            _asset_address.asset_prefix(Address.DIMENSION_UNIT))
        result['data'] = assetunitlinks(
            result['data'], Address.DIMENSION_UNIT)
        return result, 200


@ns.route('/unit/<string:address>', endpoint='asset_unit')
@ns.param('address', 'The address to decode')
class AU_unit_Decode(Resource):
    def get(self, address):
        """Return unit-of-measure asset unit details"""
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/utxqs')
class UTXQDecode(Resource):
    def get(self):
        """Returns all utxqs"""
        result = decode_match_dimension(
            _match_address.txq_dimension(Address.DIMENSION_UTXQ))
        new_data = matchlinks(result['data'], 'operation', 'utxq_')
        result['data'] = new_data
        return result, 200


@ns.route('/asks', endpoint='utxq_asks')
class UTXQ_asks_Decode(Resource):
    def get(self):
        """Returns all asks"""
        result = decode_match_initiate_list(
            _match_address.txq_list(Address.DIMENSION_UTXQ, 'ask'))
        new_data = matchtermlinks(result['data'], 'utxq_ask')
        result['data'] = new_data
        return result, 200


@ns.route('/ask/<string:address>', endpoint='utxq_ask')
@ns.param('address', 'The address to decode')
class UTXQ_ask_Decode(Resource):
    def get(self, address):
        """Return match exchange detail"""
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/mtxqs')
class MTXQDecode(Resource):
    def get(self):
        """Returns all mtxqs"""
        result = decode_match_dimension(
            _match_address.txq_dimension(Address.DIMENSION_MTXQ))
        new_data = matchlinks(result['data'], 'operation', 'mtxq_')
        result['data'] = new_data
        return result, 200


@ns.route('/tells')
class MTXQ_tells_Decode(Resource):
    def get(self):
        """Returns all tells"""
        result = decode_match_reciprocate_list(
            _match_address.txq_list(Address.DIMENSION_MTXQ, 'tell'))
        new_data = matchtermlinks(result['data'], 'mtxq_tell')
        result['data'] = new_data
        return result, 200


@ns.route('/tell/<string:address>', endpoint='mtxq_tell')
@ns.param('address', 'The address to decode')
class MTXQ_tell_Decode(Resource):
    def get(self, address):
        """Return match exchange detail"""
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
