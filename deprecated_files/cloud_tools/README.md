# skymap_scanner/cloud_tools

Distributed likelihood scan of event directions for real-time alerts.
This is a set of scripts meant to be deployed as containers.

Build this with 
```
docker build . -t icecube/skymap_scanner
```

and optionally push it to DockerHub using
```
docker push icecube/skymap_scanner
```

First, start an Apache Pulsar instance (or identify an existing one)
and get its broker or proxy URL.
For testing, you can start your own local instance with this command:
(You want to make sure Pulsar's `brokerDeleteInactiveTopicsEnabled` configuration
parameter is set to false, otherwise topics without a consumer running will be
deleted after 60 seconds.)
```
docker run -it --rm -p 6650:6650 -p 8080:8080 --name pulsar_local apachepulsar/pulsar:2.6.0 /bin/bash -c "sed -i s/brokerDeleteInactiveTopicsEnabled=.*/brokerDeleteInactiveTopicsEnabled=false/ /pulsar/conf/standalone.conf && bin/pulsar standalone"
```

You will need to connect to the pulsar broker using your machine IP,
so find it using a tool like `ifconfig` or `ip addr` and use it below
instead of `<pulsar_ip>`.

Once Pulsar is up and running, make sure the `icecube/skymap` and
`icecube/skymap_metadata` namespaces exist. If you are running a local
instance as described above, you can create it like this
(Deduplication is optional but useful. Retention is necessary.):
```
docker exec -ti pulsar_local bin/pulsar-admin tenants create icecube
docker exec -ti pulsar_local bin/pulsar-admin namespaces create icecube/skymap
docker exec -ti pulsar_local bin/pulsar-admin namespaces set-deduplication icecube/skymap --enable
docker exec -ti pulsar_local bin/pulsar-admin namespaces create icecube/skymap_metadata
docker exec -ti pulsar_local bin/pulsar-admin namespaces set-deduplication icecube/skymap_metadata --enable
docker exec -ti pulsar_local bin/pulsar-admin namespaces set-retention icecube/skymap_metadata --size -1 --time -1

docker exec -ti pulsar_local bin/pulsar-admin topics create-partitioned-topic persistent://icecube/skymap/to_be_scanned --partitions 6
docker exec -ti pulsar_local bin/pulsar-admin topics create-partitioned-topic persistent://icecube/skymap/scanned --partitions 6
```

You can run the producer to send a scan like this. Notice that you are submitting the
event with a specific name that you can use later in order to save all data:

```
docker run --rm -ti icecube/skymap_scanner:latest producer http://icecube:skua@convey.icecube.wisc.edu/data/user/ckopper/event_HESE_2017-11-28.json --broker pulsar://192.168.123.131:6650 --nside 1 -n test_event_01
```

Then you can then start some workers to scan the jobs in the queue:

```
docker run --rm -ti icecube/skymap_scanner:latest worker --broker pulsar://192.168.123.131:6650
```

Finally, since there are 7 jobs per pixel (different reconstruction seeds in absolute position
in the detector), they need to be collected for each pixel. You have to run one
(or several) of these:

```
docker run --rm -ti icecube/skymap_scanner:latest collector --broker pulsar://192.168.123.131:6650
```

Now, you can save the output queue into an .i3 file and have a look at it:
(Note that `saver` will block until all frames have been processed.)

```
docker run --rm -v $PWD:/mnt -ti icecube/skymap_scanner:latest saver --broker pulsar://192.168.123.131:6650 --nside 16 -n test_event_01 -o /mnt/test_event_01.i3
docker run --rm -v $PWD:/mnt -ti icecube/icetray:combo-stable-prod dataio-shovel -l millipede /mnt/test_event_01.i3
```


During testing, you can clean up topics with:
```
docker exec -ti pulsar_local bin/pulsar-admin topics list icecube/skymap
docker exec -ti pulsar_local bin/pulsar-admin topics delete persistent://icecube/skymap/<name>
docker exec -ti pulsar_local bin/pulsar-admin topics list icecube/skymap_metadata
docker exec -ti pulsar_local bin/pulsar-admin topics delete persistent://icecube/skymap_metadata/<name>
```
