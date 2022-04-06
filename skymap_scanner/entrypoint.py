if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    usage = """%prog <producer|worker> [options] <master:eventURL>"""
    parser.set_usage(usage)
    parser.add_option(
        "-t",
        "--topic_in",
        action="store",
        type="string",
        default="persistent://icecube/skymap/to_be_scanned",
        dest="TOPICIN",
        help="The Pulsar topic name for pixels to be scanned",
    )
    parser.add_option(
        "-m",
        "--topic_meta",
        action="store",
        type="string",
        default="persistent://icecube/skymap_metadata/mf_",
        dest="TOPICMETA",
        help="The Pulsar topic name for metadata frames such as G,C,D,Q,p",
    )
    parser.add_option(
        "-s",
        "--topic_out",
        action="store",
        type="string",
        default="persistent://icecube/skymap/scanned",
        dest="TOPICOUT",
        help="The Pulsar topic name for pixels that have been scanned",
    )
    parser.add_option(
        "-c",
        "--topic_col",
        action="store",
        type="string",
        default="persistent://icecube/skymap/collected_",
        dest="TOPICCOL",
        help='The Pulsar topic name for pixels that have been collected (each pixel is scanned several times with different seeds, this has the "best" result only)',
    )
    parser.add_option(
        "-b",
        "--broker",
        action="store",
        type="string",
        default="pulsar://localhost:6650",
        dest="BROKER",
        help="The Pulsar broker URL to connect to",
    )
    parser.add_option(
        "-a",
        "--auth-token",
        action="store",
        type="string",
        default=None,
        dest="AUTH_TOKEN",
        help="The Pulsar authentication token to use",
    )

    parser.add_option(
        "-o",
        "--output",
        action="store",
        type="string",
        default="final_output.i3",
        dest="OUTPUT",
        help='Name of the output .i3 file written by the "saver".',
    )

    parser.add_option(
        "-i",
        "--nside",
        action="store",
        type="int",
        default=None,
        dest="NSIDE",
        help="Healpix NSide, determining the number of pixels to scan.",
    )

    parser.add_option(
        "--area",
        action="callback",
        type="string",
        callback=lambda option, opt, value, parser: setattr(
            parser.values, option.dest, value.split(",")
        ),
        dest="AREA",
        help="Optional: the area to scan: <center_nside,center_pix,num_pix>",
    )

    parser.add_option(
        "--pixel-list",
        action="callback",
        type="string",
        callback=lambda option, opt, value, parser: setattr(
            parser.values, option.dest, value.split(",")
        ),
        dest="PIXELLIST",
        help="Optional: a specific comma-separated list of pixels to scan",
    )

    parser.add_option(
        "-n",
        "--name",
        action="store",
        type="string",
        default=None,
        dest="NAME",
        help="The unique event name. Will be appended to all topic names so that multiple scans can happen in parallel. Make sure you use different names for different events.",
    )

    parser.add_option(
        "--delete-output-from-queue",
        action="store_true",
        dest="DELETE_OUTPUT_FROM_QUEUE",
        help="When saving the output to a file, delete pixels from the queue once they have been written. They cannot be written a second time in that case.",
    )

    parser.add_option(
        "--connect-worker-to-all-partitions",
        action="store_true",
        dest="CONNECT_WORKER_TO_ALL_PARTITIONS",
        help="In normal operation the worker will choose a random input partition and only receive from it (and only send to the matching output partition). If you set this, it will read from all partitions. Bad for performance, but should be used if you only have very few workers.",
    )

    parser.add_option(
        "--fake-scan",
        action="store_true",
        dest="FAKE_SCAN",
        help="Just return random numbers and wait 1 second instead of performing the actual calculation in the worker. For testing only.",
    )

    # get parsed args
    (options, args) = parser.parse_args()

    if len(args) < 1:
        raise RuntimeError("You need to specify a mode <producer|worker>")
    mode = args[0].lower()

    topic_base_meta = options.TOPICMETA
    topic_in = options.TOPICIN
    topic_out = options.TOPICOUT
    topic_base_col = options.TOPICCOL

    if mode == "producer":
        if len(args) != 2:
            raise RuntimeError(
                "You need to specify an input file URL in `producer` mode"
            )

        if options.NAME is None:
            raise RuntimeError(
                "You need to explicitly specify an event name using the `-n` option and make sure you use the same one for producer, worker and collector."
            )

        if options.NSIDE is None:
            raise RuntimeError(
                "You need to explicitly specify an --nside value when in `producer` mode."
            )

        if not healpy.isnsideok(options.NSIDE):
            raise RuntimeError("--nside {} is invalid.".format(options.NSIDE))

        if options.AREA is not None:
            if len(options.AREA) != 3:
                raise RuntimeError(
                    "--area must be configured with a list of length 3: --area <center_nside,center_pix,num_pix>"
                )

            area_center_nside = int(options.AREA[0])
            area_center_pixel = int(options.AREA[1])
            area_num_pixels = int(options.AREA[2])

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

        nside = options.NSIDE
        npixels = 12 * (nside ** 2)

        print("Scanning NSide={}, corresponding to NPixel={}".format(nside, npixels))

        if options.PIXELLIST is not None:
            print("****** SPECIFIC PIXEL LIST OVERRIDE IS BEING USED ******")
            pixel_list = [int(i) for i in options.PIXELLIST]
            print("scanning: {}".format(pixel_list))
        else:
            pixel_list = None

        eventURL = args[1]
        producer(
            eventURL,
            broker=options.BROKER,
            auth_token=options.AUTH_TOKEN,
            topic=topic_in,
            metadata_topic_base=topic_base_meta,
            event_name=options.NAME,
            nside=nside,
            area_center_nside=area_center_nside,
            area_center_pixel=area_center_pixel,
            area_num_pixels=area_num_pixels,
            pixel_list=pixel_list,
        )
    elif mode == "worker":
        scan_pixel(
            broker=options.BROKER,
            auth_token=options.AUTH_TOKEN,
            topic_in=topic_in,
            topic_out=topic_out,
            fake_scan=options.FAKE_SCAN,
            all_partitions=options.CONNECT_WORKER_TO_ALL_PARTITIONS,
        )
    elif mode == "collector":
        collect_pixels(
            broker=options.BROKER,
            auth_token=options.AUTH_TOKEN,
            topic_in=topic_out,
            topic_base_out=topic_base_col,
        )
    elif mode == "saver":
        if options.NAME is None:
            raise RuntimeError(
                "You need to explicitly specify an event name using the `-n` option and make sure you use the same one for producer, worker and collector."
            )

        if options.NSIDE is None:
            nsides = None
        else:
            nside = options.NSIDE
            npixels = 12 * (nside ** 2)
            print(
                "Waiting for all pixels for NSide={}, corresponding to NPixel={}".format(
                    nside, npixels
                )
            )
            nsides = [nside]

        save_pixels(
            broker=options.BROKER,
            auth_token=options.AUTH_TOKEN,
            topic_in=topic_base_col + options.NAME,
            filename_out=options.OUTPUT,
            nsides_to_wait_for=nsides,
            delete_from_queue=options.DELETE_OUTPUT_FROM_QUEUE,
            npixel_for_nside={128: 3000, 1024: 6000},
        )
    else:
        raise RuntimeError('Unknown mode "{}"'.args[0])
