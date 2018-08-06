#include <config/bitcoin-config.h>
#include <endian.h>
#include "uint256.h"
#include "zcash/Zcash.h"
#include "zcash/Address.hpp"
#include "zcash/Note.hpp"
#include <array>
#include <iostream>
#include <sstream>
#include "secp256k1.h"
#include "sodium.h"

using namespace std;
using namespace libzcash;

int main( int c , char *argv[]) {

    uint64_t v = 13;
    uint64_t note_pos = 0;

    unsigned char seckey[32];
    randombytes_buf(seckey, 32);

    secp256k1_context* ctx = secp256k1_context_create(SECP256K1_CONTEXT_SIGN);
    int sk_verify = secp256k1_ec_seckey_verify(ctx, seckey);

    if(sk_verify > 0)
    {
        cout << "Verified secret key.\n";
    }

    //std::array<uint8_t, 11> d{0xf1, 0x9d, 0x9b, 0x79, 0x7e, 0x39, 0xf3, 0x37, 0x44, 0x58, 0x39};
    std::array<uint8_t, 11> d;
    char v_d[11];
    randombytes_buf(v_d, 11);
    for (int i = 0; i < 11; i++)
    {
        d[i] = uint8_t(v_d[i]);
    }

    uint256 sk_256 = uint256S(reinterpret_cast<const char*>(seckey));
    SaplingSpendingKey spendingKey(sk_256);
    auto fvk = spendingKey.full_viewing_key();
    auto ivk = fvk.in_viewing_key();
    auto address = *ivk.address(d);
    auto pk_d = address.pk_d;

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

    auto note = SaplingNote(d, pk_d, v, r);
    uint256 u = *(note.cm());
    cout << "Note comitment: " << u.GetHex() << "\n";

    //auto nullifier = note.nullifier(spendingKey.full_viewing_key(), note_pos);

	return 0;
}