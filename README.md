<!--- Top of README Badges (automated) --->
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/icecube/skymap_scanner?include_prereleases)](https://github.com/icecube/skymap_scanner/) [![Lines of code](https://img.shields.io/tokei/lines/github/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/) [![GitHub issues](https://img.shields.io/github/issues/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen) 
<!--- End of README Badges (automated) --->
# skymap_scanner

A distributed system that performs a likelihood scan of event directions for real-time alerts using inter-CPU queue-based message passing.

`skymap_scanner` is a python package containing two distinct applications meant to be deployed within containers (1 `skymap_scanner.server`, n `skymap_scanner.client`s), along with `skymap_scanner.utils` (utility functions) and `skymap_scanner.recos` (`icetray` reco-specific logic). Additional, package-independent, utility scripts are in `scripts/utils/`.

### Example Startup
You will need to get a pulsar broker address and authentication token to pass to both the server and client. Send a poke on slack #skymap-scanner to get those!

#### 1. Launch the Server
The server can be launched from anywhere with a stable network connection. You can run it from the cobalts for example. For now, set `--timeout-to-clients` and `--timeout-from-clients` to a large value like 300000. This will persist the server in case the clients don't start up right away.
##### Figure Your Args
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
###### `startup.json`
The server will create a `startup.json` file that has necessary info to launch a client. `--startup-json-dir` needs to be somewhere accessible by your client launch script, whether that's via condor or manually.
##### Run It
###### with Singularity
```
singularity run /cvmfs/icecube.opensciencegrid.org/containers/realtime/skymap_scanner:x.y.z" \
    python -m skymap_scanner.server \
    YOUR_ARGS
```
###### or with Docker
```
./scripts/launch_scripts/docker/launch_server.sh \
    YOUR_ARGS
```

#### 2. Launch Each Client
The client jobs can submitted via HTCondor from sub-2. Running the script below should create a condor submit file requesting the number of workers specified. You'll need to give it the same `BROKER_ADDRESS` and `AUTH_TOKEN` as the server, and the path to the startup json file created by the server. 

On sub-2, suggest setting `--timeout-to-clients` and `--timeout-from-clients` to a reasonable number like 3600s. This should keep workers long enough to process through the reconstructions and release them once the jobs are complete.

##### Figure Your Args
```
    --broker BROKER_ADDRESS \
    --auth-token AUTH_TOKEN \
    --timeout-to-clients SOME_NUMBER__BUT_FYI_THERES_A_DEFAULT \
    --timeout-from-clients SOME_NUMBER__BUT_FYI_THERES_A_DEFAULT
```
_NOTE: There are more CL arguments not shown. They have defaults._
##### Run It
###### with Condor (via Singularity)
You'll want to put your `skymap_scanner.client` args in a JSON file, then pass that to the helper script.
```
echo my_client_args.json  # just an example
./scripts/launch_scripts/condor/spawn_condor_clients.py \
    --jobs #### \
    --memory #GB \
    --singularity-image URL_OR_PATH_TO_SINGULARITY_IMAGE \
    --startup-json PATH_TO_STARTUP_JSON \
    --client-args-json my_client_args.json
```
_NOTE: `spawn_condor_clients.py` will wait until `--startup-json PATH_TO_STARTUP_JSON` exists, since it needs to file-transfer it to the worker node. Similarly, `--startup-json-dir` is auto-set by the script and thus, is disallowed from being in the `--client-args-json` file._
###### or Manually (Docker)
```
./scripts/launch_scripts/wait_for_startup_json.sh DIR_WITH_STARTUP_JSON
./scripts/launch_scripts/docker/launch_client.sh \
    --startup-json-dir DIR_WITH_STARTUP_JSON \
    YOUR_ARGS
```

#### 3. Results
When the server is finished processing reconstructions, it will write a single `.npz` file to `--output-dir`. See `skymap_scanner.utils.scan_result` for more detail.

#### 4. Cleanup & Error Handling
The server will exit on its own once it has received and processed all the reconstructions. The server will write a directory, like `run00127907.evt000020178442.HESE/`, to `--cache-dir`. The clients will exit according to their receiving-queue's timeout value (`--timeout-to-clients`).

All will exit on fatal errors (for clients, use HTCondor to manage re-launching). The in-progress pixel reconstruction is abandoned when a client fails, so there is no concern for duplicate reconstructions at the server. The pre-reconstructed pixel will be re-queued to be delivered to a different client.

#### 5. Converting i3 to json and scaling up
You may want to run on events stored in i3 files. To convert those into a json format readable by the scanner, you can do
```
cd scripts/utils
python i3_to_json.py --basegcd /data/user/followup/baseline_gcds/baseline_gcd_136897.i3 EVENT_GCD.i3 EVENT_FILE.i3
```
This will pull all the events in the i3 file into `run*.evt*.json` which can be passed as an argument to the server.

For now, it's easy to scale up using the command line. Multiple server instances can be run simultaneously and a separate submit file created for each one.

```
ls *.json | xargs -I{} bash -c 'mkdir /path/to/json/{} && python -m skymap_scanner.server --startup-json-dir /path/to/json/{} --cache-dir /path/to/cache --output-dir /path/to/out --reco-algo RECO_ALGO --event-file /path/to/data/{} --broker BROKER_ADDRESS --auth-token AUTH_TOKEN --timeout-to-clients 300000 --timeout-from-clients 300000'
```

Then, from sub-2 run `ls *.json |xargs -I{} bash -c 'sed "s/UID/{}/g" ../condor > /scratch/user/{}.condor'` using the template condor submit file below. Then you should be able to just run `condor_submit /scratch/user/*.condor`.

```
executable = /bin/sh                                                                                                                                                                                                                           
arguments = /usr/local/icetray/env-shell.sh python -m skymap_scanner.client --broker BROKER_ADDRESS --auth-token AUTH_TOKEN --timeout-to-clients 3600 --timeout-from-clients 3600 --startup-json-dir .
+SingularityImage = "/cvmfs/icecube.opensciencegrid.org/containers/realtime/skymap_scanner:x.y.z"
Requirements = HAS_CVMFS_icecube_opensciencegrid_org && has_avx
output = /scratch/tyuan/scan/UID.out
error = /scratch/tyuan/scan/UID.err
log = /scratch/tyuan/scan/UID.log
+FileSystemDomain = "blah"
should_transfer_files = YES
transfer_input_files = /path/to/json/UID/startup.json 
request_cpus = 1                                                                                                                                                                                                                               request_memory = 8GB
notification = Error
queue 300 
```

### Additional Configuration
#### Environment Variables
When the server and client(s) are launched within Docker containers, all environment variables must start with `SKYSCAN_` in order to be auto-copied forward by the [launch scripts](#how-to-run). See `skymap_scanner.config.env` for more detail.

#### Command-Line Arguments
There are more command-line arguments than those shown in [Example Startup](#example-startup). See `skymap_scanner.server.start_scan.main()` and `skymap_scanner.client.client.main()` for more detail.

#### Runtime-Configurable Reconstructions _(Work in Progress)_
Recos are registered by being placed in a dedicated module within the `skymap_scanner.recos` sub-package. Each module must contain a class of the same name (eg: `skymap_scanner.recos.foo` has `skymap_scanner.recos.foo.Foo`) that fully inherits from `skymap_scanner.recos.RecoInterface`. This includes implementing the static methods: `traysegment()` (for IceTray) and `to_pixelreco()` (for MQ).
On the command line, choosing your reco is provided via `--reco-algo` (on the server).
##### Caveats
There ~may be~ ~most likely~ definitely is some millipede-specific logic in the server, upstream of the icetray(s). This will need to be fixed before we can publicize that reconstructions are actually configurable. See https://github.com/icecube/skymap_scanner/issues/8.
