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

import os
import logging

from flask import Flask, request, url_for
from flask_restplus import Resource, Api, fields
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from modules.exceptions import DataException, AuthException, NotPrimeException
from modules.config import load_hashblock_config, agreement_secret
from modules.address import Address
from modules.decode import (
    decode_from_leaf,
    decode_asset, decode_unit,
    decode_asset_list, decode_unit_list,
    decode_proposals, decode_settings, decode_match_dimension,
    decode_match_initiate_list, decode_match_reciprocate_list)
import shared.asset as asset
import shared.match as match

LOGGER = logging.getLogger(__name__)

# Load up our configuration for URLs and keys

load_hashblock_config()
print("Succesfully loaded hasblock-rest configuration")

# Setup upload location for batch submissions
UPLOAD_FOLDER = '/uploads/files/'
ALLOWED_EXTENSIONS = set(['json'])

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Setup application
application = Flask(__name__)
application.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

api = Api(
    application,
    validate=True,
    version='0.1.0',
    title='hashblock-rest',
    description='REST for hashblock-exchange')

ns = api.namespace('hashblock', description='hashblock state operations')

_setting_address = Address.setting_addresser()
_utxq_address = Address.match_utxq_addresser()
_mtxq_address = Address.match_mtxq_addresser()

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


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


asset_fields = ns.model('asset', {
    'system': fields.String(
        required=True, description='The asset classification'),
    'key': fields.String(
        required=True, description='The asset key',),
    'signer': fields.String(
        required=True, description='The authorized proposer')})

asset_vote_fields = ns.model('asset-vote', {
    'proposal_id': fields.String(
        required=True, description='The asset proposal to vote on'),
    'vote': fields.String(
        required=True, description='The vote for proposal_id',),
    'signer': fields.String(
        required=True, description='The authorized voter')})

asset_propose_upload_parser = ns.parser()
asset_propose_upload_parser.add_argument(
    'file', location='files',
    type=FileStorage, required=True)

# Entry points


# @ns.route('/asset-seed')
# class ABFIngest(Resource):
#     @ns.expect(asset_propose_upload_parser)
#     def post(self):
#         """Batch process asset propose/vote seed data onto chain"""
#         args = asset_propose_upload_parser.parse_args()
#         in_name = args['file'].filename
#         if not allowed_file(in_name):
#             return {
#                 "DataException":
#                 "{} unsupported file type".format(in_name)}, 400
#         try:
#             destination = application.config.get('UPLOAD_FOLDER')
#             filename = '%s%s' % (destination, secure_filename(in_name))
#             args['file'].save(filename)
#             args['file'].close()
#             asset.create_asset_batch(filename)
#         except (DataException, ValueError) as e:
#             return {"DataException": str(e)}, 400
#         return {"data": "TBD"}, 200

#
#   Asset management
#

@ns.route('/asset-settings')
class ASSetDecode(Resource):
    def get(self):
        """Returns the asset settings"""
        return decode_settings(asset.ASSET_ADDRESSER.setting_address), 200


@ns.route('/assets')
class ASDecode(Resource):
    def get(self):
        """Returns list of all assets"""
        result = decode_asset_list()
        result['data'] = assetlinks(result['data'])
        return result, 200


@ns.route('/asset-create')
class CreateASIngest(Resource):
    @ns.expect(asset_fields)
    def post(self):
        """Create an asset and publish on the chain"""
        try:
            asset_id = asset.create_direct_asset(request.json)
            return {"Asset ID": asset_id, "status": "OK"}, 200
        except (DataException, ValueError) as e:
            return {"DataException": str(e)}, 400
        except AuthException:
            return {
                "AuthException": "not authorized to create asset"}, 405


@ns.route('/asset-propose')
class PropASIngest(Resource):
    @ns.expect(asset_fields)
    def post(self):
        """Propose an asset for publishing on the chain"""
        try:
            proposal_id = asset.create_asset_proposal(request.json)
            return {"proposal_id": proposal_id, "status": "OK"}, 200
        except (DataException, ValueError) as e:
            return {"DataException": str(e)}, 400
        except AuthException:
            return {
                "AuthException": "not authorized to make proposals"}, 405


@ns.route('/asset-proposals')
class ASPropDecode(Resource):
    def get(self):
        """Returns asset proposals"""
        return decode_proposals(asset.ASSET_ADDRESSER.candidate_address), 200


@ns.route('/asset-vote')
class VoteASIngest(Resource):
    @ns.expect(asset_vote_fields)
    def post(self):
        """Vote on asset proposal"""
        try:
            asset.create_asset_vote(request.json)
            return {"status": "OK"}, 200
        except (DataException, ValueError, NotPrimeException):
            return {"DataException": "invalid payload"}, 400
        except AuthException:
            return {
                "AuthException": "not authorized to vote"}, 405

#
#   Unit management
#


@ns.route('/unit-settings')
class UNSetDecode(Resource):
    def get(self):
        """Returns the unit settings"""
        return decode_settings(asset.UNIT_ADDRESSER.setting_address), 200


@ns.route('/units')
class UNDecode(Resource):
    def get(self):
        """Returns list of all units"""
        result = decode_unit_list()
        result['data'] = assetlinks(result['data'])
        return result, 200


@ns.route('/unit-create')
class CreateUNIngest(Resource):
    @ns.expect(asset_fields)
    def post(self):
        """Create a unit and publish on the chain"""
        try:
            unit_id = asset.create_direct_unit(request.json)
            return {"Unit ID": unit_id, "status": "OK"}, 200
        except (DataException, ValueError) as e:
            return {"DataException": str(e)}, 400
        except AuthException:
            return {
                "AuthException": "not authorized to create asset"}, 405


@ns.route('/unit-propose')
class PropUNIngest(Resource):
    @ns.expect(asset_fields)
    def post(self):
        """Propose a unit for publishing on the chain"""
        try:
            proposal_id = asset.create_unit_proposal(request.json)
            return {"proposal_id": proposal_id, "status": "OK"}, 200
        except (DataException, ValueError) as e:
            return {"DataException": str(e)}, 400
        except AuthException:
            return {
                "AuthException": "not authorized to make proposals"}, 405


@ns.route('/unit-proposals')
class UNPropDecode(Resource):
    def get(self):
        """Returns the list of unit proposals"""
        return decode_proposals(asset.UNIT_ADDRESSER.candidate_address), 200


@ns.route('/unit-vote')
class VoteUNIngest(Resource):
    @ns.expect(asset_vote_fields)
    def post(self):
        """Vote on unit proposal"""
        try:
            asset.create_unit_vote(request.json)
            return {"status": "OK"}, 200
        except (DataException, ValueError, NotPrimeException):
            return {"DataException": "invalid payload"}, 400
        except AuthException:
            return {
                "AuthException": "not authorized to vote"}, 405


@ns.route('/unit/<string:address>', endpoint='asset_unit')
@ns.route('/asset/<string:address>', endpoint='asset_asset')
@ns.param('address', 'The address to decode')
class AU_Decode(Resource):
    def get(self, address):
        """Return asset details"""
        tail = request.path.split('/')[-2]
        f = decode_asset if tail == 'asset' else decode_unit
        if Address.valid_leaf_address(address):
            return f(address), 200
        else:
            return {
                "address": "not a valid address",
                "data": ""}, 400


@ns.route('/utxqs/<string:agreement>')
@ns.param('agreement', 'The trading agreement')
class UTXQDecode(Resource):
    def get(self, agreement):
        """Returns all match request transactions"""
        result = decode_match_dimension(
            _utxq_address.dimension_address,
            agreement)
        # new_data = matchlinks(result['data'], 'operation', 'utxq_')
        # result['data'] = new_data
        return result, 200


# @ns.route('/asks/<string:agreement>', endpoint='utxq_asks')
# @ns.route('/offers/<string:agreement>', endpoint='utxq_offers')
# @ns.route('/commitments/<string:agreement>', endpoint='utxq_commitments')
# @ns.route('/gives/<string:agreement>', endpoint='utxq_gives')
# @ns.param('agreement', 'The trading agreement')
# class UTXQS_Decode(Resource):
#     def get(self, agreement):
#         """Returns all match requests by type"""
#         tail = request.path.split('/')[-2]
#         ref = tail[:-1]
#         indr = 'utxq_' + ref
#         result = decode_match_initiate_list(
#             _utxq_address.txq_list(_utxq_address.dimension, ref),
#             agreement)
#         # new_data = matchtermlinks(result['data'], indr)
#         # result['data'] = new_data
#         return result, 200


# @ns.route('/ask/<string:agreement>/<string:address>', endpoint='utxq_ask')
# @ns.route('/offer/<string:agreement>/<string:address>', endpoint='utxq_offer')
# @ns.route('/commitment/<string:agreement>/<string:address>', endpoint='utxq_commitment')
# @ns.route('/give/<string:agreement>/<string:address>', endpoint='utxq_give')
# @ns.param('agreement', 'The trading agreement')
# @ns.param('address', 'The address to decode')
# class UTXQ_Decode(Resource):
#     def get(self, agreement, address):
#         """Return match request detail"""

#         if Address.valid_leaf_address(address):
#             return decode_from_leaf(
#                 address,
#                 agreement_secret(agreement)), 200
#         else:
#             return {
#                 "address": "not a valid address",
#                 "data": ""}, 400


match_asset_fields = ns.model('asset detail', {
    'system': fields.String(required=True),
    'key': fields.String(required=True),
})

quantity_fields = ns.model('quantity_list', {
    'value': fields.String(required=True),
    'unit': fields.Nested(match_asset_fields, required=True),
    'resource': fields.Nested(match_asset_fields, required=True)
})

ratio_fields = ns.model('ratio', {
    'numerator': fields.Nested(quantity_fields, required=True),
    'denominator': fields.Nested(quantity_fields, required=True)
})

utxq_fields = ns.model('utxq_fields', {
    'plus': fields.String(required=True),
    'minus': fields.String(required=True),
    'quantity': fields.Nested(quantity_fields, required=True)
})

mtxq_fields = ns.inherit("mtxq_fields", utxq_fields, {
    'ratio': fields.Nested(ratio_fields, required=True),
    'utxq_address': fields.String(required=True)
})


# @ns.route('/ask')
# @ns.route('/offer')
# @ns.route('/commitment')
# @ns.route('/give')
# class UTXQ_Ingest(Resource):
#     @ns.expect(utxq_fields)
#     def post(self):
#         operation = request.path.split('/')[-1]
#         print("Creating {} transaction".format(operation))
#         match.create_utxq(operation, request.json)
#         return {"status": "OK"}, 200


@ns.route('/mtxqs/<string:agreement>')
@ns.param('agreement', 'The trading agreement')
class MTXQDecode(Resource):
    def get(self, agreement):
        """Returns all match response transactions"""
        result = decode_match_dimension(
            _mtxq_address.dimension_address,
            agreement)
        # new_data = matchlinks(result['data'], 'operation', 'mtxq_')
        # result['data'] = new_data
        return result, 200


# @ns.route('/tells/<string:agreement>', endpoint='mtxq_tells')
# @ns.route('/accepts/<string:agreement>', endpoint='mtxq_accepts')
# @ns.route('/obligations/<string:agreement>', endpoint='mtxq_obligations')
# @ns.route('/takes/<string:agreement>', endpoint='mtxq_takes')
# @ns.param('agreement', 'The trading agreement')
# class MTXQS_Decode(Resource):
#     def get(self, agreement):
#         """Returns all match response by type"""
#         tail = request.path.split('/')[-2]
#         ref = tail[:-1]
#         indr = 'mtxq_' + ref
#         result = decode_match_reciprocate_list(
#             _mtxq_address.txq_list(_mtxq_address.dimension, ref),
#             agreement)
#         # new_data = matchtermlinks(result['data'], indr)
#         # result['data'] = new_data
#         return result, 200


# @ns.route('/tell/<string:agreement>/<string:address>', endpoint='mtxq_tell')
# @ns.route('/accept/<string:agreement>/<string:address>', endpoint='mtxq_accept')
# @ns.route('/obligation/<string:agreement>/<string:address>', endpoint='mtxq_obligation')
# @ns.route('/take/<string:agreement>/<string:address>', endpoint='mtxq_take')
# @ns.param('agreement', 'The trading agreement')
# @ns.param('address', 'The address to decode')
# class MTXQ_Decode(Resource):
#     def get(self, agreement, address):
#         """Return match response detail"""
#         if Address.valid_leaf_address(address):
#             return decode_from_leaf(
#                 address,
#                 agreement_secret(agreement)), 200
#         else:
#             return {
#                 "address": "not a valid address",
#                 "data": ""}, 400


# @ns.route('/tell')
# @ns.route('/accept')
# @ns.route('/obligation')
# @ns.route('/take')
# class MTXQ_Ingest(Resource):
#     @ns.expect(mtxq_fields)
#     def post(self):
#         operation = request.path.split('/')[-1]
#         print("Creating {} transaction".format(operation))
#         try:
#             match.create_mtxq(operation, request.json)
#             return {"status": "OK"}, 200
#         except (DataException, ValueError) as e:
#             return {"DataException": str(e)}, 400


if __name__ == '__main__':
    application.run(debug=True)
