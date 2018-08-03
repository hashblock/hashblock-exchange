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
find_library(HB_LIBUNIVALUE NAMES libunivalue)
find_library(HB_LIBMEMENV NAMES libmemenv)
find_library(HB_LIBSNARK NAMES libsnark PATHS /root/zcash/src/snark)
find_library(HB_LIBBITCOIN_CRYPTO NAMES libbitcoin_crypto)
find_library(HB_LIBSECP256K1 NAMES libsecp256k1)
find_library(HB_LIBBITCOIN_UTIL NAMES libbitcoin_util)
find_library(HB_LIBBITCOIN_CLI NAMES libbitcoin_cli)
find_library(HB_LIBZCASH NAMES libzcash)


add_executable(hbzkproc ${SOURCES})
target_link_libraries(hbzkproc
	-rdynamic
	-std=c99 -Wall -Wextra -Wfatal-errors
	${HB_LIBUNIVALUE}
	${HB_LIBMEMENV}
	${HB_LIBSNARK}
	${HB_LIBBITCOIN_CRYPTO}
	${HB_LIBSECP256K1}
	${HB_LIBBITCOIN_UTIL}
	${HB_LIBBITCOIN_CLI}
	${HB_ZCASH})
