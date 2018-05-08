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
from shared.transactions import (
    submit_single_txn, create_batch_list,
    create_batch, create_transaction, compose_builder)
from modules.address import Address
from modules.exceptions import DataException


def _validate_settings(authorizations, threshold):
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


def _create_setting(ingest):
    """Creates the setting for a particular dimension"""
    signer, addresser, auth_keys, threshold = ingest
    settings = Settings(
        auth_list=','.join(auth_keys),
        threshold=threshold)
    return (
        signer,
        addresser,
        SettingPayload(
            action=SettingPayload.CREATE,
            dimension=addresser.dimension,
            data=settings.SerializeToString()))


def _create_inputs_outputs(ingest):
    """Creates the input and output addresses for setting transaction"""
    signer, addresser, payload = ingest
    props = Address(Address.FAMILY_ASSET)
    inputs = [
        addresser.settings(payload.dimension),
        props.candidates(payload.dimension)]
    outputs = [
        addresser.settings(payload.dimension),
        props.candidates(payload.dimension)]
    return (
        signer,
        addresser,
        {"inputs": inputs, "outputs": outputs},
        payload)


_unit_addrs = Address(
    Address.FAMILY_SETTING, "0.1.0", Address.DIMENSION_UNIT)
_resource_addrs = Address(
    Address.FAMILY_SETTING, "0.1.0", Address.DIMENSION_RESOURCE)


def _create_settings(signer, resauths, resthresh, uomauths, uomthresh):
    """Creates and returns a batch of setting transactions"""
    valid_signer(signer)
    res_auth_keys = _validate_settings(resauths, resthresh)
    uom_auth_keys = _validate_settings(uomauths, uomthresh)
    setting_txn_build = compose_builder(
        create_transaction,
        _create_inputs_outputs,
        _create_setting)
    res_setting = setting_txn_build(
        (signer, _resource_addrs, res_auth_keys, resthresh))[1]
    uom_setting = setting_txn_build(
        (signer, _unit_addrs, uom_auth_keys, uomthresh))[1]
    return create_batch((signer, [res_setting, uom_setting]))


def create_settings_submit(signer, resauths, resthresh, uomauths, uomthresh):
    """Submits setting transactions interactivley"""
    batch = _create_settings(signer, resauths, resthresh, uomauths, uomthresh)
    if not batch:
        raise DataException
    pass


def create_settings_batch(signer, resauths, resthresh, uomauths, uomthresh):
    """Creates the setting batch and returns for later submission"""
    batch = _create_settings(signer, resauths, resthresh, uomauths, uomthresh)
    if not batch:
        raise DataException
    return create_batch_list([batch])
