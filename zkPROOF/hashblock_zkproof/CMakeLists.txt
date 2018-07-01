# Minimum version
cmake_minimum_required(VERSION 3.5.1)

# Our project
project (hbzkproof)

# Pathing information

include_directories(/usr/local/include /usr/include/x86_64-linux-gnu)

set(SOURCES src/hbzkproof.c)

# Build settings
set(CMAKE_C_FLAGS "-Wall -std=c99 -Wall -Wextra -Wfatal-errors -O2")

# Link settings
find_library(HB_SECP NAMES secp256k1)

add_executable(hbzkproof ${SOURCES})
target_link_libraries(hbzkproof
	-rdynamic
	-std=c99 -Wall -Wextra -Wfatal-errors
	${HB_SECP})
