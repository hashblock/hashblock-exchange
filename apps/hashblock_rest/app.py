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

from flask import Flask, request, url_for
from flask_restplus import Resource, Api, fields

from modules.exceptions import DataException, AuthException, NotPrimeException
from modules.config import load_hashblock_config
from modules.address import Address
from modules.decode import decode_from_leaf
from modules.decode import decode_asset_list
from modules.decode import decode_asset_unit_list
from modules.decode import decode_proposals
from modules.decode import decode_settings
from modules.decode import decode_match_dimension
from modules.decode import decode_match_initiate_list
from modules.decode import decode_match_reciprocate_list

import shared.asset as asset

LOGGER = logging.getLogger(__name__)

application = Flask(__name__)

# Load up our configuration for URLs and keys

load_hashblock_config()
print("Succesfully loaded hasblock-rest configuration")

api = Api(
    application,
    validate=True,
    version='0.1.0',
    title='hashblock-rest',
    description='REST for hashblock-exchange')

ns = api.namespace('hashblock', description='hashblock state operations')

_setting_address = Address(Address.FAMILY_SETTING)
_asset_address = Address(Address.FAMILY_ASSET)
_match_address = Address(Address.FAMILY_MATCH)


# Utility functions


def assetlinks(data):
    for element in data:
        addr = element['link']
        baseref = 'asset_' + element['type']
        element['link'] = url_for(baseref, address=addr, _external=True)
    return data


def assetunitlinks(data, asset_type):
    for element in data:
        addr = element['link']
        baseref = 'asset_' + asset_type
        element['link'] = url_for(baseref, address=addr, _external=True)
    return data


def matchlinks(data, desc_term, url_path):
    new_data = []
    for element in data:
        op, link = element
        new_data.append({
            desc_term: op,
            'link': url_for(url_path + op, address=link, _external=True)})
    return new_data


def matchtermlinks(data, url_path):
    new_data = []
    for element in data:
        cargo, address = element
        link = url_for(url_path, address=address, _external=True)
        cargo['link'] = link
        new_data.append(cargo)
    return new_data


# Entry points

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


asset_fields = ns.model('asset', {
    'system': fields.String(
        required=True, description='The asset classification'),
    'key': fields.String(
        required=True, description='The asset key',),
    'value': fields.String(required=True, description='The asset value'),
    'signer': fields.String(
        required=True, description='The authorized proposer')})

asset_vote_fields = ns.model('asset-vote', {
    'proposal_id': fields.String(
        required=True, description='The asset proposal to vote on'),
    'vote': fields.String(
        required=True, description='The vote for proposal_id',),
    'signer': fields.String(
        required=True, description='The authorized voter')})


@ns.route('/propose-resource')
class RAPIngest(Resource):
    @ns.expect(asset_fields)
    def post(self):
        try:
            proposal_id = asset.create_proposal(
                Address.DIMENSION_RESOURCE, request.json)
            return {"proposal_id": proposal_id, "status": "OK"}, 200
        except (DataException, ValueError, NotPrimeException):
            return {"DataException": "invalid payload"}, 400
        except AuthException:
            return {
                "AuthException": "not authorized to make proposals"}, 405


@ns.route('/vote-resource')
class RAVIngest(Resource):
    @ns.expect(asset_vote_fields)
    def post(self):
        try:
            asset.create_vote(
                Address.DIMENSION_RESOURCE, request.json)
            return {"status": "OK"}, 200
        except (DataException, ValueError, NotPrimeException):
            return {"DataException": "invalid payload"}, 400
        except AuthException:
            return {
                "AuthException": "not authorized to vote"}, 405


@ns.route('/propose-unit')
class UAPIngest(Resource):
    @ns.expect(asset_fields)
    def post(self):
        try:
            proposal_id = asset.create_proposal(
                Address.DIMENSION_UNIT, request.json)
            return {"proposal_id": proposal_id, "status": "OK"}, 200
        except (DataException, ValueError, NotPrimeException):
            return {"DataException": "invalid payload"}, 400
        except AuthException:
            return {
                "AuthException": "not authorized to make proposals"}, 405


@ns.route('/vote-unit')
class UAVIngest(Resource):
    @ns.expect(asset_vote_fields)
    def post(self):
        try:
            asset.create_vote(
                Address.DIMENSION_UNIT, request.json)
            return {"status": "OK"}, 200
        except (DataException, ValueError, NotPrimeException):
            return {"DataException": "invalid payload"}, 400
        except AuthException:
            return {
                "AuthException": "not authorized to vote"}, 405


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
@ns.route('/resource/<string:address>', endpoint='asset_resource')
@ns.param('address', 'The address to decode')
class AU_Decode(Resource):
    def get(self, address):
        """Return asset details"""
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/utxqs')
class UTXQDecode(Resource):
    def get(self):
        """Returns all match request transactions"""
        result = decode_match_dimension(
            _match_address.txq_dimension(Address.DIMENSION_UTXQ))
        new_data = matchlinks(result['data'], 'operation', 'utxq_')
        result['data'] = new_data
        return result, 200


@ns.route('/asks', endpoint='utxq_asks')
@ns.route('/offers', endpoint='utxq_offers')
@ns.route('/commitments', endpoint='utxq_commitments')
@ns.route('/gives', endpoint='utxq_gives')
class UTXQS_Decode(Resource):
    def get(self):
        """Returns all match requests by type"""
        tail = request.path.split('/')[-1]
        ref = tail[:-1]
        indr = 'utxq_' + ref
        result = decode_match_initiate_list(
            _match_address.txq_list(Address.DIMENSION_UTXQ, ref))
        new_data = matchtermlinks(result['data'], indr)
        result['data'] = new_data
        return result, 200


@ns.route('/ask/<string:address>', endpoint='utxq_ask')
@ns.route('/offer/<string:address>', endpoint='utxq_offer')
@ns.route('/commitment/<string:address>', endpoint='utxq_commitment')
@ns.route('/give/<string:address>', endpoint='utxq_give')
@ns.param('address', 'The address to decode')
class UTXQ_Decode(Resource):
    def get(self, address):
        """Return match request detail"""
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/mtxqs')
class MTXQDecode(Resource):
    def get(self):
        """Returns all match response transactions"""
        result = decode_match_dimension(
            _match_address.txq_dimension(Address.DIMENSION_MTXQ))
        new_data = matchlinks(result['data'], 'operation', 'mtxq_')
        result['data'] = new_data
        return result, 200


@ns.route('/tells', endpoint='mtxq_tells')
@ns.route('/accepts', endpoint='mtxq_accepts')
@ns.route('/obligations', endpoint='mtxq_obligations')
@ns.route('/takes', endpoint='mtxq_takes')
class MTXQS_Decode(Resource):
    def get(self):
        """Returns all match response by type"""
        tail = request.path.split('/')[-1]
        ref = tail[:-1]
        indr = 'utxq_' + ref
        result = decode_match_reciprocate_list(
            _match_address.txq_list(Address.DIMENSION_MTXQ, ref))
        new_data = matchtermlinks(result['data'], indr)
        result['data'] = new_data
        return result, 200


@ns.route('/tell/<string:address>', endpoint='mtxq_tell')
@ns.route('/accept/<string:address>', endpoint='mtxq_accept')
@ns.route('/obligation/<string:address>', endpoint='mtxq_obligation')
@ns.route('/take/<string:address>', endpoint='mtxq_take')
@ns.param('address', 'The address to decode')
class MTXQ_Decode(Resource):
    def get(self, address):
        """Return match response detail"""
        if Address.valid_leaf_address(address):
            return decode_from_leaf(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


if __name__ == '__main__':
    application.run(debug=True)
