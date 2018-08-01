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
find_library(HB_ZCASH NAMES zcashd,zcash_cli)

add_executable(hbzkproc ${SOURCES})
target_link_libraries(hbzkproc
	-rdynamic
	-std=c99 -Wall -Wextra -Wfatal-errors
	${HB_ZCASH})
