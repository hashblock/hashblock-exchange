# Minimum version
# Run: rm -R build && mkdir build && cd build && cmake .. && make

cmake_minimum_required(VERSION 3.5.1)

# Our project
project (hbzkproc)

include(CheckIncludeFile)
include(CheckSymbolExists)

# Pathing information
include_directories(/usr/local/include
	/usr/include/x86_64-linux-gnu
	/root/zcash/src
	/root/zcash/src/secp256k1/include
	/root/zcash/depends/x86_64-unknown-linux-gnu/include)

set(CMAKE_CXX_COMPILER "/usr/bin/g++")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -std=c++11 -Wextra -Wfatal-errors -O2")
set(SOURCES src/hbzkproc.cpp)

# Link settings
find_library(HB_LIBUNIVALUE NAMES univalue PATHS /root/zcash/src/univalue/.libs)
find_library(HB_LIBMEMENV NAMES memenv PATHS /root/zcash/src/leveldb)
find_library(HB_LIBSNARK NAMES snark PATHS /root/zcash/src/snark)
find_library(HB_LIBBITCOIN_CRYPTO NAMES bitcoin_crypto PATHS /root/zcash/src/crypto)
find_library(HB_LIBSECP256K1 NAMES secp256k1 PATHS /root/zcash/src/secp256k1/.libs)
find_library(HB_LIBBITCOIN_UTIL NAMES bitcoin_util PATHS /root/zcash/src)
find_library(HB_LIBBITCOIN_CLI NAMES bitcoin_cli PATHS /root/zcash/src)
find_library(HB_LIBZCASH NAMES zcash PATHS /root/zcash/src)
find_library(HB_LIBRUSTZCASH NAMES rustzcash PATHS /root/zcash/depends/x86_64-unknown-linux-gnu/lib)
find_library(HB_LIBBOOST NAMES boost_system PATHS /root/zcash/depends/x86_64-unknown-linux-gnu/lib)

add_executable(hbzkproc ${SOURCES})
CHECK_INCLUDE_FILE(endian.h HAVE_ENDIAN_H)
CHECK_SYMBOL_EXISTS(htobe16 "endian.h" HAVE_DECL_HTOBE16)
CHECK_SYMBOL_EXISTS(bswap_16 "byteswap.h" HAVE_DECL_BSWAP_16)
target_compile_definitions(hbzkproc PUBLIC HAVE_ENDIAN_H HAVE_DECL_HTOBE16 HAVE_DECL_BSWAP_16)

target_link_libraries(hbzkproc
	-rdynamic
	${HB_LIBUNIVALUE}
	${HB_LIBMEMENV}
	${HB_LIBSNARK}
	${HB_LIBBITCOIN_CRYPTO}
	${HB_LIBSECP256K1}
	${HB_LIBBITCOIN_UTIL}
	${HB_LIBBITCOIN_CLI}
	${HB_ZCASH}
	${HB_LIBRUSTZCASH}
	${HB_LIBBOOST})
