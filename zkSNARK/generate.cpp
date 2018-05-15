#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>

#include <libff/common/profiling.hpp>

#include <libsnark/common/default_types/r1cs_ppzkadsnark_pp.hpp>
#include <hashblock_r1cs.hpp>

using namespace libsnark;

void generate()
{
    default_r1cs_ppzkadsnark_pp::init_public_params();
    libff::start_profiling();

    libff::enter_block("Generate Hashblock R1CS");
    hashblock_r1cs<libff::Fr<snark_pp<default_r1cs_ppzkadsnark_pp>>> r1cs =
        generate_hashblock_r1cs<libff::Fr<snark_pp<default_r1cs_ppzkadsnark_pp>>>();
    libff::leave_block("Generate Hashblock R1CS");

    libff::enter_block("Call to hashblock_r1cs_keys");

    r1cs_ppzkadsnark_auth_keys<ppT> auth_keys = r1cs_ppzkadsnark_auth_generator<ppT>();

    libff::print_header("Hashblock R1CS ppzkADSNARK Generator");
    r1cs_ppzkadsnark_keypair<ppT> keypair = r1cs_ppzkadsnark_generator<ppT>(r1cs.constraint_system,auth_keys.pap);
    printf("\n"); libff::print_indent(); libff::print_mem("after generator");

    libff::print_header("Preprocess verification key");
    r1cs_ppzkadsnark_processed_verification_key<ppT> pvk = r1cs_ppzkadsnark_verifier_process_vk<ppT>(keypair.vk);

    libff::enter_block("Write encoded keys");
    std::stringstream pkss;
    std::stringstream vkss;
    pkss << keypair.pk ;
    std::string spk = pkss.str();
    std::string encoded_spk = base64_encode(reinterpret_cast<const unsigned char*>(spk.c_str()), spk.length());
    vkss << keypair.vk;
    std::string svk = vkss.str();    
    std::string encoded_svk = base64_encode(reinterpret_cast<const unsigned char*>(svk.c_str()), svk.length());

    std::cout << "pk: " << encoded_spk << std::endl;
    std::cout << "vk: " << encoded_svk << std::endl;

    std::ofstream file_pk("zkSNARK.pk");
    std::ofstream file_vk("zkSNARK.vk");

    file_pk << encoded_spk;
    file_vk << encoded_svk;

    libff::leave_block("Write encoded keys");

    libff::leave_block("Call to hashblock_r1cs_keys");
}

