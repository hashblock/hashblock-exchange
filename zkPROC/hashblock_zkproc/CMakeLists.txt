# Minimum version
# Run: rm -R build && mkdir build && cd build && cmake .. && make

cmake_minimum_required(VERSION 3.5.1)

# Our project
project (hbzkproc)

# Pathing information

include_directories(/usr/local/include /usr/include/x86_64-linux-gnu)

set(SOURCES src/hbzkproc.c)

# Build settings
set(CMAKE_C_FLAGS "-Wall -std=c99 -Wall -Wextra -Wfatal-errors -O2")

# Link settings
find_library(HB_LIBUNIVALUE NAMES univalue PATHS /root/zcash/src/univalue/.libs)
find_library(HB_LIBMEMENV NAMES memenv PATHS /root/zcash/src/leveldb)
find_library(HB_LIBSNARK NAMES snark PATHS /root/zcash/src/snark)
find_library(HB_LIBBITCOIN_CRYPTO NAMES bitcoin_crypto PATHS /root/zcash/src/crypto)
find_library(HB_LIBSECP256K1 NAMES secp256k1 PATHS /root/zcash/src/secp256k1/.libs)
find_library(HB_LIBBITCOIN_UTIL NAMES bitcoin_util PATHS /root/zcash/src)
find_library(HB_LIBBITCOIN_CLI NAMES bitcoin_cli PATHS /root/zcash/src)
find_library(HB_LIBZCASH NAMES zcash)


add_executable(hbzkproc ${SOURCES})
target_link_libraries(hbzkproc
	-std=c99 -Wall -Wextra -Wfatal-errors
	${HB_LIBUNIVALUE}
	${HB_LIBMEMENV}
	${HB_LIBSNARK}
	${HB_LIBBITCOIN_CRYPTO}
	${HB_LIBSECP256K1}
	${HB_LIBBITCOIN_UTIL}
	${HB_LIBBITCOIN_CLI}
	${HB_ZCASH})
