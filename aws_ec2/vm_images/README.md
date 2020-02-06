Run this command in here to create an AMI with pre-staged docker images.
```
packer build ubuntu_docker.json
```


(Make sure you ran `docker build . -t icecube/skymap_scanner` and `docker push icecube/skymap_scanner` before.)
