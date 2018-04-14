# sawtooth-uom/bin

This script directory is 'pathed' into the various containers of hashblock-exchange.

## Contents

name | description
-----|------------
build_all | builds local containers helpful for hashblock-exchange development
build_distro | builds production ready containers for deploying hashblock-exchange
build_python | builds a shell for local transaction processing support
protogen | Compiles the protobuff descriptors (in protos folder) and copies to cli and processor families
run_tests | Runs the TP family unit tests
hbasset | Administrative utility for proposing and voting on hashblock-asset
hbsetting | Administrative utility for managing hashblock-asset settings as well as creating a geneis.batch file
txq | Administrative utility for creating exchange transactions
asset-tp | Called within the asset-processor container to start the asset transaction processor
match-tp | Called within the asset-processor container to start the asset transaction processor
setting-tp | Called within the asset-processor container to start the asset transaction processor
