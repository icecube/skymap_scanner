<!--- Top of README Badges (automated) --->
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/icecube/skymap_scanner?include_prereleases)](https://github.com/icecube/skymap_scanner/) [![Lines of code](https://img.shields.io/tokei/lines/github/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/) [![GitHub issues](https://img.shields.io/github/issues/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen) 
<!--- End of README Badges (automated) --->
# skymap_scanner

Distributed likelihood scan of event directions for real-time alerts using inter-CPU queue-based message passing.

`skymap_scanner` is a python package containing two distinct applications meant to be deployed within containers (1 `skymap_scanner.server`, n `skymap_scanner.client`s), along with `skymap_scanner.utils` (utility functions) and `skymap_scanner.recos` (`icetray` reco-specific logic). Additional, package-independent, utility scripts are in `scripts/utils/`.

### Example Startup
#### 1. Launch the Server
##### Figure Your Args:
```
    --startup-json-dir DIR_TO_PUT_STARTUP_JSON \
    --cache-dir `pwd`/server_cache \
    --output-dir `pwd` \
    --reco-algo millipede \
    --event-file `pwd`/run00136662-evt000035405932-BRONZE.pkl \  # could also be a .json file
    --broker <BROKER_ADDRESS> \
    --auth-token `cat ~/skyscan-broker.token` \
    --timeout-to-clients SOME_NUMBER__BUT_FYI_THERES_A_DEFAULT \
    --timeout-from-clients SOME_NUMBER__BUT_FYI_THERES_A_DEFAULT \
```
_NOTE: The `--*dir` arguments can all be the same if you'd like. Relative paths are also fine._
_NOTE: There are more CL arguments not shown. They have defaults._
##### Run It
###### with Singularity:
```
singularity run skymap_scanner.sif \
    python -m skymap_scanner.server \
    YOUR_ARGS
```
###### or with Docker:
```
./scripts/launch_scripts/docker/launch_server.sh \
    YOUR_ARGS
```

#### 2. Launch Each Client
##### Figure Your Args:
```
    --startup-json-dir DIR_WITH_STARTUP_JSON \
    --broker BROKER_ADDRESS \
    --auth-token `cat ~/skyscan-broker.token` \
    --timeout-to-clients SOME_NUMBER__BUT_FYI_THERES_A_DEFAULT \
    --timeout-from-clients SOME_NUMBER__BUT_FYI_THERES_A_DEFAULT
```
_NOTE: There are more CL arguments not shown. They have defaults._
##### Run It
###### with Condor (Singularity):
You'll want to put your `skymap_scanner.client` args in a file, then pass that to the helper script.
```
echo YOUR_ARGS > my_client_args.txt
./scripts/launch_scripts/condor/spawn_condor_clients.py \
    --jobs ####, \
    --memory #GB, \
    --singularity-image URL_OR_PATH_TO_SINGULARITY_IMAGE, \
    --client-args-file my_client_args.txt
```
###### or Manually (Docker):
```
./scripts/launch_scripts/docker/launch_client.sh \
    YOUR_ARGS
```

#### 3. Results
When the server is finished processing reconstructions, it will write a single `.npz` file to `--output-dir`. See `skymap_scanner.utils.scan_result` for more detail.

#### 4. Cleanup & Error Handling
The server will exit on its own once it has received and processed all the reconstructions. The server will write a directory, like `run00127907.evt000020178442.HESE/`, to `--cache-dir`. The clients will exit according to their receiving-queue's timeout value (`--timeout-to-clients`).

All will exit on fatal errors (for clients, use HTCondor to manage re-launching). The in-progress pixel reconstruction is abandoned when a client fails, so there is no concern for duplicate reconstructions at the server. The pre-reconstructed pixel will be re-queued to be delivered to a different client.

### Environment Variables
When the server and client(s) are launched within Docker containers, all environment variables must start with `SKYSCAN_` in order to be auto-copied forward by the [launch scripts](#how-to-run). See `skymap_scanner.config.env` for more detail.

### Additional Configuration
There are more command-line arguments than those shown in [Example Startup](#example-startup). See `skymap_scanner.server.start_scan.main()` and `skymap_scanner.client.client.main()` for more detail.

#### Runtime Configurable Reconstructions _(Work in Progress)_
Recos are registered by being placed in `skymap_scanner.recos` submodule. Each submodule must contain a class of the same name (eg: `skymap_scanner.recos.foo` has `skymap_scanner.recos.foo.Foo`) which fully inherits from `skymap_scanner.recos.RecoInterface`. This includes defining static methods, `traysegment()` (for IceTray) and `to_pixelreco()` (for MQ).
On the command line, choosing your reco is provided via `--reco-algo` (on the server).
##### Caveats
There ~may be~ ~most likely~ definitely is some millipede-specific logic in the server, upstream of the icetray(s). This will need to be fixed before we can publicize that reconstructions are actually configurable. See https://github.com/icecube/skymap_scanner/issues/8.