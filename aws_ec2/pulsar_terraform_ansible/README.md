Install the necessary tools and configure AWS.
```
brew install awscli terraform ansible terraform-inventory
awscli configure
```

If you do not have one, set up an AWS ssh key and copy it somewhere.
Mine is in `~/.ssh/id_rsa`  /  `~/.ssh/id_rsa.pub`

Also you need to create a public and private key for pulsar token signing:
```
docker run -v $PWD:/mnt --rm -ti apachepulsar/pulsar:2.5.0 bin/pulsar tokens create-key-pair --output-private-key /mnt/secrets/my-private.key --output-public-key /mnt/secrets/my-public.key
```

Now sign a token to use as the proxy token and another one for the admin user:
```
docker run -v $PWD:/mnt --rm -ti apachepulsar/pulsar:2.5.0 bin/pulsar tokens create --private-key file:///mnt/secrets/my-private.key --subject proxy-user > secrets/proxy-user.token
docker run -v $PWD:/mnt --rm -ti apachepulsar/pulsar:2.5.0 bin/pulsar tokens create --private-key file:///mnt/secrets/my-private.key --subject admin > secrets/admin.token
docker run -v $PWD:/mnt --rm -ti apachepulsar/pulsar:2.5.0 bin/pulsar tokens create --private-key file:///mnt/secrets/my-private.key --subject icecube > secrets/icecube.token
docker run -v $PWD:/mnt --rm -ti apachepulsar/pulsar:2.5.0 bin/pulsar tokens create --private-key file:///mnt/secrets/my-private.key --subject icecube.skymap > secrets/icecube.skymap.token
```

Update terraform.tfvars with the correct AMI, region and availability zone (AZ).
We use `us-east-2` / `us-east-2c` in this example.
Find the ami-id corresponding to the latest Amazon Linux 2, Centos, RHEL, ...

```
terraform init
terraform apply
```

This should return the URL assigned to the load balancer.
```
external_dns_name = pulsar.api.icecube.aq
pulsar_service_url = pulsar+ssl://pulsar.api.icecube.aq:6651
pulsar_web_url = http://pulsar.api.icecube.aq:8443
```

Now run the playbook to actually install pulsar on the provisioned hosts.
```
TF_STATE=./ ansible-playbook --user='ec2-user' --inventory=`which terraform-inventory` deploy-pulsar.yaml
```

Now connect to create a basic tenant and namespace with configuration:
```
ssh ec2-user@<pulsar_client_ip>
alias pulsar-admin='sudo /opt/pulsar/bin/pulsar-admin'
pulsar-admin tenants create --admin-roles icecube icecube
pulsar-admin namespaces create icecube/skymap --bundles 12
pulsar-admin namespaces set-deduplication icecube/skymap --enable
pulsar-admin namespaces create icecube/skymap_metadata --bundles 12
pulsar-admin namespaces set-deduplication icecube/skymap_metadata --enable
pulsar-admin namespaces set-retention icecube/skymap_metadata --size -1 --time -1
pulsar-admin namespaces grant-permission icecube/skymap          --actions produce,consume --role icecube.skymap
pulsar-admin namespaces grant-permission icecube/skymap_metadata --actions produce,consume --role icecube.skymap
pulsar-admin topics create-partitioned-topic persistent://icecube/skymap/to_be_scanned --partitions 6
pulsar-admin topics create-partitioned-topic persistent://icecube/skymap/scanned --partitions 6
```

If you want to use pulsar-admin from a different host, you could use docker to get access
to pulsar-admin instead.
This can be used from remote hosts to administer the pulsar cluster:
```
alias pulsar-admin='docker run --rm -ti apachepulsar/pulsar:2.5.0 bin/pulsar-admin --admin-url https://pulsar.api.icecube.aq:8443 --auth-plugin org.apache.pulsar.client.impl.auth.AuthenticationToken --auth-params token:`cat secrets/admin.token`'
pulsar-admin tenants create --admin-roles icecube icecube
pulsar-admin namespaces create icecube/skymap --bundles 12
pulsar-admin namespaces set-deduplication icecube/skymap --enable
pulsar-admin namespaces create icecube/skymap_metadata --bundles 12
pulsar-admin namespaces set-deduplication icecube/skymap_metadata --enable
pulsar-admin namespaces set-retention icecube/skymap_metadata --size -1 --time -1
pulsar-admin namespaces grant-permission icecube/skymap          --actions produce,consume --role icecube.skymap
pulsar-admin namespaces grant-permission icecube/skymap_metadata --actions produce,consume --role icecube.skymap
pulsar-admin topics create-partitioned-topic persistent://icecube/skymap/to_be_scanned --partitions 6
pulsar-admin topics create-partitioned-topic persistent://icecube/skymap/scanned --partitions 6
```

Once you are ready, use something like this to submit your jobs:

```
./submit_scan_to_ec2.py --num 2 --nside 1 -p pulsar.api.icecube.aq ../resources/scripts/event_HESE_2017-11-28.json
```

You can clear everything and start over from scratch using something like this: 

```
pulsar-admin topics delete-partitioned-topic persistent://icecube/skymap/to_be_scanned
pulsar-admin topics delete-partitioned-topic persistent://icecube/skymap/scanned
pulsar-admin topics list icecube/skymap
pulsar-admin topics delete persistent://icecube/skymap/collected_<...>

pulsar-admin topics create-partitioned-topic persistent://icecube/skymap/to_be_scanned --partitions 6
pulsar-admin topics create-partitioned-topic persistent://icecube/skymap/scanned --partitions 6
```
