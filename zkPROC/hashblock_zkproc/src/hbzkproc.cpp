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

#include <array>
#include <iostream>
#include <sstream>

//  ZCash functions
#include <config/bitcoin-config.h>
#include <endian.h>
#include <uint256.h>
#include <zcash/Zcash.h>
#include <zcash/Address.hpp>
#include <zcash/Note.hpp>
#include <sodium.h>
#include <secp256k1.h>

//  Our functions
#include "base64.h"

using namespace std;
using namespace libzcash;

template <class T, size_t N>
ostream& operator<<(ostream& o, const array<T, N>& arr)
{
    copy(arr.cbegin(), arr.cend(), ostream_iterator<T>(o, " "));
    return o;
}

vector<unsigned char> HexToBytes(const string& hex) {
  vector<unsigned char> bytes;

  for (unsigned int i = 0; i < hex.length(); i += 2) {
    string byteString = hex.substr(i, 2);
    unsigned char byte = (unsigned char) strtol(byteString.c_str(), NULL, 16);
    bytes.push_back(byte);
  }

  return bytes;
}

int main( int c , char *argv[]) {

    uint64_t v = 13;
    uint64_t note_pos = 0;

    string private_key = "59c193cb554c7100dd6c1f38b5c77f028146be29373ee9e503bfcc81e70d1dd1";
    vector<unsigned char> priv_k = HexToBytes(private_key);

    secp256k1_context* ctx = secp256k1_context_create(SECP256K1_CONTEXT_SIGN);
    int sk_verify = secp256k1_ec_seckey_verify(ctx, priv_k.data());

    if(sk_verify == 1)
    {
        int to_pub;
        uint256 pub_key;

        cout << "Verified secret key" << endl;
        // unsigned char *cpublic_key = (unsigned char *) "02d3543108be0b401184a574e17d271124679391fdff1f73a2f93ea99f3bea3b53";
        // secp256k1_pubkey pubkey;
        // to_pub = secp256k1_ec_pubkey_parse(ctx, &pubkey, cpublic_key, 33);
        // if(to_pub == 1) {
        //     pub_key = uint256S(reinterpret_cast<const char*>(pubkey.data));
        //     cout << "Pubkey (as uint256) = " << pub_key.GetHex() << endl;
        // }
    }

    //std::array<uint8_t, 11> d{0xf1, 0x9d, 0x9b, 0x79, 0x7e, 0x39, 0xf3, 0x37, 0x44, 0x58, 0x39};
    std::array<uint8_t, 11> d;
    char v_d[11];
    randombytes_buf(v_d, 11);
    for (int i = 0; i < 11; i++)
    {
        d[i] = uint8_t(v_d[i]);
    }

    SaplingSpendingKey spendingKey(uint256S(reinterpret_cast<const char*>(priv_k.data())));

    auto fvk = spendingKey.full_viewing_key();
    auto ivk = fvk.in_viewing_key();
    cout << "Fetching address" << endl;
    SaplingPaymentAddress spa = *ivk.address(d);
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
    uint256 u = *(note.cm());
    cout << "Note comitment: " << u.GetHex() << endl;

    //auto nullifier = note.nullifier(spendingKey.full_viewing_key(), note_pos);

	return 0;
}