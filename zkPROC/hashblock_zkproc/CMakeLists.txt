# ------------------------------------------------------------------------
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
# ------------------------------------------------------------------------

# Useful build commands
# Run: cd .. && rm -R build && mkdir build && cd build && cmake .. && make

# Minimum version
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
	/root/zcash/depends/x86_64-unknown-linux-gnu/include
	/root/zcash/depends/x86_64-unknown-linux-gnu/include/gtest)

set(CMAKE_CXX_COMPILER "/usr/bin/g++")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -std=c++11 -Wextra -Wfatal-errors -O2 -pthread")
set(SOURCES src/hbzkproc.cpp src/base64.cpp)

# Link settings
find_library(HB_LIBSSL NAMES event_openssl)
find_library(HB_LIBCRYPTO NAMES crypto)
find_library(HB_LIBUNIVALUE NAMES univalue PATHS /root/zcash/src/univalue/.libs)
find_library(HB_LIBMEMENV NAMES memenv PATHS /root/zcash/src/leveldb)
find_library(HB_LIBSNARK NAMES snark PATHS /root/zcash/src/snark)
find_library(HB_LIBSECP256K1 NAMES secp256k1 PATHS /root/zcash/src/secp256k1/.libs)
find_library(HB_LIBBITCOIN_COMMON NAMES bitcoin_common PATHS /root/zcash/src)
find_library(HB_LIBBITCOIN_UTIL NAMES bitcoin_util PATHS /root/zcash/src)
find_library(HB_LIBBITCOIN_CLI NAMES bitcoin_cli PATHS /root/zcash/src)
find_library(HB_LIBBITCOIN_CRYPTO NAMES bitcoin_crypto PATHS /root/zcash/src/crypto)
find_library(HB_LIB_SODIUM NAMES sodium PATHS /root/zcash/depends/x86_64-unknown-linux-gnu/lib)
find_library(HB_LIBZCASH NAMES zcash PATHS /root/zcash/src)
find_library(HB_LIBRUSTZCASH NAMES rustzcash PATHS /root/zcash/depends/x86_64-unknown-linux-gnu/lib)
find_library(HB_LIBBOOST NAMES boost_system PATHS /root/zcash/depends/x86_64-unknown-linux-gnu/lib)

add_executable(hbzkproc ${SOURCES})
CHECK_INCLUDE_FILE(endian.h HAVE_ENDIAN_H)
CHECK_SYMBOL_EXISTS(htobe16 "endian.h" HAVE_DECL_HTOBE16)
CHECK_SYMBOL_EXISTS(bswap_16 "byteswap.h" HAVE_DECL_BSWAP_16)
target_compile_definitions(hbzkproc PUBLIC HAVE_ENDIAN_H HAVE_DECL_HTOBE16 HAVE_DECL_BSWAP_16)

target_link_libraries(hbzkproc
	-Wl,--no-as-needed
	-ldl
	${HB_LIBZCASH}
	${HB_LIBRUSTZCASH}
	${HB_LIBUNIVALUE}
	${HB_LIBMEMENV}
	${HB_LIBSNARK}
	${HB_LIBBITCOIN_CRYPTO}
	${HB_LIBSECP256K1}
	${HB_LIBBITCOIN_UTIL}
	${HB_LIBBITCOIN_CLI}
	${HB_LIBBITCOIN_COMMON}
	${HB_LIBBOOST}
	${HB_LIB_SODIUM}
	${HB_LIBSSL}
	${HB_LIBCRYPTO})
