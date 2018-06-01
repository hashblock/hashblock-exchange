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

#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>
#include <fstream>
#include <iostream>
#include <sstream>


#include <libff/common/profiling.hpp>
#include <libsnark/common/default_types/r1cs_ppzksnark_pp.hpp>
#include <libsnark/zk_proof_systems/ppzksnark/r1cs_ppzksnark/r1cs_ppzksnark.hpp>
#include <hbutils.hpp>
#include <match_r1cs.hpp>
#include <base64.h>

using namespace libsnark;

match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> _r1cs;
match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> __r1cs;
r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp> _proof;


// Loads a key from file and decodes from base64
template<class T>
T get_constraint_key(std::string const& file_path,
                                std::string const& file_name)
{
    std::ofstream key_file;
    key_file.open(file_path + file_name, std::fstream::in);
    std::stringstream encoded_key;
    encoded_key << key_file.rdbuf();
    std::string key = base64_decode(encoded_key.str());
    std::stringstream _key(key);
    T the_pk;
    _key >> the_pk;
    return the_pk;
}


r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp> decode_proof_string(std::string const& proof_str)
{
    std::stringstream encoded_proof;
    encoded_proof << proof_str;
    std::string decoded_proof = base64_decode(encoded_proof.str());
    r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp> proof;
    std::stringstream decoded_proof_stream;
    decoded_proof_stream << decoded_proof;
    decoded_proof_stream >> proof;
    return proof;
}

match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> generate_constraint(std::vector<int> const& ints)
{
    default_r1cs_ppzksnark_pp::init_public_params();
    return
        generate_match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>>(
            ints[0], ints[1],ints[2], ints[3],
            ints[4], ints[5],ints[6], ints[7],
            ints[8], ints[9],ints[10], ints[11]);
}

match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>>
    generate_constraint(std::string const& intake_string)
{
    return generate_constraint(extract_ints(intake_string));
}

int generate_constraint_keys(
    std::string const& file_path,
    match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> const& r1cs)
{
    default_r1cs_ppzksnark_pp::init_public_params();
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
    std::ofstream file_pk(file_path + hbutil::PROOVE_KEYNAME);
    std::ofstream file_vk(file_path + hbutil::VERIFY_KEYNAME);
    file_pk << encoded_spk;
    file_vk << encoded_svk;
    return 0;
}

r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp>
    proove(std::string const& file_path,
        match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> const& r1cs)
{
    default_r1cs_ppzksnark_pp::init_public_params();
    r1cs_ppzksnark_proving_key<default_r1cs_ppzksnark_pp> prvkey =
         get_constraint_key<r1cs_ppzksnark_proving_key<default_r1cs_ppzksnark_pp>>
            (file_path, hbutil::PROOVE_KEYNAME);
    r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp> proof =
        r1cs_ppzksnark_prover<default_r1cs_ppzksnark_pp>(prvkey,
            r1cs.primary_input, r1cs.auxiliary_input);

    std::stringstream proofstr;
    proofstr << proof;
    std::string spk = proofstr.str();
    std::string encoded_spk = base64_encode(
        reinterpret_cast<const unsigned char*>(spk.c_str()), spk.length());
    std::cerr << encoded_spk << std::endl;
   return proof;
}

int verify(std::string const& file_path,
    r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp> proof,
    match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> const& r1cs)
{
    default_r1cs_ppzksnark_pp::init_public_params();
    r1cs_ppzksnark_verification_key<default_r1cs_ppzksnark_pp> verkey =
        get_constraint_key<r1cs_ppzksnark_verification_key<default_r1cs_ppzksnark_pp>>
        (file_path, hbutil::VERIFY_KEYNAME);
    const bool ans = r1cs_ppzksnark_verifier_strong_IC<default_r1cs_ppzksnark_pp>(
        verkey, r1cs.primary_input, proof);
    std::cout << ans << std::endl;

    return 0;
}

void zksnark_test(std::string file_path) {
    default_r1cs_ppzksnark_pp::init_public_params();
    const std::string ptest("10,4,2,20,11,13,11,13,17,19,17,19");
    match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> r1csP =
         generate_constraint(ptest);
    verify(file_path, proove(file_path, r1csP), r1csP);

    const std::string ftest("0,4,2,20,11,13,11,13,17,19,17,19");
    match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> r1csF =
         generate_constraint(ftest);
    verify(file_path, proove(file_path, r1csF), r1csP );
}

int main(int argc, const char * argv[]) {

    if (argc < 3) {
        std::cerr <<  "Invalid call. hbzksnark [-g, -p, -v] [options]" << std::endl;
        return -1;
    }
    else if (strcmp(argv[1], "-g") == 0) {
        if (argc > 4) {
            std::cerr << "Invalid call. hbzksnark -g file_path secret_string" << std::endl;
            return -1;
        }
        else {
            std::string file_path(argv[2]);
            std::string keyvars(argv[3]);
            // match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> r1csP =
            //     generate_constraint(extract_ints(keyvars));
            return generate_constraint_keys(file_path,
                generate_constraint(keyvars));
                //keyvars);
        }
    }
    else if (strcmp(argv[1], "-p") == 0) {
        if (argc != 4) {
            std::cerr << "Invalid call. hbzksnark -p file_path data_str" << std::endl;
            return -1;
        }
        else {
            std::string file_path(argv[2]);
            std::string keyvars(argv[3]);
            proove(file_path,generate_constraint(keyvars));
            return 0;
        }
    }
    else if (strcmp(argv[1], "-v") == 0) {
        if (argc != 5) {
            std::cerr << "Invalid call. hbzksnark -v file_path proof_str data_str" << std::endl;
            return -1;
        }
        else {
            std::string file_path(argv[2]);
            std::string proofstr(argv[3]);
            std::string keyvars(argv[4]);
            verify(file_path, decode_proof_string(proofstr), generate_constraint(keyvars));
            return 0;
        }
    }
    else if (strcmp(argv[1], "-t") == 0) {
            std::string file_path(argv[2]);
            zksnark_test(file_path);
    }
    else {
        std::cerr <<  "No command match. Correct input and try again" << std::endl;
        return -1;
    }

    return 0;
}

