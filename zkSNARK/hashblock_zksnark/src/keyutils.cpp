/*
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
*/

#include <fstream>
#include <libff/common/profiling.hpp>

#include <libsnark/common/default_types/r1cs_ppzksnark_pp.hpp>
#include <libsnark/zk_proof_systems/ppzksnark/r1cs_ppzksnark/r1cs_ppzksnark.hpp>
#include <match_r1cs.hpp>
#include <base64.h>

using namespace libsnark;

void generate_constraint_keys(std::string const& file_path, std::vector<int> const& ints) {
    default_r1cs_ppzksnark_pp::init_public_params();

    std::cout << "Generating Constraint Keys" << std::endl;

    match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> r1cs =
        generate_match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>>(
            ints[0], ints[1],ints[2], ints[3],
            ints[4], ints[5],ints[6], ints[7],
            ints[8], ints[9],ints[10], ints[11]);

    r1cs_ppzksnark_keypair<default_r1cs_ppzksnark_pp> keypair =
        r1cs_ppzksnark_generator<default_r1cs_ppzksnark_pp>(r1cs.constraint_system);

    std::stringstream pkss;
    std::stringstream vkss;
    pkss << keypair.pk ;
    std::string spk = pkss.str();
    std::string encoded_spk = base64_encode(reinterpret_cast<const unsigned char*>(spk.c_str()), spk.length());
    vkss << keypair.vk;
    std::string svk = vkss.str();
    std::string encoded_svk = base64_encode(reinterpret_cast<const unsigned char*>(svk.c_str()), svk.length());
    std::string prvkey("hashblock_zkSNARK.pk");
    std::string valkey("hashblock_zkSNARK.vk");
    std::ofstream file_pk(file_path + prvkey);
    std::ofstream file_vk(file_path + valkey);
    file_pk << encoded_spk;
    file_vk << encoded_svk;
    std::cout << "Constraint Keys Created" << std::endl;
}


