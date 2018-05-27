#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>
#include <fstream>
#include <iostream>

#include <libff/common/profiling.hpp>

#include <libsnark/zk_proof_systems/ppzkadsnark/r1cs_ppzkadsnark/examples/prf/aes_ctr_prf.tcc>
#include <libsnark/zk_proof_systems/ppzkadsnark/r1cs_ppzkadsnark/examples/signature/ed25519_signature.tcc>
#include <libsnark/common/default_types/r1cs_ppzkadsnark_pp.hpp>
#include <libsnark/zk_proof_systems/ppzkadsnark/r1cs_ppzkadsnark/r1cs_ppzkadsnark.hpp>
#include <libsnark/zk_proof_systems/ppzkadsnark/r1cs_ppzkadsnark/hashblock/match_r1cs.hpp>
#include <libsnark/zk_proof_systems/ppzkadsnark/r1cs_ppzkadsnark/hashblock/base64.h>

using namespace libsnark;

void generate_keys(std::string file_path) {
    default_r1cs_ppzkadsnark_pp::init_public_params();
    match_r1cs<libff::Fr<snark_pp<default_r1cs_ppzkadsnark_pp>>> r1cs = generate_match_r1cs<libff::Fr<snark_pp<default_r1cs_ppzkadsnark_pp>>>();
    r1cs_ppzkadsnark_auth_keys<default_r1cs_ppzkadsnark_pp> auth_keys = r1cs_ppzkadsnark_auth_generator<default_r1cs_ppzkadsnark_pp>();
    r1cs_ppzkadsnark_keypair<default_r1cs_ppzkadsnark_pp> keypair = r1cs_ppzkadsnark_generator<default_r1cs_ppzkadsnark_pp>(r1cs.constraint_system,auth_keys.pap);
    r1cs_ppzkadsnark_processed_verification_key<default_r1cs_ppzkadsnark_pp> pvk = r1cs_ppzkadsnark_verifier_process_vk<default_r1cs_ppzkadsnark_pp>(keypair.vk);
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

}

int main(int argc, const char * argv[]) {

    if (argc < 3) {
        std::cerr <<  "Invalid catll. hbzksnark [-g, -p, -v] [options]" << std::endl;
        return -1;
    }
    else if (strcmp(argv[1], "-g") == 0) {
        if (argc > 3) {
            std::cerr << "Invalid catll. hbzksnark -g file_path" << std::endl;
            return -1;
        }
        else {
            std::string file_path(argv[2]);
            generate_keys(file_path);
        }
    }
    else if (strcmp(argv[1], "-p") == 0) {

    }
    else if (strcmp(argv[1], "-v") == 0) {

    }
    else {
        std::cerr <<  "No command match. Correct input and try again" << std::endl;
        return -1;
    }

    return 0;
}

