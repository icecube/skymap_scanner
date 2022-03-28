#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo $SCRIPT_DIR

python $SCRIPT_DIR/perform_scan.py -r "ssh submitter" -n 30 ic191001a_sim -c $SCRIPT_DIR/output_skymap_scanner --event $SCRIPT_DIR/ic191001a_sim.i3 --gcd_dir $SCRIPT_DIR
