SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

/cvmfs/icecube.opensciencegrid.org/users/followup/metaprojects/combo-realtime/trunk/build/env-shell.sh python $SCRIPT_DIR/perform_scan.py -r "ssh submitter" -n 30 ic191001a_sim -c $SCRIPT_DIR/output_skymap_scanner --event $SCRIPT_DIR/ic191001a_sim.i3 --gcd_dir $SCRIPT_DIR
