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
from modules.config import load_hashblock_config
from modules.address import Address
from modules.decode import (
    decode_exchange_initiate,
    decode_exchange_initiate_list,
    decode_exchange_reciprocate,
    decode_exchange_reciprocate_list,
    decode_asset, decode_unit,
    decode_asset_list, decode_unit_list,
    decode_proposals, decode_settings)
import shared.asset as asset
import shared.exchange as exchange

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
    version='0.2.0',
    title='hashblock-rest',
    description='Convenience REST for hashblock-exchange')

ns = api.namespace('hashblock', description='hashblock operations')

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


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


property_fields = ns.model(
    'property', {
        'name': fields.String(description='The name (key) of the property'),
        'value': fields.String(
            description='The value associated to the property name')
    })

asset_fields = ns.model('asset', {
    'system': fields.String(
        required=True, description='The asset classification'),
    'key': fields.String(
        required=True, description='The asset key',),
    'signer': fields.String(
        required=True, description='The authorized proposer'),
    'properties': fields.List(
        fields.Nested(
            property_fields, skip_none=True))})

asset_vote_fields = ns.model('asset-vote', {
    'proposal_id': fields.String(
        required=True, description='The asset proposal ID to vote on'),
    'vote': fields.String(
        required=True, description='The vote for proposal_id',),
    'signer': fields.String(
        required=True, description='The authorized voter')})

unit_fields = ns.model('unit', {
    'system': fields.String(
        required=True, description='The unit classification'),
    'key': fields.String(
        required=True, description='The unit key',),
    'signer': fields.String(
        required=True, description='The authorized proposer')})

unit_vote_fields = ns.model('unit-vote', {
    'proposal_id': fields.String(
        required=True, description='The unit proposal ID to vote on'),
    'vote': fields.String(
        required=True, description='The vote for proposal_id',),
    'signer': fields.String(
        required=True, description='The authorized voter')})


batch_propose_upload_parser = ns.parser()
batch_propose_upload_parser.add_argument(
    'file', location='files',
    type=FileStorage, required=True)

# Entry points

#
#   Batch load management
#


@ns.route('/batch-seed')
class BatchIngest(Resource):
    @ns.expect(batch_propose_upload_parser)
    def post(self):
        """Batch process asset propose/vote seed data onto chain"""
        args = batch_propose_upload_parser.parse_args()
        in_name = args['file'].filename
        if not allowed_file(in_name):
            return {
                "DataException":
                "{} unsupported file type".format(in_name)}, 400
        try:
            destination = application.config.get('UPLOAD_FOLDER')
            filename = '%s%s' % (destination, secure_filename(in_name))
            args['file'].save(filename)
            args['file'].close()
            asset.create_asset_unit_batch(filename)
        except (DataException, ValueError) as e:
            return {"DataException": str(e)}, 400
        return {"data": "TBD"}, 200

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
    @ns.expect(unit_fields)
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
    @ns.expect(unit_fields)
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
    @ns.expect(unit_vote_fields)
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

#
# Exchange data models
#


exchange_fields = ns.model('quantity detail', {
    'system': fields.String(required=True),
    'key': fields.String(required=True),
})

quantity_fields = ns.model('quantity_list', {
    'value': fields.String(required=True),
    'unit': fields.Nested(exchange_fields, required=True),
    'asset': fields.Nested(exchange_fields, required=True)
})

ratio_fields = ns.model('ratio', {
    'numerator': fields.Nested(quantity_fields, required=True),
    'denominator': fields.Nested(quantity_fields, required=True)
})

utxq_fields = ns.model('utxq_fields', {
    'operation': fields.String(required=True),
    'plus': fields.String(required=True),
    'minus': fields.String(required=True),
    'quantity': fields.Nested(quantity_fields, required=True)
})

mtxq_fields = ns.inherit("mtxq_fields", utxq_fields, {
    'ratio': fields.Nested(ratio_fields, required=True),
    'utxq_address': fields.String(required=True)
})

#
#   Match post process utilities
#


def exchangeprep(result, agreement, eprefix):
    """Sets endpoint link in results"""
    for element in result["data"]:
        element["link"] = url_for(
            eprefix,
            agreement=agreement,
            address=element.pop("address"),
            _external=True)


#
#   UTXQ management
#


@ns.route('/utxq/<string:agreement>/<string:address>', endpoint='utxq')
@ns.param('agreement', 'The trading agreement')
@ns.param('address', 'The UTXQ address')
class UTXQDecode(Resource):
    def get(self, agreement, address):
        """Returns specific UTXQ"""
        result = decode_exchange_initiate(address, agreement)
        return result, 200


@ns.route('/utxqs/<string:agreement>')
@ns.param('agreement', 'The trading agreement')
class UTXQSDecode(Resource):
    def get(self, agreement):
        """Returns all UTXQs"""
        result = decode_exchange_initiate_list(agreement)
        exchangeprep(result, agreement, 'utxq')
        return result, 200


@ns.route('/utxq-create')
class UTXQ_Ingest(Resource):
    @ns.expect(utxq_fields)
    def post(self):
        exchange.create_utxq(request.json)
        return {"status": "OK"}, 200


#
#   MTXQ management
#


@ns.route('/mtxq/<string:agreement>/<string:address>', endpoint='mtxq')
@ns.param('agreement', 'The trading agreement')
@ns.param('address', 'The MTXQ address')
class MTXQDecode(Resource):
    def get(self, agreement, address):
        """Returns specific UTXQ"""
        result = decode_exchange_reciprocate(address, agreement)
        return result, 200


@ns.route('/mtxqs/<string:agreement>')
@ns.param('agreement', 'The trading agreement')
class MTXQSDecode(Resource):
    def get(self, agreement):
        """Returns all match response transactions"""
        result = decode_exchange_reciprocate_list(agreement)
        exchangeprep(result, agreement, 'mtxq')
        return result, 200


@ns.route('/mtxq-create')
class MTXQ_Ingest(Resource):
    @ns.expect(mtxq_fields)
    def post(self):
        """Create a matching transaction"""
        try:
            exchange.create_mtxq(request.json)
            return {"status": "OK"}, 200
        except (DataException, ValueError) as e:
            return {"DataException": str(e)}, 400


if __name__ == '__main__':
    application.run(debug=True)
