#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

public_key_path       = "~/.ssh/id_rsa.pub"
region                = "us-east-2"
availability_zone     = "us-east-2c"
aws_ami               = "ami-02ccb28830b645a41"
num_zookeeper_nodes   = 3
num_bookie_nodes      = 3
num_broker_nodes      = 3
num_proxy_nodes       = 1
base_cidr_block       = "10.0.0.0/16"
external_ssl_cert_arn = "arn:aws:acm:us-east-2:085443031105:certificate/48d43c86-fefe-4378-866c-d50371b96d2f"
external_dns_name     = "pulsar.api.icecube.aq"
route53_zone_id       = "Z10MLEU0KBC5J5"

instance_types      = {
  "zookeeper"   = "t2.small"
  "bookie"      = "i3.xlarge"
  "broker"      = "c5.2xlarge"
  "proxy"       = "c5.2xlarge"
  "client"      = "t2.small"
}
