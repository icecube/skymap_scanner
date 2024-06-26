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
export EWMS_PILOT_TASK_TIMEOUT=1200
```

Currently, RabbitMQ uses URL parameters for the hostname, virtual host, and port (`[https://]HOST[:PORT][/VIRTUAL_HOST]`). The heartbeat is configured by `EWMS_PILOT_TASK_TIMEOUT`. This may change in future updates.

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
export EWMS_PILOT_QUARANTINE_TIME=1200  # helps decrease condor blackhole nodes
export EWMS_PILOT_TASK_TIMEOUT=1200
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
export EWMS_PILOT_TASK_TIMEOUT=1200
```
###### Command-Line Arguments
```
    --client-startup-json PATH_TO_CLIENT_STARTUP_JSON \
    --cache-dir `pwd`/server_cache \
    --output-dir `pwd` \
    --reco-algo millipede_original \
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
export EWMS_PILOT_TASK_TIMEOUT=1200
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
export EWMS_PILOT_TASK_TIMEOUT=1200
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
environment = "SKYSCAN_BROKER_AUTH=AUTHTOKEN SKYSCAN_BROKER_ADDRESS=BROKER_ADDRESS EWMS_PILOT_TASK_TIMEOUT=1200 EWMS_PILOT_QUARANTINE_TIME=1200"
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
When the server and client(s) are launched within Docker containers, all environment variables must start with `SKYSCAN_` in order to be auto-copied forward by the [launch scripts](#how-to-run). `EWMS_`-prefixed variables are also forwarded. See `skymap_scanner.config.ENV` for more detail.
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
Relatedly, the environment variable `EWMS_PILOT_TASK_TIMEOUT` & `EWMS_PILOT_QUARANTINE_TIME` can also be configured (see [1. Launch the Server](#1-launch-the-server) and [2. Launch Each Client](#2-launch-each-client)).

#### Command-Line Arguments
There are more command-line arguments than those shown in [Example Startup](#example-startup). See `skymap_scanner.server.start_scan.main()` and `skymap_scanner.client.client.main()` for more detail.

#### Runtime-Configurable Reconstructions
Recos are registered by being placed in a dedicated module within the `skymap_scanner.recos` sub-package. Each module must contain a class of the same name (eg: `skymap_scanner.recos.foo` has `skymap_scanner.recos.foo.Foo`) that fully inherits from `skymap_scanner.recos.RecoInterface`. This includes implementing the static methods: `traysegment()` (for IceTray) and `to_pixelreco()` (for MQ). The reco-specific logic in the upstream/pixel-generation phase is defined in the same class by the `prepare_frames()` (pulse cleaning, vertex generation) and `get_vertex_variations()` (variations of the vertex positions to be used as additional seeds for each pixel). On the command line, choosing your reco is provided via `--reco-algo` (on the server).

## Making Branch-Based Images for Production-like Testing
If you need to test your updates in a production-like environment at a scale that isn't provided by CI, then create a branch-based image. This image will be available on Docker Hub and CVMFS.
### Steps:
1. Go to _Actions_ tab
1. Go to `docker & singularity/cvmfs releases` workflow tab (on left column)
1. Click _Run workflow_, select your branch, and click the _Run workflow_ button
1. Wait for the workflow steps to complete
    * You can check the workflow's progress by clicking the top-most entry (there will be a small delay after the previous step)
1. Check https://hub.docker.com/r/icecube/skymap_scanner/tags and/or CVMFS (the filepath will be the bottom-most line of https://github.com/WIPACrepo/cvmfs-actions/blob/main/docker_images.txt)
### Note
The resulting image is specific to the branch's most recent commit. To test subsequent updates, you will need to repeat this process.


## Data Types
These are the important data types within the scanner. Since memory-reduction is a consideration, some are persisted longer than others.

### Pixel-Like
There are 5 data types to represent a pixel-like thing in its various forms. In order of appearance:
#### 1. `(nside, pixel_id)`-tuple
- generated by `pixels.py`
#### 2. `I3Frame`
- generated by `PixelsToReco`
- introduces position-variations (eg: `milipede_original`)
- M `I3Frame` : 1 `(nside, pixel_id)`-tuple
- sent to client(s), not persisted on the server
- ~800 bytes
#### 3. `SentPixelVariation`
- used for tracking a single sent pixel variation
- 1 `SentPixelVariation` : 1 `I3Frame`
- persisted on the server in place of `I3Frame`
- ~50 bytes
#### 4. `RecoPixelVariation`
- represents a pixel-variation reconstruction
- sent from client to server, persisted on the server
- 1 `RecoPixelVariation` : 1 `SentPixelVariation`
- ~50 bytes
#### 5. `RecoPixelFinal`
- represents a final saved pixel post-reco (on the server only)
- 1 `RecoPixelFinal` : M `RecoPixelVariation`
- These types are saved in `nsides_dict` (`NSidesDict`)
- ~50 bytes

### Sky Map-Like
Unlike pixel-like data types, these types are meant to exist as singular instances within the scanner.
#### `nsides_dict` (`NSidesDict`)
- a dict of dicts containing `RecoPixelFinal` objects, keyed by nside & pixel id
- exists on the server only
- grows as the scan progresses
- not persisted past the lifetime of a scan
#### `skyreader.SkyScanResult`
- a class/object for using the result of a scan outside of the scanner (see [icecube/skyreader](https://github.com/icecube/skyreader))
- created at the end of the scan (from `nsides_dict`)
    * intermediate/incomplete instances exist only to be sent to SkyDriver
- can be exported to JSON and/or `.npz`-file
- can be created from `nsides_dict` (internal to the scanner), JSON, and/or `.npz`-file
- SkyDriver persists a serialized (JSON) version for each scan

## Versioning
The `MAJOR.MINOR.PATCH` versioning scheme is updated according to the following

1. `MAJOR`: Breaking change or other fundamental change in the skymap-scanner
2. `MINOR`: Physics change or non-breaking new feature
3. `PATCH`: Bug fixes

When the icetray image is updated, try to follow the same schema as its version update. So if icetray is bumped up a minor release, also increment it here.
