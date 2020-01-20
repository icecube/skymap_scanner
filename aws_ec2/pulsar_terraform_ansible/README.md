Install the necessary tools and configure AWS.
```
brew install awscli terraform ansible terraform-inventory
awscli configure
```

```
git clone https://github.com/apache/pulsar --branch v2.5.0
cd pulsar/deployment/terraform-ansible/aws
```

If you do not have one, set up an AWS ssh key using the console and copy it somewhere.
Mine is in `~/.ssh/id_rsa`  /  `~/.ssh/id_rsa.pub`


Update terraform.tfvars with the correct AMI, region and availability zone (AZ).
We use `us-east-2` / `us-east-2c`.
Find the ami-id corresponding to `RHEL-7.4_HVM_GA-20170808-x86_64-2-Hourly2-GP2`
and use it (consider using Centos instead).

```
terraform init
terraform apply
```

This should return the IPs/URLs. For me, these are:
```
  dns_name_internal = internal-pulsar-elb-internal-997200071.us-east-2.elb.amazonaws.com
  pulsar_service_url_internal = pulsar://internal-pulsar-elb-internal-997200071.us-east-2.elb.amazonaws.com:6650
  pulsar_web_url_internal = http://internal-pulsar-elb-internal-997200071.us-east-2.elb.amazonaws.com:8080
```

Now run the playbook:
```
TF_STATE=./ ansible-playbook \
  --user='ec2-user' \
  --inventory=`which terraform-inventory` \
  deploy-pulsar.yaml
```

Now you also have to make sure to create a VPC peering connection between the
newly created pulsar VPC and the VPC you are going to use for your other work.
You will need to create a peering connection and adapt the routing tables on
both ends.

Now connect to create a basic tenant and namespace with configuration:
```
ssh ec2-user@18.191.134.83
alias pulsar-admin='sudo /opt/pulsar/bin/pulsar-admin --admin-url http://internal-pulsar-elb-internal-997200071.us-east-2.elb.amazonaws.com:8080'
pulsar-admin tenants create icecube
pulsar-admin namespaces create icecube/skymap
pulsar-admin namespaces create icecube/skymap_metadata
pulsar-admin namespaces set-retention icecube/skymap_metadata --size -1 --time -1
```

If you want to use pulsar-admin from a different host, you could use docker to get access
to pulsar-admin instead.
This can be used from remote hosts to administer the pulsar cluster:
```
alias pulsar-admin='sudo docker run --rm -ti apachepulsar/pulsar:2.5.0 bin/pulsar-admin --admin-url http://internal-pulsar-elb-internal-997200071.us-east-2.elb.amazonaws.com:8080'
pulsar-admin tenants create icecube
pulsar-admin namespaces create icecube/skymap
pulsar-admin namespaces create icecube/skymap_metadata
pulsar-admin namespaces set-retention icecube/skymap_metadata --size -1 --time -1
```
