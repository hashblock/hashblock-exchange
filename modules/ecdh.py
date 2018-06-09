#https://github.com/ludbb/secp256k1-py
#https://pypi.org/project/eciespy/

import binascii
import secp256k1

from ecies import aes_encrypt, aes_decrypt

__CONTEXTBASE__ = secp256k1.Base(ctx=None, flags=secp256k1.ALL_FLAGS)
__CTX__ = __CONTEXTBASE__.ctx

encoding='utf-8'

SK_CHURCH = '59c193cb554c7100dd6c1f38b5c77f028146be29373ee9e503bfcc81e70d1dd1'
PK_CHURCH = '02d3543108be0b401184a574e17d271124679391fdff1f73a2f93ea99f3bea3b53'
SK_TURING = 'f5109ec8e2b1bec395ca7e24e27aaf22bc0afaeef3e39314591fd488fa6805cd'
PK_TURING = '0322e2aab7bbf8f6160bdc1afb5c043f7e508b089448f2f848dccbc4c5c928b7ba'

priv_church = bytes(bytearray.fromhex(SK_CHURCH))
sk_church = secp256k1.PrivateKey(ctx=__CTX__)
sk_church.set_raw_privkey(priv_church)

raw_church=sk_church.pubkey.serialize()
pk_church=binascii.hexlify(raw_church).decode(encoding)

assert pk_church == PK_CHURCH

priv_turing = bytes(bytearray.fromhex(SK_TURING))
sk_turing = secp256k1.PrivateKey(ctx=__CTX__)
sk_turing.set_raw_privkey(priv_turing)

raw_turing=sk_turing.pubkey.serialize()
pk_turing=binascii.hexlify(raw_turing).decode(encoding)

assert pk_turing == PK_TURING

if not secp256k1.HAS_ECDH:
    print('not has')
else:
    print('has')

secret_c = sk_turing.pubkey.ecdh(sk_church.private_key)
secret_t = sk_church.pubkey.ecdh(sk_turing.private_key)

print("Church secret {}".format(secret_c))
print("Turing secret {}".format(secret_t))

if secret_c == secret_t:
    print('match')
else:
    print('no match')

data = b'this is a test'
encdata = aes_encrypt(secret_c, data)   # Encrypt with church
redata = aes_decrypt(secret_t, encdata) # Decrypt with turing
print("Encrypted {}".format(encdata))
print("{}".format(redata))
