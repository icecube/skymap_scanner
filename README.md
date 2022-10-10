<!--- Top of README Badges (automated) --->
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/icecube/skymap_scanner?include_prereleases)](https://github.com/icecube/skymap_scanner/) [![Lines of code](https://img.shields.io/tokei/lines/github/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/) [![GitHub issues](https://img.shields.io/github/issues/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen) 
<!--- End of README Badges (automated) --->
# skymap_scanner

Distributed likelihood scan of event directions for real-time alerts using inter-CPU queue-based message passing.

`skymap_scanner` is a python package containing two distinct applications meant to be deployed within containers (1 `skymap_scanner.server`, n `skymap_scanner.client`s), along with utility functions located in `skymap_scanner.utils`. Additional, package-independent, utility scripts are in `scripts/utils/`.

## How to Run
***There are two\* important helper scripts that will make this easy***: `scripts/launch_scripts/launch_server.sh` and `scripts/launch_scripts/launch_client.sh`. Pass in arguments like you would for the desired python sub-module. These will launch docker containers, auto-manage file transfer/binding, and copy over `SKYSCAN_*` [environment variables](#environment-variables) for you!

\* _Another useful script is `scripts/launch_scripts/wait_for_startup_json.sh`. Use this before launching each client to eliminate file-writing race conditions._

### Example Startup
#### 1. Launch the Server
```
./scripts/launch_scripts/launch_server.sh \
    --reco-algo millipede \
    --event-file `pwd`/run00136662-evt000035405932-BRONZE.pkl \  # could also be a .json file
    --cache-dir `pwd`/server_cache \
    --output-dir `pwd` \
    --startup-json-dir <STARTUP_JSON_DIR> \
    --broker <BROKER_ADDRESS> \
    --auth-token `cat ~/skyscan-broker.token` \
    --log DEBUG \
    --log-third-party INFO \
```
_NOTE: The `--*dir` arguments can all be the same if you'd like. Relative paths are also fine._

#### 2. Launch Each Client
Each on a different CPU:
```
./scripts/launch_scripts/wait_for_startup_json.sh <STARTUP_JSON_DIR>

./scripts/launch_scripts/launch_client.sh \
    --mq-basename $(cat <STARTUP_JSON_DIR>/mq-basename.txt) \
    --baseline-gcd-file $(cat <STARTUP_JSON_DIR>/baseline_GCD_file.txt) \
    --gcdqp-packet-json <STARTUP_JSON_DIR>/GCDQp_packet.json \
    --broker <BROKER_ADDRESS> \
    --auth-token `cat ~/skyscan-broker.token` \
    --log DEBUG \
    --log-third-party INFO \
```

#### 3. Results
When the server is finished processing reconstructions, it will write a single `.npz` file to `--output-dir`. See `skymap_scanner.utils.scan_result` for more detail.

#### 4. Cleanup & Error Handling
The server will exit on its own once it has received and processed all the reconstructions. The server will write a directory, like `run00127907.evt000020178442.HESE/`, to `--cache-dir`. The clients will exit according to their receiving-queue's timeout value (`--timeout-to-clients`).

All will exit on fatal errors (for clients, use HTCondor to manage re-launching). The in-progress pixel reconstruction is abandoned when a client fails, so there is no concern for duplicate reconstructions at the server. The pre-reconstructed pixel will be re-queued to be delivered to a different client.

### Environment Variables
Because the server and client(s) are launched within Docker containers, all environment variables must start with `SKYSCAN_` in order to be auto-copied forward by the [launch scripts](#how-to-run). See `skymap_scanner.config.env` for more detail.

### Additional Configuration
There are more command-line arguments than those shown in [Example Startup](#example-startup). See `skymap_scanner.server.start_scan.main()` and `skymap_scanner.client.client.main()` for more detail.