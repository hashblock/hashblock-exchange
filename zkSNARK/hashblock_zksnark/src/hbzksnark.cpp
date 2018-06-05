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
#include <stdexcept>


#include <libff/common/profiling.hpp>
#include <libsnark/common/default_types/r1cs_ppzksnark_pp.hpp>
#include <libsnark/zk_proof_systems/ppzksnark/r1cs_ppzksnark/r1cs_ppzksnark.hpp>
#include <hbutils.hpp>
#include <match_r1cs.hpp>
#include <base64.h>

using namespace libsnark;
using namespace std;

// Loads a key from file and decodes from base64
template<class T>
T get_constraint_key(string const& file_path, string const& file_name)
{
    ofstream key_file;
    key_file.open(file_path + file_name, fstream::in);
    stringstream encoded_key;
    encoded_key << key_file.rdbuf();
    string key = base64_decode(encoded_key.str());
    stringstream _key(key);
    T the_pk;
    _key >> the_pk;
    return the_pk;
}


r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp>
    decode_proof_string(string const& proof_str)
{
    default_r1cs_ppzksnark_pp::init_public_params();
    r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp> proof;
    try
    {
        stringstream encoded_proof;
        encoded_proof << proof_str;
        string decoded_proof = base64_decode(encoded_proof.str());
        stringstream decoded_proof_stream;
        decoded_proof_stream << decoded_proof;
        decoded_proof_stream >> proof;
    }
    catch(...)
    {
        cerr << "Something wicked" << endl;
    }
    return proof;
}

match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>>
    generate_constraint(vector<int> const& ints)
{
    default_r1cs_ppzksnark_pp::init_public_params();
    return
        generate_match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>>(
            ints[0], ints[1],ints[2], ints[3],
            ints[4], ints[5],ints[6], ints[7],
            ints[8], ints[9],ints[10], ints[11]);
}

match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>>
    generate_constraint(string const& intake_string)
{
    return generate_constraint(extract_ints(intake_string));
}

int generate_constraint_keys(
    string const& file_path,
    match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> const& r1cs)
{
    default_r1cs_ppzksnark_pp::init_public_params();
    r1cs_ppzksnark_keypair<default_r1cs_ppzksnark_pp> keypair =
        r1cs_ppzksnark_generator<default_r1cs_ppzksnark_pp>(r1cs.constraint_system);

    stringstream pkss;
    stringstream vkss;
    pkss << keypair.pk ;
    string spk = pkss.str();
    string encoded_spk = base64_encode(
        reinterpret_cast<const unsigned char*>(spk.c_str()), spk.length());
    vkss << keypair.vk;
    string svk = vkss.str();
    string encoded_svk = base64_encode(
        reinterpret_cast<const unsigned char*>(svk.c_str()), svk.length());
    ofstream file_pk(file_path + hbutil::PROOVE_KEYNAME);
    ofstream file_vk(file_path + hbutil::VERIFY_KEYNAME);
    file_pk << encoded_spk;
    file_vk << encoded_svk;
    return 0;
}

int verify(string const& file_path,
    r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp> proof,
    string const& encoded_pi)
{
    default_r1cs_ppzksnark_pp::init_public_params();
    r1cs_ppzksnark_verification_key<default_r1cs_ppzksnark_pp> verkey =
        get_constraint_key<r1cs_ppzksnark_verification_key<default_r1cs_ppzksnark_pp>>
        (file_path, hbutil::VERIFY_KEYNAME);

    libff::Fr<default_r1cs_ppzksnark_pp> field;
    r1cs_primary_input<libff::Fr<default_r1cs_ppzksnark_pp>>
        new_primary_input;

    stringstream dec_strm(base64_decode(encoded_pi));

    while (dec_strm >> field)
        new_primary_input.push_back(field);

    const bool ans = r1cs_ppzksnark_verifier_strong_IC<default_r1cs_ppzksnark_pp>(
        verkey, new_primary_input, proof);
    cout << ans << endl;

    return 0;
}

r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp>
    proove(string const& file_path,
        match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> const& r1cs)
{
    default_r1cs_ppzksnark_pp::init_public_params();
    r1cs_ppzksnark_proving_key<default_r1cs_ppzksnark_pp> prvkey =
         get_constraint_key<r1cs_ppzksnark_proving_key<default_r1cs_ppzksnark_pp>>
            (file_path, hbutil::PROOVE_KEYNAME);
    r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp> proof =
        r1cs_ppzksnark_prover<default_r1cs_ppzksnark_pp>(prvkey,
            r1cs.primary_input, r1cs.auxiliary_input);

    // Get the primary input and encode
    stringstream pairing_stream;
    for(auto it = r1cs.primary_input.begin();
        it != r1cs.primary_input.end(); ++it)
        pairing_stream << *it;;

    string pairing_str = pairing_stream.str();
    string encoded_pairing = base64_encode(
        reinterpret_cast<const unsigned char*>(
            pairing_str.c_str()),pairing_str.length());

    stringstream proofstr;
    proofstr << proof;
    string spk = proofstr.str();
    string encoded_spk = base64_encode(
        reinterpret_cast<const unsigned char*>(spk.c_str()), spk.length());

    cerr << encoded_spk << ' ' << encoded_pairing;
    return proof;
}

int main(int argc, const char * argv[]) {

    if (argc < 3) {
        cerr <<  "Invalid call. hbzksnark [-g, -p, -v] [options]" << endl;
        return -1;
    }
    else if (strcmp(argv[1], "-g") == 0) {
        //  Generate keys returns 0 for successful generation else
        //  exception in secret key given. If exception, return -1 and stderr has reason
        if (argc > 4) {
            cerr << "Invalid call. hbzksnark -g file_path secret_string" << endl;
            return -1;
        }
        else {
            try {
                string file_path(argv[2]);
                string keyvars(argv[3]);
                return generate_constraint_keys(file_path,
                    generate_constraint(keyvars));
            }
            catch(std::invalid_argument & e) {
                cerr << e.what() << endl;
                return -1;
            }
        }
    }
    else if (strcmp(argv[1], "-p") == 0) {
        //  Generate proof returns 0 for successful generation else
        //  exception in secret key given. If exception, return -1 and stderr has reason
        if (argc != 4) {
            cerr << "Invalid call. hbzksnark -p file_path data_str" << endl;
            return -1;
        }
        else {
            try {
                string file_path(argv[2]);
                string keyvars(argv[3]);
                proove(file_path,generate_constraint(keyvars));
                return 0;
            }
            catch(std::invalid_argument & e) {
                cerr << e.what() << endl;
                return -1;
            }
        }
    }
    else if (strcmp(argv[1], "-v") == 0) {
        //  Verify proof returns 0 for successful generation else
        //  exception in secret key given. If exception, return -1 and stderr has reason
        if (argc != 5) {
            cerr << "Invalid call. hbzksnark -v file_path proof_str pairing_str" << endl;
            return -1;
        }
        else {
            try {
                string file_path(argv[2]);
                string proofstr(argv[3]);
                string pairing(argv[4]);
                verify(file_path, decode_proof_string(proofstr), pairing);
                return 0;
            }
            catch(std::invalid_argument & e) {
                cerr << e.what() << endl;
                return -1;
            }
        }
    }
    else {
        cerr <<  "No command match. Correct input and try again" << endl;
        return -1;
    }

    return 0;
}

