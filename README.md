<!--- Top of README Badges (automated) --->
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/icecube/skymap_scanner?include_prereleases)](https://github.com/icecube/skymap_scanner/) [![Lines of code](https://img.shields.io/tokei/lines/github/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/) [![GitHub issues](https://img.shields.io/github/issues/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/icecube/skymap_scanner)](https://github.com/icecube/skymap_scanner/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen) 
<!--- End of README Badges (automated) --->

# Skymap Scanner v3

A distributed system that performs a likelihood scan of event directions for real-time alerts using inter-CPU queue-based message passing.

Skymap Scanner is the computational core of the [SkyDriver orchestration service](https://github.com/WIPACrepo/SkyDriver).

`skymap_scanner` is a python package containing two distinct applications meant to be deployed within containers (1 `skymap_scanner.server`, n `skymap_scanner.client`s), along with `skymap_scanner.utils` (utility functions) and `skymap_scanner.recos` (`icetray` reco-specific logic). Additional, package-independent, utility scripts are in `resources/utils/`.

## Reconstructions Algorithms

Reconstructions algorithms (reco algos) are registered by being placed in a dedicated module within the `skymap_scanner.recos` sub-package. Each module must contain a class of the same name (eg: `skymap_scanner.recos.foo` has `skymap_scanner.recos.foo.Foo`) that fully inherits from `skymap_scanner.recos.RecoInterface`. This includes implementing the static methods: `traysegment()` (for IceTray) and `to_pixelreco()` (for MQ). The reco-specific logic in the upstream/pixel-generation phase is defined in the same class by the `prepare_frames()` (pulse cleaning, vertex generation) and `get_vertex_variations()` (variations of the vertex positions to be used as additional seeds for each pixel). On the command line, choosing your reco is provided via `--reco-algo` (on the server).

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
