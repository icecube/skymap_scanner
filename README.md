<!--- Top of README Badges (automated) --->
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/icecube/skymap_scanner?include_prereleases)](https://github.com/icecube/skymap_scanner/) [![Lines of code](https://img.shields.io/tokei/lines/github/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/) [![GitHub issues](https://img.shields.io/github/issues/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen) 
<!--- End of README Badges (automated) --->
# Skymap Scanner v3

A distributed system that performs a likelihood scan of event directions for real-time alerts using inter-CPU queue-based message passing.

Skymap Scanner is the computational core of the [SkyDriver orchestration service](https://github.com/WIPACrepo/SkyDriver).

`skymap_scanner` is a python package containing two distinct applications meant to be deployed within containers (1 `skymap_scanner.server`, n `skymap_scanner.client`s), along with `skymap_scanner.utils` (utility functions) and `skymap_scanner.recos` (`icetray` reco-specific logic). Additional, package-independent, utility scripts are in `resources/utils/`.

## Queue Types

The default queue type in the container is RabbitMQ, since v3.1.0.
Build `Dockerfile_pulsar` for a pulsar container.

### RabbitMQ
Env variables

```
# export SKYSCAN_BROKER_CLIENT=rabbitmq  # rabbitmq is the default so env var is not needed
export SKYSCAN_BROKER_ADDRESS=<hostname>/<vhost>
export SKYSCAN_BROKER_AUTH=<token>
export EWMS_PILOT_QUARANTINE_TIME=1200  # helps decrease condor blackhole nodes
export RABBITMQ_HEARTBEAT=600
```

Currently, RabbitMQ uses URL parameters for the hostname, virtual host, and port (`[https://]HOST[:PORT][/VIRTUAL_HOST]`). The heartbeat is configured by `RABBITMQ_HEARTBEAT`. This may change in future updates.

Python install:
```
pip install .[rabbitmq]
```

### Pulsar
Env variables

```
export SKYSCAN_BROKER_CLIENT=pulsar
export SKYSCAN_BROKER_ADDRESS=<ip address>
export SKYSCAN_BROKER_AUTH=<token>
export PULSAR_UNACKED_MESSAGES_TIMEOUT_SEC=900
```

Python install:
```
pip install .[pulsar]
```

## Example
This example is for the rabbitmq (default) broker. Steps for using a pulsar broker are similar and differences are noted throughout this example. The predominant difference is noted in [Queue Types](queue-types) (`Dockerfile_pulsar`).

### Example Startup
You will need to get a rabbitmq broker address and authentication token to pass to both the server and client. Send a poke on slack #skymap-scanner to get those!

#### 1. Launch the Server
The server can be launched from anywhere with a stable network connection. You can run it from the cobalts for example.

##### Figure Your Args
###### Environment Variables
```
export SKYSCAN_BROKER_ADDRESS=BROKER_ADDRESS
# export SKYSCAN_BROKER_CLIENT=rabbitmq  # rabbitmq is the default so env var is not needed
export SKYSCAN_BROKER_AUTH=$(cat ~/skyscan-broker.token)  # obfuscated for security
export RABBITMQ_HEARTBEAT=600  # replace with PULSAR_UNACKED_MESSAGES_TIMEOUT_SEC=900 for pulsar
```
###### Command-Line Arguments
```
    --client-startup-json PATH_TO_CLIENT_STARTUP_JSON \
    --cache-dir `pwd`/server_cache \
    --output-dir `pwd` \
    --reco-algo millipede \
    --event-file `pwd`/run00136662-evt000035405932-BRONZE.pkl  # could also be a .json file
```
_NOTE: The `--*dir` arguments can all be the same if you'd like. Relative paths are also fine._
_NOTE: There are more CL arguments not shown. They have defaults._
###### `client-startup.json`
The server will create a `PATH_TO_CLIENT_STARTUP_JSON` file that has necessary info to launch a client. the parent directory of `--client-startup-json` needs to be somewhere accessible by your client launch script, whether that's via condor or manually.
##### Run It
###### with Singularity
```
singularity run /cvmfs/icecube.opensciencegrid.org/containers/realtime/skymap_scanner:x.y.z" \
    python -m skymap_scanner.server \
    YOUR_ARGS
```
###### or with Docker
```
# side note: you may want to first set environment variables, see below
./resources/launch_scripts/docker/launch_server.sh \
    YOUR_ARGS
```
_NOTE: By default the launch script will pull, build, and run the latest image from Docker Hub. You can optionally set environment variables to configure how to find a particular tag. For example:_
```
export SKYSCAN_DOCKER_IMAGE_TAG='x.y.z'  # defaults to 'latest'
export SKYSCAN_DOCKER_PULL_ALWAYS=0  # defaults to 1 which maps to '--pull=always'
export RABBITMQ_HEARTBEAT=600  # replace with PULSAR_UNACKED_MESSAGES_TIMEOUT_SEC=900 for pulsar
```

#### 2. Launch Each Client
The client jobs can submitted via HTCondor from sub-2. Running the script below should create a condor submit file requesting the number of workers specified. You'll need to give it the same `SKYSCAN_BROKER_ADDRESS` and `BROKER_AUTH` as the server, and the path to the client-startup json file created by the server.

##### Figure Your Args
###### Environment Variables
```
export SKYSCAN_BROKER_ADDRESS=BROKER_ADDRESS
# export SKYSCAN_BROKER_CLIENT=rabbitmq  # rabbitmq is the default so env var is not needed
export SKYSCAN_BROKER_AUTH=$(cat ~/skyscan-broker.token)  # obfuscated for security
export EWMS_PILOT_QUARANTINE_TIME=1200  # helps decrease condor blackhole nodes
export RABBITMQ_HEARTBEAT=600  # replace with PULSAR_UNACKED_MESSAGES_TIMEOUT_SEC=900 for pulsar
```
###### Command-Line Arguments
_See notes about `--client-startup-json` below. See `client.py` for additional optional args._
##### Run It
###### with Condor (via Singularity)
You'll want to put your `skymap_scanner.client` args in a JSON file, then pass that to the helper script.
```
echo my_client_args.json  # just an example
./resources/client_starter.py \
    --jobs #### \
    --memory #GB \
    --singularity-image URL_OR_PATH_TO_SINGULARITY_IMAGE \
    --client-startup-json PATH_TO_CLIENT_STARTUP_JSON \
    --client-args-json my_client_args.json
```
_NOTE: `client_starter.py` will wait until `--client-startup-json PATH_TO_CLIENT_STARTUP_JSON` exists, since it needs to file-transfer it to the worker node. Similarly, the client's `--client-startup-json` is auto-set by the script and thus, is disallowed from being in the `--client-args` arguments._
###### or Manually (Docker)
```
# side note: you may want to first set environment variables, see below
./resources/launch_scripts/wait_for_file.sh PATH_TO_CLIENT_STARTUP_JSON 600
./resources/launch_scripts/docker/launch_client.sh \
    --client-startup-json PATH_TO_CLIENT_STARTUP_JSON \
    YOUR_ARGS
```
_NOTE: By default the launch script will pull, build, and run the latest image from Docker Hub. You can optionally set environment variables to configure how to find a particular tag. For example:_
```
export SKYSCAN_DOCKER_IMAGE_TAG='x.y.z'  # defaults to 'latest'
export SKYSCAN_DOCKER_PULL_ALWAYS=0  # defaults to 1 which maps to '--pull=always'
```

#### 3. Results
When the server is finished processing reconstructions, it will write a single `.npz` file to `--output-dir`. See `skymap_scanner.utils.scan_result` for more detail.

#### 4. Cleanup & Error Handling
The server will exit on its own once it has received and processed all the reconstructions. The server will write a directory, like `run00127907.evt000020178442.HESE/`, to `--cache-dir`. The clients will exit according to their receiving-queue's timeout value (`SKYSCAN_MQ_TIMEOUT_TO_CLIENTS`), unless they are killed manually (`condor_rm`).

All will exit on fatal errors (for clients, use HTCondor to manage re-launching). The in-progress pixel reconstruction is abandoned when a client fails, so there is no concern for duplicate reconstructions at the server. The pre-reconstructed pixel will be re-queued to be delivered to a different client.

### In-Production Usage Note: Converting i3 to json and scaling up
You may want to run on events stored in i3 files. To convert those into a json format readable by the scanner, you can do
```
cd resources/utils
python i3_to_json.py --basegcd /data/user/followup/baseline_gcds/baseline_gcd_136897.i3 EVENT_GCD.i3 EVENT_FILE.i3
```
This will pull all the events in the i3 file into `run*.evt*.json` which can be passed as an argument to the server.

For now, it's easy to scale up using the command line. Multiple server instances can be run simultaneously and a separate submit file created for each one. To run `N` servers in parallel

```
export SKYSCAN_BROKER_ADDRESS=BROKER_ADDRESS
export SKYSCAN_BROKER_CLIENT=rabbitmq
export SKYSCAN_BROKER_AUTH=$(cat ~/skyscan-broker.token)  # obfuscated for security
ls *.json | xargs -n1 -PN -I{} bash -c 'mkdir /path/to/json/{} && python -m skymap_scanner.server --client-startup-json /path/to/json/{}/client-startup.json --cache-dir /path/to/cache --output-dir /path/to/out --reco-algo RECO_ALGO --event-file /path/to/data/{}'
```

Then, from sub-2 run `ls *.json |xargs -I{} bash -c 'sed "s/UID/{}/g" ../condor > /scratch/$USER/{}.condor'` using the template condor submit file below. Then you should be able to just run:
```
ls /scratch/$USER/run*.condor | head -nN | xargs -I{} condor_submit {}
```
```
executable = /bin/sh 
arguments = /usr/local/icetray/env-shell.sh python -m skymap_scanner.client --client-startup-json ./client-startup.json
+SingularityImage = "/cvmfs/icecube.opensciencegrid.org/containers/realtime/skymap_scanner:x.y.z"
environment = "SKYSCAN_BROKER_AUTH=AUTHTOKEN SKYSCAN_BROKER_ADDRESS=BROKER_ADDRESS RABBITMQ_HEARTBEAT=600 EWMS_PILOT_QUARANTINE_TIME=1200"
Requirements = HAS_CVMFS_icecube_opensciencegrid_org && has_avx
output = /scratch/$USER/UID.out
error = /scratch/$USER/UID.err
log = /scratch/$USER/UID.log
+FileSystemDomain = "blah"
should_transfer_files = YES
transfer_input_files = /path/to/json/UID/client-startup.json
request_cpus = 1
request_memory = 8GB
notification = Error
queue 300 
```

You may also need to add this line to the condor submit file if running `millipede_wilks` as some resources have been removed from the image.
```
environment = "APPTAINERENV_I3_DATA=/cvmfs/icecube.opensciencegrid.org/data SINGULARITYENV_I3_DATA=/cvmfs/icecube.opensciencegrid.org/data I3_DATA=/cvmfs/icecube.opensciencegrid.org/data I3_TESTDATA=/cvmfs/icecube.opensciencegrid.org/data/i3-test-data-svn/trunk"
```
The extra envs for `I3_DATA` are to ensure it gets passed through for use inside the container. Additionally, ftp-v1 ice was introduced in v3.4.0.

### Additional Configuration
#### Environment Variables
When the server and client(s) are launched within Docker containers, all environment variables must start with `SKYSCAN_` in order to be auto-copied forward by the [launch scripts](#how-to-run). `EWMS_`-, `PULSAR_`- and, `RABBITMQ_`-prefixed variables are also forwarded. See `skymap_scanner.config.ENV` for more detail.
##### Timeouts
The Skymap Scanner is designed to have realistic timeouts for HTCondor. That said, there are three main timeouts which can be altered:
```
    # seconds -- how long client waits between receiving pixels before thinking event scan is 100% done
    #  - set to `max(reco duration) + max(subsequent iteration startup time)`
    #  - think about starved clients
    #  - normal expiration scenario: the scan is done, no more pixels to scan (alternative: manually kill client process)
    SKYSCAN_MQ_TIMEOUT_TO_CLIENTS: int = 60 * 30  # 30 mins
    #
    # seconds -- how long server waits before thinking all clients are dead
    #  - set to duration of first reco + client launch (condor)
    #  - important if clients launch *AFTER* server
    #  - normal expiration scenario: all clients died (bad condor submit file), otherwise never (server knows when all recos are done)
    SKYSCAN_MQ_TIMEOUT_FROM_CLIENTS: int = 3 * 24 * 60 * 60  # 3 days
    #
    # seconds -- how long client waits before first message (set to duration of server startup)
    #  - important if clients launch *BEFORE* server
    #  - normal expiration scenario: server died (ex: tried to read corrupted event file), otherwise never
    SKYSCAN_MQ_CLIENT_TIMEOUT_WAIT_FOR_FIRST_MESSAGE: int = 60 * 60  # 60 mins
```
Relatedly, the environment variable `RABBITMQ_HEARTBEAT` & `EWMS_PILOT_QUARANTINE_TIME` can also be configured (see [1. Launch the Server](#1-launch-the-server) and [2. Launch Each Client](#2-launch-each-client)).

#### Command-Line Arguments
There are more command-line arguments than those shown in [Example Startup](#example-startup). See `skymap_scanner.server.start_scan.main()` and `skymap_scanner.client.client.main()` for more detail.

#### Runtime-Configurable Reconstructions
Recos are registered by being placed in a dedicated module within the `skymap_scanner.recos` sub-package. Each module must contain a class of the same name (eg: `skymap_scanner.recos.foo` has `skymap_scanner.recos.foo.Foo`) that fully inherits from `skymap_scanner.recos.RecoInterface`. This includes implementing the static methods: `traysegment()` (for IceTray) and `to_pixelreco()` (for MQ). Specialized reco-specific logic in the upstream/pixel-generation phase is done on an ad-hoc basis, eg: `if reco_algo == 'millipede_original': ...`. On the command line, choosing your reco is provided via `--reco-algo` (on the server).
