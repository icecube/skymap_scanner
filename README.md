# skymap_scanner

Distributed likelihood scan of event directions for real-time alerts. This is a set of scripts meant to be deployed as containers.

Build this with 

```
docker build . -t icecube/skymap_scanner
```

and optionally push it to DockerHub using

```
docker push icecube/skymap_scanner
```

You can run the master server with something like this: 

```
docker run -p 12345:12345 --rm -ti icecube/skymap_scanner master http://icecube:****@convey.icecube.wisc.edu//data/user/ckopper/event_HESE_2017-11-28.json -p 12345
```

The just point workers at the master:

```
docker run --rm -ti icecube/skymap_scanner worker <master_ip> -p 12345
```
