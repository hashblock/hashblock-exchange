# Convenient sawtooth scripts

A collection of bash shell scripts (placed somewhere in your path) that:

script | description
-------| -----------
stup   | runs the docker-compose for the sawtooth images
stdwn  | after Ctrl-C, shuts down the sawtooth environment
stshell | puts you into sawtooth-default-shell with bash
strest  | puts you into sawtooth-rest-api-default with bash
stval | puts you into sawtooth-validator-default with bash
stset | puts you into sawtooth-settings-default with bash
stintk | puts you into sawtooth-intkey-tp-python-default with bash

`sawtooth-default.yaml` is used by `stup` and `stdwn`

