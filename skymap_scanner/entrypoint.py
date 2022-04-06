"""Main entry point which triggers different sub-modules."""

import argparse

import healpy  # type: ignore[import]


def main() -> None:
    """Read command-line arguments and trigger producer, worker, collector, or saver."""
    parser = argparse.ArgumentParser(
        description="Run Skymap Scanner according to `mode` argument.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "mode",
        choices=["producer", "worker", "collector", "saver"],
        help="the Skymap Scanner role to invoke",
    )  # TODO - once dust settles, this could be a subparser

    parser.add_argument(
        "-e",
        "--event_url",
        "event_url",
        help="input file URL of the event",
    )
    parser.add_argument(
        "-t",
        "--topic_in",
        default="persistent://icecube/skymap/to_be_scanned",
        dest="TOPICIN",
        help="The Pulsar topic name for pixels to be scanned",
    )
    parser.add_argument(
        "-m",
        "--topic_meta",
        default="persistent://icecube/skymap_metadata/mf_",
        dest="TOPICMETA",
        help="The Pulsar topic name for metadata frames such as G,C,D,Q,p",
    )
    parser.add_argument(
        "-s",
        "--topic_out",
        default="persistent://icecube/skymap/scanned",
        dest="TOPICOUT",
        help="The Pulsar topic name for pixels that have been scanned",
    )
    parser.add_argument(
        "-c",
        "--topic_col",
        default="persistent://icecube/skymap/collected_",
        dest="TOPICCOL",
        help='The Pulsar topic name for pixels that have been collected (each pixel is scanned several times with different seeds, this has the "best" result only)',
    )
    parser.add_argument(
        "-b",
        "--broker",
        default="pulsar://localhost:6650",
        dest="BROKER",
        help="The Pulsar broker URL to connect to",
    )
    parser.add_argument(
        "-a",
        "--auth-token",
        default=None,
        dest="AUTH_TOKEN",
        help="The Pulsar authentication token to use",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="final_output.i3",
        dest="OUTPUT",
        help='Name of the output .i3 file written by the "saver".',
    )
    parser.add_argument(
        "-i",
        "--nside",
        type=int,
        default=None,
        dest="NSIDE",
        help="Healpix NSide, determining the number of pixels to scan.",
    )
    parser.add_argument(
        "--area",
        action="callback",
        callback=lambda option, opt, value, parser: setattr(
            parser.values, option.dest, value.split(",")
        ),
        dest="AREA",
        help="Optional: the area to scan: <center_nside,center_pix,num_pix>",
    )
    parser.add_argument(
        "--pixel-list",
        action="callback",
        callback=lambda option, opt, value, parser: setattr(
            parser.values, option.dest, value.split(",")
        ),
        dest="PIXELLIST",
        help="Optional: a specific comma-separated list of pixels to scan",
    )
    parser.add_argument(
        "-n",
        "--name",
        default=None,
        dest="NAME",
        help="The unique event name. Will be appended to all topic names so that multiple scans can happen in parallel. Make sure you use different names for different events.",
    )
    parser.add_argument(
        "--delete-output-from-queue",
        action="store_true",
        dest="DELETE_OUTPUT_FROM_QUEUE",
        help="When saving the output to a file, delete pixels from the queue once they have been written. They cannot be written a second time in that case.",
    )
    parser.add_argument(
        "--connect-worker-to-all-partitions",
        action="store_true",
        dest="CONNECT_WORKER_TO_ALL_PARTITIONS",
        help="In normal operation the worker will choose a random input partition and only receive from it (and only send to the matching output partition). If you set this, it will read from all partitions. Bad for performance, but should be used if you only have very few workers.",
    )
    parser.add_argument(
        "--fake-scan",
        action="store_true",
        dest="FAKE_SCAN",
        help="Just return random numbers and wait 1 second instead of performing the actual calculation in the worker. For testing only.",
    )

    args = parser.parse_args()

    if args.mode == "producer":
        if args.NAME is None:
            raise RuntimeError(
                "You need to explicitly specify an event name using the `-n` option and make sure you use the same one for producer, worker and collector."
            )

        if args.NSIDE is None:
            raise RuntimeError(
                "You need to explicitly specify an --nside value when in `producer` mode."
            )

        if not healpy.isnsideok(args.NSIDE):
            raise RuntimeError("--nside {} is invalid.".format(args.NSIDE))

        if args.AREA is not None:
            if len(args.AREA) != 3:
                raise RuntimeError(
                    "--area must be configured with a list of length 3: --area <center_nside,center_pix,num_pix>"
                )

            area_center_nside = int(args.AREA[0])
            area_center_pixel = int(args.AREA[1])
            area_num_pixels = int(args.AREA[2])

            if not healpy.isnsideok(area_center_nside):
                raise RuntimeError(
                    "--area center pixel nside {} is invalid.".format(area_center_nside)
                )

            area_center_nside_npix = healpy.nside2npix(area_center_nside)
            if area_center_pixel >= area_center_nside_npix:
                raise RuntimeError(
                    "--area center pixel number {} is invalid (valid range=0..{}).".format(
                        area_center_pixel, area_center_nside_npix - 1
                    )
                )

            if area_num_pixels <= 0:
                raise RuntimeError("--area pixel number cannot be zero or negative!")
        else:
            area_center_nside = None
            area_center_pixel = None
            area_num_pixels = None

        print(
            "Scanning NSide={}, corresponding to NPixel={}".format(
                args.NSIDE, 12 * (args.NSIDE ** 2)
            )
        )

        if args.PIXELLIST is not None:
            print("****** SPECIFIC PIXEL LIST OVERRIDE IS BEING USED ******")
            pixel_list = [int(i) for i in args.PIXELLIST]
            print("scanning: {}".format(pixel_list))
        else:
            pixel_list = None

        producer(
            args.event_url,
            broker=args.BROKER,
            auth_token=args.AUTH_TOKEN,
            topic=args.TOPICIN,
            metadata_topic_base=args.TOPICMETA,
            event_name=args.NAME,
            nside=args.NSIDE,
            area_center_nside=area_center_nside,
            area_center_pixel=area_center_pixel,
            area_num_pixels=area_num_pixels,
            pixel_list=pixel_list,
        )
    elif args.mode == "worker":
        scan_pixel(
            broker=args.BROKER,
            auth_token=args.AUTH_TOKEN,
            topic_in=args.TOPICIN,
            topic_out=args.TOPICOUT,
            fake_scan=args.FAKE_SCAN,
            all_partitions=args.CONNECT_WORKER_TO_ALL_PARTITIONS,
        )
    elif args.mode == "collector":
        collect_pixels(
            broker=args.BROKER,
            auth_token=args.AUTH_TOKEN,
            topic_in=args.TOPICOUT,
            topic_base_out=args.TOPICCOL,
        )
    elif args.mode == "saver":
        if args.NAME is None:
            raise RuntimeError(
                "You need to explicitly specify an event name using the `-n` option and make sure you use the same one for producer, worker and collector."
            )

        if args.NSIDE is None:
            nsides = None
        else:
            print(
                "Waiting for all pixels for NSide={}, corresponding to NPixel={}".format(
                    args.NSIDE, 12 * (args.NSIDE ** 2)
                )
            )
            nsides = [args.NSIDE]

        save_pixels(
            broker=args.BROKER,
            auth_token=args.AUTH_TOKEN,
            topic_in=args.TOPICCOL + args.NAME,
            filename_out=args.OUTPUT,
            nsides_to_wait_for=nsides,
            delete_from_queue=args.DELETE_OUTPUT_FROM_QUEUE,
            npixel_for_nside={128: 3000, 1024: 6000},
        )
    else:
        raise RuntimeError(f'Unknown mode: "{args.mode}"')


if __name__ == "__main__":
    main()
