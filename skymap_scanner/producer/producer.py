"""Entry point for the Producer sub-package."""


def producer(
    eventURL,
    broker,
    auth_token,
    topic,
    metadata_topic_base,
    event_name,
    nside,
    area_center_nside=None,
    area_center_pixel=None,
    area_num_pixels=None,
    pixel_list=None,
):
    """
    Handle incoming events and perform a full scan.
    """
    if (
        area_center_nside is not None
        or area_center_pixel is not None
        or area_num_pixels is not None
    ) and (
        area_center_nside is None
        or area_center_pixel is None
        or area_num_pixels is None
    ):
        raise RuntimeError(
            "You have to either set none of the three options area_center_nside,area_center_pixel,area_num_pixels or all of them"
        )

    try:
        # figure out if this is supposed to be JSON or .i3:
        url_file_path = urlparse(eventURL).path
        file_name, file_ext = os.path.splitext(url_file_path)
        if file_ext == ".json":
            file_format = "json"
        elif file_ext == ".i3":
            file_format = "i3"
        elif file_ext in [".zst", ".gz", ".bz2", ".xz"]:
            file_name, file_ext2 = os.path.splitext(file_name)
            if file_ext2 == ".i3":
                file_format = "i3"
            else:
                raise RuntimeError(
                    "File format {}.{} is unknown (url={})".format(
                        file_ext2, file_ext, eventURL
                    )
                )
        else:
            raise RuntimeError(
                "File format {} is unknown (url={})".format(file_ext, eventURL)
            )

        # load JSON
        if file_format == "json":
            # get a file stager
            stagers = dataio.get_stagers()

            print(
                "Skymap scanner is starting. Reading event information from JSON blob at `{0}`.".format(
                    eventURL
                )
            )

            print("reading JSON blob from {0}".format(eventURL))
            json_blob_handle = stagers.GetReadablePath(eventURL)
            if not os.path.isfile(str(json_blob_handle)):
                print("problem reading JSON blob from {0}".format(eventURL))
                raise RuntimeError(
                    "problem reading JSON blob from {0}".format(eventURL)
                )
            with open(str(json_blob_handle)) as json_data:
                json_event = json.load(json_data)
            del json_blob_handle

            # extract the JSON message
            print("Event loaded. I am extracting it now...")
            GCDQp_packet = extract_json_message(json_event)

            # Note: the online messages to not use pulse cleaning, so we will need to work with
            # "SplitUncleanedInIcePulses" instead of "SplitInIcePulses" as the P-frame pulse map.
            # (Setting `pulsesName` will make sure "SplitInIcePulses" gets created and just points
            # to "SplitUncleanedInIcePulses".)
            pulsesName = "SplitUncleanedInIcePulses"
        else:  # file_format == 'i3'
            print(
                "Skymap scanner is starting. Reading event information from i3 file at `{0}`.".format(
                    eventURL
                )
            )
            GCDQp_packet = extract_i3_file(eventURL)

            pulsesName = "SplitInIcePulses"

        # rename frame onbjects we might recreate
        GCDQp_packet = clean_old_frame_objects(GCDQp_packet)

        # (re-)create the online alert information
        GCDQp_packet = calculate_online_alert_dict(GCDQp_packet, pulsesName=pulsesName)

        # This step will create missing frame objects if necessary.
        print(
            "Event extracted. I will now perform some simple tasks like the HESE veto calculation..."
        )
        GCDQp_packet = prepare_frames(GCDQp_packet, pulsesName=pulsesName)
        print("Done.")

        # get the event id
        event_id = get_event_id(GCDQp_packet)

        # get the event time
        time = get_event_time(GCDQp_packet)

        print("Event `{0}` happened at `{1}`.".format(event_id, str(time)))

        print("Publishing events to   {}".format(topic))
        print("Publishing metadata to {}<...>".format(metadata_topic_base))

        print("Submitting scan...")
        send_scan(
            frame_packet=GCDQp_packet,
            broker=broker,
            auth_token=auth_token,
            topic=topic,
            metadata_topic_base=metadata_topic_base,
            event_name=event_name,
            nside=nside,
            area_center_nside=area_center_nside,
            area_center_pixel=area_center_pixel,
            area_num_pixels=area_num_pixels,
            pixel_list=pixel_list,
        )

        print("All scans for `{0}` are submitted.".format(event_id))
    except:
        exception_message = (
            str(sys.exc_info()[0])
            + "\n"
            + str(sys.exc_info()[1])
            + "\n"
            + str(sys.exc_info()[2])
        )
        print(
            "Something went wrong while scanning the event (python caught an exception): ```{0}```".format(
                exception_message
            )
        )
        raise  # re-raise exceptions
