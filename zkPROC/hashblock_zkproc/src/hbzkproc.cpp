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

vector<unsigned char> HexToBytes(const string& hex) {
  vector<unsigned char> bytes;

  for (unsigned int i = 0; i < hex.length(); i += 2) {
    string byteString = hex.substr(i, 2);
    unsigned char byte = (unsigned char) strtol(byteString.c_str(), NULL, 16);
    bytes.push_back(byte);
  }

  return bytes;
}

template<typename TInputIter>
string make_hex_string(TInputIter first, TInputIter last, bool use_uppercase = false, bool insert_spaces = false)
{
    ostringstream ss;
    ss << hex << setfill('0');
    if (use_uppercase)
        ss << uppercase;
    while (first != last)
    {
        ss << setw(2) << static_cast<int>(*first++);
        if (insert_spaces && first != last)
            ss << " ";
    }
    return ss.str();
}

bool verifyPrivateKey(const std::string& private_str) {
    secp256k1_context* ctx = secp256k1_context_create(SECP256K1_CONTEXT_SIGN | SECP256K1_CONTEXT_VERIFY);
    int sk_verify = secp256k1_ec_seckey_verify(ctx, (const unsigned char*) private_str.c_str());
    return sk_verify == 1;
}

std::string hexKeyToString(const char *key) {
    std::string ks(key);
    vector<unsigned char> k = HexToBytes(ks);
    std::string result(k.begin(), k.end());
    return result;
}

std::string valueNoteCommitment(const string& private_key, uint64_t value) {
    SaplingSpendingKey spendingKey(uint256S(private_key));
    auto note = SaplingNote(spendingKey.default_address(), value);
    uint256 u = *(note.cm());
    return u.GetHex();
}

int mintQuantity(const std::string& secret_key, uint64_t value, uint64_t unit, uint64_t asset) {
    cout << endl;
    if( verifyPrivateKey(secret_key) ) {
        string cV = valueNoteCommitment(secret_key, value);
        string cU = valueNoteCommitment(secret_key, unit);
        string cA = valueNoteCommitment(secret_key, asset);
        cout << "Value: " << value << " cm: " << cV << endl;
        cout << "Unit: " << unit << " cm: " << cU << endl;
        cout << "Asset: " << asset << " cm: " << cA << endl;
        return 1;
    }
    else {
        return 0;
    }
}


int main( int argc , char *argv[]) {
    int result=0;
    cout << endl;
    if ( argc < 2 )
        return result;
    else {
        /*
        ./hbzkproc -qc 59c193cb554c7100dd6c1f38b5c77f028146be29373ee9e503bfcc81e70d1dd1 5 0E77546B264D97ED79C0E8A00BF62F7C2A0F8BA6BE3D 0F2538C94209E2E2C98D319352C3630FCDA76F802E1F
        */
        if (strcmp(argv[1], "-qc") == 0) {
            if (argc < 5) {
                cout << "hbzkproc -qc secret value unit asset" << endl;
                return result;
            }
            else {
                return mintQuantity(hexKeyToString(argv[2]), charToUint(argv[3]), hexToUint(argv[4]), hexToUint(argv[5]));
            }
        }
    }
    //  Get the spending key and the full viewing key
    uint64_t note_pos = 0;

    //auto nullifier = note.nullifier(spendingKey.full_viewing_key(), note_pos);

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
