# hashblock-exchange/bin

This script directory is 'pathed' into the various containers of hashblock-exchange.

## Contents

name | description
-----|------------
build_all | builds local containers helpful for hashblock-exchange development
build_distro | builds production ready containers for testing. Actual distro built on Docker Hub
protogen | Compiles the protobuff descriptors (in protos folder) and copies to apps and TP families
run_tests | Initiates TP family unit tests
run_docker_test | Executes TP family unit tests
asset-tp | Called within the asset-processor container to start the asset transaction processor
match-tp | Called within the asset-processor container to start the match transaction processor
setting-tp | Called within the asset-processor container to start the setting transaction processor
