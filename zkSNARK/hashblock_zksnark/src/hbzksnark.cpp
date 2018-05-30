#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>
#include <fstream>
#include <iostream>

#include <libff/common/profiling.hpp>

#include <libsnark/common/default_types/r1cs_ppzksnark_pp.hpp>
#include <libsnark/zk_proof_systems/ppzksnark/r1cs_ppzksnark/r1cs_ppzksnark.hpp>
#include <libsnark/zk_proof_systems/ppzksnark/r1cs_ppzksnark/hashblock/match_r1cs.hpp>
#include <libsnark/zk_proof_systems/ppzksnark/r1cs_ppzksnark/hashblock/base64.h>

using namespace libsnark;

match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> _r1cs;
r1cs_ppzksnark_proving_key<default_r1cs_ppzksnark_pp> _pk;
r1cs_ppzksnark_verification_key<default_r1cs_ppzksnark_pp> _vk;
r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp> _proof;

void generate_keys(std::string file_path) {
    default_r1cs_ppzksnark_pp::init_public_params();
    const int _i_0 = 5;
    const int _n_0 = 2;
    const int _d_0 = 1;
    const int _r_0 = 10;
    const int _i_1 = 2;
    const int _n_1 = 5;
    const int _d_1 = 2;
    const int _r_1 = 5;
    const int _i_2 = 3;
    const int _n_2 = 7;
    const int _d_2 = 3;
    const int _r_2 = 7;

    match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> r1cs = generate_match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>>(
             _i_0, _n_0, _d_0, _r_0,
            _i_1, _n_1, _d_1, _r_1,
            _i_2, _n_2, _d_2, _r_2);
    _r1cs = r1cs;
    
    r1cs_ppzksnark_keypair<default_r1cs_ppzksnark_pp> keypair = r1cs_ppzksnark_generator<default_r1cs_ppzksnark_pp>(r1cs.constraint_system);
    _pk = keypair.pk;
    _vk = keypair.vk;

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

void generate_keys_test() {
    default_r1cs_ppzksnark_pp::init_public_params();
    match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> r1cs = generate_match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>>();
    r1cs_ppzksnark_keypair<default_r1cs_ppzksnark_pp> keypair = r1cs_ppzksnark_generator<default_r1cs_ppzksnark_pp>(r1cs.constraint_system);

    std::stringstream pkss;
    std::stringstream vkss;
    pkss << keypair.pk ;
    std::string spk = pkss.str();
    vkss << keypair.vk;
    std::string svk = vkss.str();

    const int _i_0 = 5;
    const int _n_0 = 2;
    const int _d_0 = 1;
    const int _r_0 = 10;
    const int _i_1 = 2;
    const int _n_1 = 5;
    const int _d_1 = 2;
    const int _r_1 = 5;
    const int _i_2 = 3;
    const int _n_2 = 7;
    const int _d_2 = 3;
    const int _r_2 = 7;

    match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>> r1cs_1 = generate_match_r1cs<libff::Fr<default_r1cs_ppzksnark_pp>>(
             _i_0, _n_0, _d_0, _r_0,
            _i_1, _n_1, _d_1, _r_1,
            _i_2, _n_2, _d_2, _r_2);
    r1cs_ppzksnark_keypair<default_r1cs_ppzksnark_pp> keypair_1 = r1cs_ppzksnark_generator<default_r1cs_ppzksnark_pp>(r1cs_1.constraint_system);

    std::stringstream pkss_1;
    std::stringstream vkss_1;
    pkss_1 << keypair_1.pk ;
    std::string spk_1 = pkss_1.str();
    vkss_1 << keypair_1.vk;
    std::string svk_1 = vkss_1.str();

    if(spk.compare(spk_1) !=0 )
    {
        std::cout << "pk NOT equal" << std::endl;
    }
    else
    {
        std::cout << "pk ARE equal" << std::endl;
    }

    if(svk.compare(svk_1) != 0)
    {
        std::cout << "vk NOT equal" << std::endl;
    }
    else
    {
        std::cout << "vk ARE equal" << std::endl;
    }

}

void proove() {
    default_r1cs_ppzksnark_pp::init_public_params();
    r1cs_ppzksnark_proof<default_r1cs_ppzksnark_pp> proof = r1cs_ppzksnark_prover<default_r1cs_ppzksnark_pp>(_pk, _r1cs.primary_input, _r1cs.auxiliary_input);
    _proof = proof;
}

void verify()
{
    default_r1cs_ppzksnark_pp::init_public_params();
    const bool ans = r1cs_ppzksnark_verifier_strong_IC<default_r1cs_ppzksnark_pp>(_vk, _r1cs.primary_input, _proof);
    printf("\n"); libff::print_indent(); libff::print_mem("after verifier");
    printf("* The verification result is: %s\n", (ans ? "PASS" : "FAIL"));
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

            //TODO: Remove the following lines
            proove();
            verify();
        }
    }
    else if (strcmp(argv[1], "-p") == 0) {
        proove();
    }
    else if (strcmp(argv[1], "-v") == 0) {
        verify();
    }
    else if (strcmp(argv[1], "-t") == 0) {
        generate_keys_test();
    }
    else {
        std::cerr <<  "No command match. Correct input and try again" << std::endl;
        return -1;
    }

    return 0;
}

