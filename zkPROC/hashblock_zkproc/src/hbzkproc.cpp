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

#include <string>
#include <array>
#include <iostream>
#include <iomanip>

// Dependencies
#include <endian.h>
#include <config/bitcoin-config.h>
#include <uint256.h>
#include <sodium.h>
#include <secp256k1.h>

//  ZCash functions
#include <zcash/Zcash.h>
#include <zcash/Address.hpp>
#include <zcash/Note.hpp>
#include <transaction.h>
#include <zcash/IncrementalMerkleTree.hpp>
#include "streams.h"
#include <utilstrencodings.h>
#include <librustzcash.h>

using namespace std;
using namespace libzcash;

typedef IncrementalMerkleTree<SAPLING_INCREMENTAL_MERKLE_TREE_DEPTH, libzcash::PedersenHash> SaplingMerkleTree;
static const int PROTOCOL_VERSION = 170006;

// Utilities

template <class T, size_t N>
ostream& operator<<(ostream& o, const array<T, N>& arr)
{
    copy(arr.cbegin(), arr.cend(), ostream_iterator<T>(o, " "));
    return o;
}

uint64_t charToUint(const char *num) {
    char *end;
    uint64_t result;
    errno = 0;
    result = strtoull(num, &end, 10);
    if (result == 0 && end == num) {
        /* str was not a number */
    } else if (result == ULLONG_MAX && errno) {
        /* the value of str does not fit in unsigned long long */
    } else if (*end) {
        /* str began with a number but has junk left over at the end */
    }
    return result;
}

uint64_t hexToUint(const char *hex) {
    char *end;
    uint64_t result;
    errno = 0;
    result = strtoull(hex, &end, 16);
    if (result == 0 && end == hex) {
        /* str was not a number */
    } else if (result == ULLONG_MAX && errno) {
        cout << hex << " larger than uint64_t capacity" << endl;
    } else if (*end) {
        /* str began with a number but has junk left over at the end */
    }
    return result;
}

bool verifyPrivateKey(const std::string& private_str) {
    secp256k1_context* ctx = secp256k1_context_create(SECP256K1_CONTEXT_SIGN | SECP256K1_CONTEXT_VERIFY);
    int sk_verify = secp256k1_ec_seckey_verify(ctx, (const unsigned char*) private_str.c_str());
    return sk_verify == 1;
}

std::string hexKeyToString(const char *key) {
    vector<unsigned char> k = ParseHex(key);
    std::string result(k.begin(), k.end());
    return result;
}

std::string valueNoteCommitment(const SaplingPaymentAddress& spa, uint64_t value) {
    auto note = SaplingNote(spa, value);
    return (*(note.cm())).GetHex();
}

string treeStats(const uint256& v, const SaplingMerkleTree& tree) {
    cout << endl;
    cout << "Comm = " << v.GetHex() << endl;
    cout << "Root = " << tree.root().GetHex() << endl;
    cout << "Size = " << tree.size() << endl;
    cout << "Witness Post = " << tree.witness().position() << endl;
    cout << "Witness Root = " << tree.witness().root().GetHex() << endl;
    cout << "Witness Elem = " << tree.witness().element().GetHex() << endl;
    CDataStream ss_out(SER_NETWORK, PROTOCOL_VERSION);
    ss_out << tree;
    string tree_hex = HexStr(ss_out.begin(), ss_out.end());
    cout << "Serialized hex = " << tree_hex << endl;
    return tree_hex;
}

/*
    Add commitments to current tree, returns
    For each commitment: position,commitment <sp>
    followed by the new serialized tree, so:
    x,value<sp>y,unit<sp>z,asset<sp> tree
*/

int commitmentToTree(const char* tree, const char *value, const char *unit, const char *asset) {
    SaplingMerkleTree tree_new;
    uint256 u_v = uint256S(value);
    uint256 u_u = uint256S(unit);
    uint256 u_a = uint256S(asset);
    CDataStream ss_in(
        ParseHex(tree),
        SER_NETWORK, PROTOCOL_VERSION);
    ss_in >> tree_new;
    tree_new.append(u_v);
    CDataStream vwpath(SER_NETWORK, PROTOCOL_VERSION);
    vwpath << tree_new.witness().path();
    string v_path = HexStr(vwpath.begin(), vwpath.end());
    
    boost::filesystem::path sapling_spend = "/root/.zcash-params/sapling-spend.params";
    boost::filesystem::path sapling_output = "/root/.zcash-params/sapling-output.params";
    boost::filesystem::path sprout_groth16 = "/root/.zcash-params/sprout-groth16.params";

    std::string sapling_spend_str = sapling_spend.string();
    std::string sapling_output_str = sapling_output.string();
    std::string sprout_groth16_str = sprout_groth16.string();

    librustzcash_init_zksnark_params(
        sapling_spend_str.c_str(),
        "8270785a1a0d0bc77196f000ee6d221c9c9894f55307bd9357c3f0105d31ca63991ab91324160d8f53e2bbd3c2633a6eb8bdf5205d822e7f3f73edac51b2b70c",
        sapling_output_str.c_str(),
        "657e3d38dbb5cb5e7dd2970e8b03d69b4787dd907285b5a7f0790dcc8072f60bf593b32cc2d1c030e00ff5ae64bf84c5c3beb84ddc841d48264b4a171744d028",
        sprout_groth16_str.c_str(),
        "e9b238411bd6c0ec4791e9d04245ec350c9c5744f5610dfcce4365d5ca49dfefd5054e371842b3f88fa1b9d7e8e075249b3ebabd167fa8b0f3161292d36c180a"
    );

    auto ctx = librustzcash_sapling_proving_ctx_init();
    SaplingSpendingKey spendingKey(uint256S("59c193cb554c7100dd6c1f38b5c77f028146be29373ee9e503bfcc81e70d1dd1"));
    // auto nf = spend.note.nullifier(
    //         spendingKey.full_viewing_key(), tree_new.witness().position());
    std::vector<unsigned char> witness(vwpath.begin(), vwpath.end());

    const unsigned char alpha[32] = {
                0xf3, 0x44, 0xec, 0x38, 0x0f, 0xe1, 0x27, 0x3e, 0x30, 0x98, 0xc2, 0x58, 0x8c, 0x5d,
                0x3a, 0x79, 0x1f, 0xd7, 0xba, 0x95, 0x80, 0x32, 0x76, 0x07, 0x77, 0xfd, 0x0e, 0xfa,
                0x8e, 0xf1, 0x16, 0x20
            };
    SpendDescription sdesc;
    unsigned char f_r[32];
    librustzcash_sapling_generate_r(f_r);
    auto result = librustzcash_sapling_spend_proof(
                ctx,
                spendingKey.full_viewing_key().ak.begin(),
                spendingKey.expanded_spending_key().nsk.begin(),
                spendingKey.default_address().d.data(),
                //uint256S("00b0b92c4c2467605caad7ed24c1952caf3f15c70a2bf22018649e503607c371").begin(),  //r
                f_r,
                uint256S((const char*)alpha).begin(),              //spend.alpha.begin(),
                5,                          //spend.note.value(),
                tree_new.root().begin(),    //spend.anchor.begin(),
                witness.data(),
                sdesc.cv.begin(),
                sdesc.rk.begin(),
                sdesc.zkproof.data());

                cerr << "....................................................\n";
                cerr << result << "\n";
                cerr << sdesc.zkproof.size() << "\n";
                cerr << "....................................................\n";


    librustzcash_sapling_proving_ctx_free(ctx);

    cerr << v_path << ',' << tree_new.witness().position() << ',' << value << ' ';
    tree_new.append(u_u);
    cerr << tree_new.witness().position() << ',' << unit << ' ';
    tree_new.append(u_a);
    cerr << tree_new.witness().position()  << ',' << asset<< ' ';
    CDataStream ss_out(SER_NETWORK, PROTOCOL_VERSION);
    ss_out << tree_new;
    string tree_hex = HexStr(ss_out.begin(), ss_out.end());
    cerr << tree_hex;
    return 0;
}

/*
    Generates commitments for value, unit, asset
    returns value_commitment<sp>unit_commitment<sp>asset_commitment
*/

int generateCommitments(const std::string& secret_key, uint64_t value, uint64_t unit, uint64_t asset) {
    if( verifyPrivateKey(secret_key) ) {
        SaplingSpendingKey spendingKey(uint256S(secret_key));
        SaplingPaymentAddress spa = spendingKey.default_address();
        uint256 valueCommitment = *(SaplingNote(spa, value).cm());
        //output r from note because we need it
        SaplingNote vnote(spa, unit);
        
        uint256 nf = *(vnote.nullifier(spendingKey.expanded_spending_key().full_viewing_key(), 0));

        uint256 unitCommitment = *(SaplingNote(spa, unit).cm());
        uint256 assetCommitment = *(SaplingNote(spa, asset).cm());
        cerr << "******" << nf.GetHex() << "*****" << "----------" << vnote.r.GetHex() << "----------" << valueCommitment.GetHex() << ' '
            << unitCommitment.GetHex() << ' '
            << assetCommitment.GetHex();
        return 0;
    }
    else {
        return 2;
    }

}

/*
    DEAD CODE FOR REFERENCING
    Spits commitments and trees
*/

int mintQuantity(const std::string& secret_key, const char* tree, uint64_t value, uint64_t unit, uint64_t asset) {
    cout << endl;

    if( verifyPrivateKey(secret_key) ) {
        SaplingSpendingKey spendingKey(uint256S(secret_key));
        SaplingPaymentAddress spa = spendingKey.default_address();
        uint256 valueCommitment = *(SaplingNote(spa, value).cm());
        uint256 unitCommitment = *(SaplingNote(spa, unit).cm());
        uint256 assetCommitment = *(SaplingNote(spa, asset).cm());

        // cout << "Value: " << valueCommitment.GetHex() << " cm: " << cV << endl;
        // cout << "Unit: " << unitCommitment.GetHex() << " cm: " << cU << endl;
        // cout << "Asset: " << assetCommitment.GetHex() << " cm: " << cA << endl;

        // Need to populate tree from inbound

        SaplingMerkleTree tree_new;
        CDataStream ss_in(
            ParseHex(tree),
            SER_NETWORK, PROTOCOL_VERSION);
        ss_in >> tree_new;
        tree_new.append(valueCommitment);
        treeStats(valueCommitment, tree_new);
        tree_new.append(unitCommitment);
        treeStats(unitCommitment, tree_new);
        tree_new.append(assetCommitment);
        string final_tree_string = treeStats(assetCommitment, tree_new);

        // TBD
        // auto cV_anchor = tree_new.root();
        // auto cV_witness = tree_new.witness();

        cout << "Final tree hex = " << final_tree_string << endl << endl;

        cout << "Outputs " << endl;
        cerr << final_tree_string << ' '
            << valueCommitment.GetHex() << ' '
            << unitCommitment.GetHex() << ' '
            << assetCommitment.GetHex();
        return 0;
    }
    else {
        cout << "Secret failure" << endl;
        return 2;
    }
}

int main( int argc , char *argv[]) {
    int result=1;
    cout << endl;
    if ( argc < 2 )
        return result;
    else {
        /*
        ./hbzkproc -qc 59c193cb554c7100dd6c1f38b5c77f028146be29373ee9e503bfcc81e70d1dd1 5 0000000000000000000000000000fcc1cb47ddc86179 0000000000000000000000000000eb50c37a09093a83
        */
        if (strcmp(argv[1], "-qc") == 0) {
            if (argc < 5) {
                cerr << "hbzkproc -qc secret value unit asset" << endl;
                return result;
            }
            else {
                return generateCommitments(
                    hexKeyToString(argv[2]),
                    charToUint(argv[3]),
                    hexToUint(argv[4]),
                    hexToUint(argv[5]));
            }
        }
        /*
        ./hbzkproc -ctm 0000000000000000000000000000000000000000000000000000000000000000 3d5a2ea8fd4fedde0204895ab753867cbf9953047f33b74fbf246e7fcd5a73de 065647602db565583d5f717dc24000209975c24dfedcf2ef0c97812067596f4e 3263e9ab0e2ecc9362ae8f292d7e438058999c461927fa2082fb73b1eb8c23b9
        */
        else if (strcmp(argv[1], "-ctm") == 0) {
            if (argc < 6) {
                cerr << "hbzkproc -ctm tree value unit asset" << endl;
                return result;
            }
            else {
                return commitmentToTree(argv[2], argv[3], argv[4], argv[5]);
            }
        }
        else {
            cerr << "hbzkproc [-qc] args...";
            return result;
        }
    }

	return result;
}


/*    Dead (potentially resurected) code

    // Verifying private key

    // Public key from private
        int to_pub;
        unsigned char ser_33[33];
        size_t iser_33 = 33;
        unsigned char ser_66[66];
        size_t iser_66 = 66;

        uint256 pub_key;
        secp256k1_pubkey pubkey;

        to_pub = secp256k1_ec_pubkey_create(ctx, &pubkey, priv_k.data());
        cout << "pubkey create result " << to_pub << endl;
        secp256k1_ec_pubkey_serialize(ctx, ser_33, &iser_33, &pubkey, SECP256K1_EC_COMPRESSED);
        secp256k1_ec_pubkey_serialize(ctx, ser_66, &iser_66, &pubkey, SECP256K1_EC_UNCOMPRESSED);
        cout << "i33 = " << iser_33 << " i66 = " << iser_66 << endl;
        auto from_array_33 = make_hex_string(begin(ser_33), std::end(ser_33));
        auto from_array_66 = make_hex_string(begin(ser_66), std::end(ser_66));
        cout << "ser33 = " << from_array_33 << endl;
        cout << "ser66 = " << from_array_66 << endl;
        uint256 pub_256 = uint256S((const char *) pubkey.data);
        cout << "pub_256 = " << pub_256.GetHex() << endl;

        //std::array<uint8_t, 11> d{0xf1, 0x9d, 0x9b, 0x79, 0x7e, 0x39, 0xf3, 0x37, 0x44, 0x58, 0x39};
        std::array<uint8_t, 11> d;
        char v_d[11];
        randombytes_buf(v_d, 11);
        for (int i = 0; i < 11; i++)
        {
            d[i] = uint8_t(v_d[i]);
        }


    auto fvk = spendingKey.full_viewing_key();

    auto ivk = fvk.in_viewing_key();

    //SaplingPaymentAddress spa = *ivk.address(d);
    cout << "Fetching pk_d" << endl;
    auto pk_d = spa.pk_d;
    cout << "Key from address = " << pk_d.GetHex() << endl;

    char v_r_c[32];
    randombytes_buf(v_r_c, 32);
    std::vector<uint8_t> v_r;
    for (int i = 0; i < 32; i++)
    {
        if(i<23) // I do not know why this cannot be 32 yet
        {
        v_r.push_back(uint8_t(v_r_c[i]));
        }
        else
        {
            v_r.push_back(0);
        }

    }
    uint256 r(v_r);
    cout << "Creating note" << endl;
    cout << "in v = " << v << endl;
    cout << "in r = " << r.GetHex() << endl;
    auto note = SaplingNote(d, pk_d, v, r);

*/
