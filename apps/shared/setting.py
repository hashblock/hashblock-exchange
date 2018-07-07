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

"""setting - hashblock-setting business logic

This module is referenced when posting hashblock-setting transactions
"""

from modules.config import valid_signer
from protobuf.setting_pb2 import Settings, SettingPayload
from shared.transactions import (create_transaction, compose_builder)
from modules.address import Address
from modules.exceptions import DataException


def __validate_settings(authorizations, threshold):
    """Validates authorization keys and threshold"""
    entries = []
    threshold = int(threshold)
    for entry in authorizations:
        key = valid_signer(entry)
        entries.append(key)
    if not threshold:
        raise DataException('approval thresholds must be greater than 1')
    elif threshold < 1:
        raise DataException('approval thresholds must be positive number')
    elif threshold > len(entries):
        raise DataException(
            'approval thresholds must not be greater than number of '
            'authorizing keys')
    return entries


def __create_setting(ingest):
    """Creates the setting for a particular family"""
    signer, addresser, auth_keys, threshold = ingest
    settings = Settings(
        auth_list=','.join(auth_keys),
        threshold=threshold)
    return (
        signer,
        addresser,
        SettingPayload(
            action=SettingPayload.CREATE,
            dimension=addresser.family,
            data=settings.SerializeToString()))


def __create_inputs_outputs(ingest):
    """Creates the input and output addresses for setting transaction"""
    signer, addresser, payload = ingest
    inputs = [
        addresser.setting_address,
        addresser.candidate_address]
    outputs = [
        addresser.setting_address,
        addresser.candidate_address]
    return (
        signer,
        Address.setting_addresser(),
        # addresser,
        {"inputs": inputs, "outputs": outputs},
        payload)


def __create_settings(signer, assetauths, assetthresh, unitauths, unitthresh):
    """Creates and returns a batch of setting transactions"""
    valid_signer(signer)
    _asset_addrs = Address.asset_addresser()
    _unit_addrs = Address.unit_addresser()
    asset_auth_keys = __validate_settings(assetauths, assetthresh)
    unit_auth_keys = __validate_settings(unitauths, unitthresh)
    setting_txn_build = compose_builder(
        create_transaction,
        __create_inputs_outputs,
        __create_setting)
    asset_setting_txn = setting_txn_build(
        (signer, _asset_addrs, asset_auth_keys, assetthresh))[1]
    unit_setting_txn = setting_txn_build(
        (signer, _unit_addrs, unit_auth_keys, unitthresh))[1]
    return [asset_setting_txn, unit_setting_txn]


def create_settings_genesis(
        signer, assetauths, assetthresh, unitauths, unitthresh):
    """Creates the setting transactions returns for later submission"""
    return __create_settings(
        signer, assetauths, assetthresh, unitauths, unitthresh)
