# Minimum version
cmake_minimum_required(VERSION 3.5.1)

# Our project
project (hbzksnark)

# Pathing information

include_directories(/usr/local/include /root/libsnark /root/libsnark/depends/libff /root/libsnark/depends/libfqfft /root/libsnark/depends/libff/libff/.. include -isystem /usr/include/x86_64-linux-gnu)

set(SOURCES src/hbzksnark.cpp src/base64.cpp src/hbutils.cpp)

# Build settings
set(CMAKE_CXX_FLAGS "-Wall -std=c++11 -Wall -Wextra -Wfatal-errors -O2")
add_definitions(-DCURVE_BN128 -DBINARY_OUTPUT -DWITH_PROCPS=OFF -DBN_SUPPORT_SNARK=1 -DMONTGOMERY_OUTPUT -DUSE_ASM -DNDEBUG)

# Link settings
find_library(HB_GMP NAMES gmp)
find_library(HB_GMPXX NAMES gmpxx)
find_library(HB_CRYPTO NAMES crypto)
find_library(HB_SNARK NAMES snark)
find_library(HB_FF NAMES ff)
find_library(HB_ZM NAMES zm PATHS /root/libsnark/build/depends/)
find_library(HB_SC snark_supercop /root/libsnark/build/depends/)

add_executable(hbzksnark ${SOURCES})
target_link_libraries(hbzksnark
	-rdynamic
	-std=c++11 -Wall -Wextra -Wfatal-errors
	${HB_GMP}
	${HB_GMPXX}
	${HB_SNARK}
	${HB_FF}
	${HB_ZM}
	${HB_CRYPTO})
