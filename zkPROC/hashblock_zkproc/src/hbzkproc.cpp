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
    // cout << "Witness Elem = " << tree.witness().element().GetHex() << endl;
    CDataStream ss_out(SER_NETWORK, PROTOCOL_VERSION);
    ss_out << tree;
    string tree_hex = HexStr(ss_out.begin(), ss_out.end());
    cout << "Serialized hex = " << tree_hex << endl;
    return tree_hex;
}

/*
    TODO: This loading of the keys is way busy so we do it once for each
    block of commitments to add to the tree and the resulting witness
*/

void initialize_parameters() {

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

}

/*
    Add commitments to current tree, returns
    For each commitment: position,commitment <sp>
    and proof
    followed by the new serialized tree, so:
    x,value<sp>y,unit<sp>z,asset<sp> tree
*/

const unsigned char alpha[32] = {
            0xf3, 0x44, 0xec, 0x38, 0x0f, 0xe1, 0x27, 0x3e, 0x30, 0x98, 0xc2, 0x58, 0x8c, 0x5d,
            0x3a, 0x79, 0x1f, 0xd7, 0xba, 0x95, 0x80, 0x32, 0x76, 0x07, 0x77, 0xfd, 0x0e, 0xfa,
            0x8e, 0xf1, 0x16, 0x20
        };


int inTreeOutProof(
    SaplingMerkleTree &tree,
    SaplingSpendingKey &spendingKey,
    const char* hexNote,
    SpendDescription &sdesc)
{

    SaplingNotePlaintext i_vnpt;
    SaplingNote v_note;

    // Rehydrate NotePlainText
    cout << "Rehydrate note" << endl;
    CDataStream ss_vin(
        ParseHex(hexNote),
        SER_NETWORK, PROTOCOL_VERSION);
    ss_vin >> i_vnpt;

    cout << "Note rehydrated" << endl;
    // Extract SaplingNote
    v_note = *(i_vnpt.note(spendingKey.expanded_spending_key().full_viewing_key().in_viewing_key()));
    cout << "Note extracted" << endl;

    // Insert commitment in tree
    uint256 commitment = *(v_note.cm());
    tree.append(commitment);
    // cout << "Commitment " << commitment.GetHex() << " in tree" << endl;
    // treeStats(commitment, tree);

    // Get witness slot
    CDataStream witness_stream(SER_NETWORK, PROTOCOL_VERSION);
    witness_stream << tree.witness().path();
    std::vector<unsigned char> witness(witness_stream.begin(), witness_stream.end());

    // Setup a context (may reuse just one as input arg to call)
    auto ctx = librustzcash_sapling_proving_ctx_init();
    cout << "Proof context created" << endl;

    cout << "Using R " << v_note.r.GetHex() << " in tree" << endl;

    // Get the proof
    auto result = librustzcash_sapling_spend_proof(
                ctx,
                //spendingKey.full_viewing_key().ak.begin(),
                spendingKey.expanded_spending_key().full_viewing_key().ak.begin(),
                spendingKey.expanded_spending_key().nsk.begin(),
                spendingKey.default_address().d.data(),
                v_note.r.begin(),
                uint256S((const char*)alpha).begin(),   //  Dummy for now
                i_vnpt.value(),                         //
                tree.root().begin(),                    //spend.anchor.begin(),
                witness.data(),
                sdesc.cv.begin(),
                sdesc.rk.begin(),
                sdesc.zkproof.data());
    // Delete context (may reuse just one as input arg to call)
    librustzcash_sapling_proving_ctx_free(ctx);
    return result;
}

int test_inTreeOutProof(
    SaplingMerkleTree &tree,
    SaplingSpendingKey &spendingKey,
    SaplingNote &v_note,
    SpendDescription &sdesc)
{

    SaplingNotePlaintext i_vnpt;

    // Insert commitment in tree
    uint256 commitment = *(v_note.cm());
    tree.append(commitment);
    cout << "Commitment " << commitment.GetHex() << " in tree" << endl;

    // Get witness slot

    CDataStream witness_stream(SER_NETWORK, PROTOCOL_VERSION);
    witness_stream << tree.witness().path();
    std::vector<unsigned char> witness(witness_stream.begin(), witness_stream.end());


    cout << "Withness byte 0 " << witness.data()[0] << " 1 " << witness.data()[1] << endl;

    // cout << "Witness path array " << witness << endl;

    // Setup a context (may reuse just one as input arg to call)
    auto ctx = librustzcash_sapling_proving_ctx_init();
    cout << "Proof context created" << endl;

    cout << "Using R " << v_note.r.GetHex() << " in tree" << endl;

    // Get the proof
    auto result = librustzcash_sapling_spend_proof(
                ctx,
                spendingKey.full_viewing_key().ak.begin(),
                // spendingKey.expanded_spending_key().full_viewing_key().ak.begin(),
                spendingKey.expanded_spending_key().nsk.begin(),
                spendingKey.default_address().d.data(),
                v_note.r.begin(),
                uint256S((const char*)alpha).begin(),   //  Dummy for now
                i_vnpt.value(),                         //
                tree.root().begin(),                    //spend.anchor.begin(),
                witness.data(),
                sdesc.cv.begin(),
                sdesc.rk.begin(),
                sdesc.zkproof.data());
    // Delete context (may reuse just one as input arg to call)
    librustzcash_sapling_proving_ctx_free(ctx);
    return result;
}

int commitmentToTree(
        const char* tree,
        const std::string& private_key,
        const char *valueNote,
        const char *unitNote,
        const char *assetNote)
{
    int result = 1;
    if( verifyPrivateKey(private_key) ) {
        SaplingSpendingKey spendingKey(uint256S(private_key));

        initialize_parameters();

        SaplingMerkleTree tree_new;

        cout << "Tree hydration" << endl;
        // Rehydrate tree
        CDataStream ss_in(
            ParseHex(tree),
            SER_NETWORK, PROTOCOL_VERSION);
        ss_in >> tree_new;

        cout << "Passed tree hydration" << endl;

        SpendDescription vdesc;
        auto vres = inTreeOutProof(tree_new, spendingKey, valueNote, vdesc);

        if (vres != 1) {
            cerr << "Unsuccesful value proof" << endl;
            return 1;
        }

        SpendDescription udesc;
        auto ures = inTreeOutProof(tree_new, spendingKey, unitNote, udesc);

        if (ures != 1) {
            cerr << "Unsuccesful unit proof" << endl;
            return 1;
        }

        SpendDescription adesc;
        auto ares = inTreeOutProof(tree_new, spendingKey, assetNote, adesc);

        if (ares != 1) {
            cerr << "Unsuccesful asset proof" << endl;
            return 1;
        }

        // Publish the tree and the proofs
        CDataStream vp_out(SER_NETWORK, PROTOCOL_VERSION);
        vp_out << vdesc;
        string vp_hex = HexStr(vp_out.begin(), vp_out.end());

        CDataStream up_out(SER_NETWORK, PROTOCOL_VERSION);
        up_out << udesc;
        string up_hex = HexStr(up_out.begin(), up_out.end());

        CDataStream ap_out(SER_NETWORK, PROTOCOL_VERSION);
        ap_out << adesc;
        string ap_hex = HexStr(ap_out.begin(), ap_out.end());

        CDataStream ss_out(SER_NETWORK, PROTOCOL_VERSION);
        ss_out << tree_new;
        string tree_hex = HexStr(ss_out.begin(), ss_out.end());
        cerr << tree_hex << ' ' << vp_hex << ' ' << up_hex << ' ' << ap_hex;
        return 0;
    }
    else {
        cerr << "Invalid key" << endl;
        return 2;
    }
    return result;
}

/*
    Generates commitments for value, unit, asset
    returns value_commitment<sp>unit_commitment<sp>asset_commitment
*/

int generateCommitments(const std::string& secret_key, uint64_t value, uint64_t unit, uint64_t asset) {
    if( verifyPrivateKey(secret_key) ) {
        SaplingSpendingKey spendingKey(uint256S(secret_key));
        SaplingPaymentAddress spa = spendingKey.default_address();

        array<unsigned char, ZC_MEMO_SIZE> memo;
        SaplingNote valueNote = SaplingNote(spa, value);
        SaplingNotePlaintext vnpt = SaplingNotePlaintext(SaplingNote(spa, value),memo);
        SaplingNotePlaintext unpt = SaplingNotePlaintext(SaplingNote(spa, unit),memo);
        SaplingNotePlaintext anpt = SaplingNotePlaintext(SaplingNote(spa, asset),memo);
        // cout << "VNPT = " << vnpt << endl;
        CDataStream val_out(SER_NETWORK, PROTOCOL_VERSION);
        val_out << vnpt;
        string valueN_hex = HexStr(val_out.begin(), val_out.end());

        CDataStream unit_out(SER_NETWORK, PROTOCOL_VERSION);
        unit_out << unpt;
        string unitN_hex = HexStr(unit_out.begin(), unit_out.end());

        CDataStream asset_out(SER_NETWORK, PROTOCOL_VERSION);
        asset_out << anpt;
        string assetN_hex = HexStr(asset_out.begin(), asset_out.end());


        // uint256 nf = *(valueNote.nullifier(spendingKey.expanded_spending_key().full_viewing_key(), 0));

        cerr << valueN_hex << ' ' << unitN_hex << ' ' << assetN_hex;

        // cout << endl;
        // cout << "Initializing parameters" << endl << endl;
        // initialize_parameters();

        // SaplingMerkleTree tree = SaplingMerkleTree();
        // SpendDescription sdesc;

        // treeStats(*(valueNote.cm()), tree);

        // cout << "Testing insert and proof" << endl;
        // // auto res = inTreeOutProof(tree, spendingKey, valueN_hex.data(), sdesc);
        // auto res = test_inTreeOutProof(tree, spendingKey, valueNote, sdesc);
        // cout << "Result = " << res << endl;

        return 0;
    }
    else {
        cout << "Invalid key" << endl;
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

        */
        else if (strcmp(argv[1], "-ctm") == 0) {
            if (argc < 7) {
                cerr << "hbzkproc -ctm tree key value unit asset" << endl;
                return result;
            }
            else {
                cout << "Input tree " << argv[2] << endl;
                return commitmentToTree(
                    argv[2],                    // Tree
                    hexKeyToString(argv[3]),    // Key
                    argv[4],                    // vNote
                    argv[5],                    // uNote
                    argv[6]);                   // aNote
            }
        }
        else {
            cerr << "hbzkproc [-qc] args...";
            return result;
        }
    }

	return result;
}

