#!/bin/bash
# Copyright Red Hat
#
# setpaths.sh
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
#
# Set PATH and PYTHONPATH for running snapm (and optionally boom) from
# a checked out git repository in the current working directory.
#
# This script assumes that you are running it from the snapm git repository,
# and that boom-boot (if it is also present) is found at the path ../boom-boot.
#
# Run ". scripts/setpaths.sh" to enable snapm/boom in your PATH/PYTHONPATH.
if ! [[ "$PATH" =~ "$PWD/bin:" ]]; then
    export PATH="$PWD/bin:$PATH"
fi

if ! [[ "$PYTHONPATH" =~ "$PWD:" ]]; then
    if [ "$PYTHONPATH" != "" ]; then
        export PYTHONPATH="$PWD:$PYTHONPATH"
    else
        export PYTHONPATH="$PWD"
    fi
fi

if ! [[ "$PATH" =~ "$PWD/../boom-boot/bin:" ]]; then
    if [ -d "$PWD/../boom-boot" ]; then
        export PATH="$PWD/../boom-boot/bin:$PATH"
    fi
fi

if ! [[ "$PYTHONPATH" =~ "$PWD/../boom-boot:" ]]; then
    if [ -d "$PWD/../boom-boot" ]; then
        export PYTHONPATH="$PWD/../boom-boot:$PYTHONPATH"
    fi
fi
