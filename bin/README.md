# hashblock-exchange/bin

This directory contains various build, test and execution scripts.

## Contents

name | description
-----|------------
build_all | builds local containers helpful for hashblock-exchange development
protogen | Compiles the protobuff descriptors (in protos folder) and copies to apps and TP families
run_tests | Initiates TP family unit tests
run_docker_test | Executes TP family unit tests
asset-tp | Called within the asset-TP container to start the asset transaction processor
unit-tp | Called within the unit-TP container to start the unit transaction processor
exchange-tp | Called within the exchange-TP container to start the exchange transaction processor
setting-tp | Called within the setting-TP container to start the setting transaction processor
