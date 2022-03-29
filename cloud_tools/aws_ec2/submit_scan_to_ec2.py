#!/usr/bin/env python3

from __future__ import print_function
import sys
import os
import io
import hashlib
import base64
import time
import math
import random
from datetime import datetime, timedelta
import contextlib
import argparse
import asyncio
from textwrap import dedent

import boto3
import botocore


class Specs(dict):
    """Default ec2 instance specs"""
    def __init__(self):
        super(Specs, self).__init__()
        self['ami'] = 'ami-0d987ffbb488908b0'
        self['instance_types'] = {
            't3a.small': {'max_price': '0.008', 'cores': 1},
        }
        self['hours'] = 16
        self['keypair'] = 'claudiok'
        self['region'] = 'us-east-2'
        self['public_zones'] = {
            'us-east-2a': 'subnet-0b284de90164ece23',
            'us-east-2b': 'subnet-07e62479ad8964a27',
            'us-east-2c': 'subnet-01b1763702ded170c',
        }
        self['private_zones'] = {
            'us-east-2a': 'subnet-0c5b40d944c5db6d0',
            'us-east-2b': 'subnet-02ffde5210f3ddf53',
            'us-east-2c': 'subnet-0fa2166b9bf3b0011',
        }
        self['security_group'] = 'sg-1affe374' # make sure the VPC this is running in has an Endpoint to S3
        self['fleet_role'] = 'arn:aws:iam::085443031105:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet'


def format_user_data(text):
    text = dedent(text)
    if sys.version_info[0] < 3:
        return base64.b64encode(text)
    else:
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')


class Instance:
    """Wrapper for ec2 instance"""
    def __init__(self, ec2, user_data, spec, public=False, spot=True, termination_not_an_error=False, name='server'):
        self.ec2 = ec2
        self.user_data = user_data
        self.spec = spec
        self.public = public
        self.name = name
        self.spot = spot
        self.termination_not_an_error = termination_not_an_error

        self.request_id = None
        self.instance_id = None
        self.zone = None
        self.dnsname = None
        self.ipv6_address = None
        self.ipv4_address = None

    async def __aenter__(self):
        """
        Create and wait to come up.
        """
        if self.public:
            zones = self.spec['public_zones']
        else:
            zones = self.spec['private_zones']
        self.zone = random.choice(list(zones.keys()))

        if self.spot:
            ret = self.ec2.request_spot_instances(
                DryRun=False,
                SpotPrice=self.spec['price'],
                InstanceCount=1,
                Type='one-time',
                InstanceInterruptionBehavior='terminate',
                BlockDurationMinutes=int(math.ceil(self.spec['hours'])*60),
                LaunchSpecification={
                    'ImageId': self.spec['ami'],
                    'KeyName': self.spec['keypair'],
                    'Placement': {
                        'AvailabilityZone': self.zone
                    },
                    'NetworkInterfaces': [
                        {
                            'AssociatePublicIpAddress': self.public, # for ipv4
                            'DeleteOnTermination': True,
                            'DeviceIndex': 0,
                            'Groups': [self.spec['security_group']],
                            'Ipv6AddressCount': 1,
                            'SubnetId': zones[self.zone],
                        }
                    ],
                    'UserData': format_user_data(self.user_data),
                    'InstanceType': self.spec['instance_type'],
                }
            )
            self.request_id = ret['SpotInstanceRequests'][0]['SpotInstanceRequestId']
            try:
                self.instance_id = ret['SpotInstanceRequests'][0]['InstanceId']
            except Exception:
                self.instance_id = None
        else:
            ret = self.ec2.run_instances(
                DryRun=False,
                InstanceInitiatedShutdownBehavior='terminate',
                InstanceType=self.spec['instance_type'],
                UserData=dedent(self.user_data),
                KeyName=self.spec['keypair'],
                Placement = {
                    'AvailabilityZone': self.zone
                },
                NetworkInterfaces = [{
                    'AssociatePublicIpAddress': self.public, # for ipv4
                    'DeleteOnTermination': True,
                    'DeviceIndex': 0,
                    'Groups': [self.spec['security_group']],
                    'Ipv6AddressCount': 1,
                    'SubnetId': zones[self.zone],
                }],
                TagSpecifications = [{
                    'ResourceType': 'instance',
                    'Tags' : [{
                        'Key': 'Name',
                        'Value': self.name
                    }]
                }],
                ImageId=self.spec['ami'],
                MinCount=1,
                MaxCount=1)
            self.instance_id = ret['Instances'][0]['InstanceId']
            if not self.instance_id: raise Exception("Instance could not be created")
            self.request_id = None
            
        await asyncio.sleep(1)

        try:
            if self.spot:
                while not self.instance_id:
                    print(self.name, 'waiting for spot instance creation')
                    ret = self.ec2.describe_spot_instance_requests(
                        SpotInstanceRequestIds=[self.request_id],
                    )
                    try:
                        self.instance_id = ret['SpotInstanceRequests'][0]['InstanceId']
                    except Exception:
                        self.instance_id = None
                    if not self.instance_id:
                        if 'Status' in ret['SpotInstanceRequests'][0] and 'Message' in ret['SpotInstanceRequests'][0]['Status']:
                            print(self.name, '  ', ret['SpotInstanceRequests'][0]['Status']['Message'])
                        await asyncio.sleep(10)

                # set the instance name
                self.ec2.create_tags(
                    DryRun=False,
                    Resources=[self.instance_id],
                    Tags=[{
                        'Key': 'Name',
                        'Value': self.name
                    }]
                )

            while True:
                print(self.name, 'waiting for server startup')
                ret = self.ec2.describe_instances(
                    InstanceIds=[self.instance_id],
                )
                state = ret['Reservations'][0]['Instances'][0]['State']['Name']
                if state == 'pending':
                    await asyncio.sleep(10)
                    continue
                if state != 'running':
                    raise Exception("State after `pending` is unexpected (expected `running`): {}".format(state))
                # we are done!
                break

            while not self.ipv6_address:
                print(self.name, 'waiting for server startup')
                ret = self.ec2.describe_instances(
                    InstanceIds=[self.instance_id],
                )
                try:
                    self.dnsname = ret['Reservations'][0]['Instances'][0]['PublicDnsName']
                    self.ipv4_address = ret['Reservations'][0]['Instances'][0]['PrivateIpAddress']
                    for interface in ret['Reservations'][0]['Instances'][0]['NetworkInterfaces']:
                        self.ipv6_address = interface['Ipv6Addresses'][0]['Ipv6Address']
                        if self.ipv6_address:
                            break
                except Exception:
                    self.dnsname = None
                    self.ipv6_address = None
                    self.ipv4_address = None
                if not self.ipv6_address:
                    await asyncio.sleep(5)
                    
        except (KeyboardInterrupt,Exception):
            if self.request_id:
                self.ec2.cancel_spot_instance_requests(
                    SpotInstanceRequestIds=[self.request_id],
                )
            if self.instance_id:
                self.ec2.terminate_instances(
                    InstanceIds=[self.instance_id],
                )
            raise

        print(self.name, 'started', self.dnsname, self.ipv6_address, self.ipv4_address)

    async def monitor(self, timeout=10000000000000000, frequency_seconds=60):
        """Monitor instance and die after `timeout` seconds."""
        end_time = time.time()+timeout
        while self.instance_id and time.time() < end_time:
            ret = self.ec2.describe_instances(
                InstanceIds=[self.instance_id],
            )
            state = ret['Reservations'][0]['Instances'][0]['State']['Name']
            try:
                assert state == 'running'
            except Exception:
                print(self.name, 'instance seems to be not running. (state={}) about to quit monitor()'.format(state))
                self.instance_id = None
            else:
                await asyncio.sleep(frequency_seconds)
        
        if self.termination_not_an_error:
            print(self.name, 'instance terminated')
        else:
            raise Exception(f'{self.name} instance terminated unexpectedly')

    async def __aexit__(self, exc_type, exc, tb):
        print(self.name, 'instance termination requested')
        if self.request_id:
            print(self.name, 'canceling spot instance request')
            self.ec2.cancel_spot_instance_requests(
                SpotInstanceRequestIds=[self.request_id],
            )
            print(self.name, 'spot instance request canceled')
        if self.instance_id:
            print(self.name, 'terminating instance')
            self.ec2.terminate_instances(
                InstanceIds=[self.instance_id],
            )
            print(self.name, 'instance terminated')
        

class SpotFleet:
    """Wrapper for ec2 spot fleet"""
    def __init__(self, ec2, user_data, spec, num=1, name='fleet'):
        self.ec2 = ec2
        self.user_data = user_data
        self.spec = spec
        self.num = num
        self.name = name

        self.fleet_id = None

    async def __aenter__(self):
        """
        Create and wait to come up.
        """
        user_data_b64 = format_user_data(self.user_data)

        date_from = datetime.utcnow()
        date_to = date_from + timedelta(hours=self.spec['hours'])

        launch_specs = []
        for inst in self.spec['instance_types']:
            for zone in self.spec['private_zones']:
                launch_specs.append({
                    'ImageId': self.spec['ami'],
                    'KeyName': self.spec['keypair'],
                    'Placement': {
                        'AvailabilityZone': zone
                    },
                    'NetworkInterfaces': [
                        {
                            'AssociatePublicIpAddress': False,
                            'DeleteOnTermination': True,
                            'DeviceIndex': 0,
                            'Groups': [self.spec['security_group']],
                            'Ipv6AddressCount': 1,
                            'SubnetId': self.spec['private_zones'][zone],
                        }
                    ],
                    'UserData': user_data_b64,
                    'InstanceType': inst,
                    'SpotPrice': self.spec['instance_types'][inst]['max_price'],
                    'WeightedCapacity': self.spec['instance_types'][inst]['cores'],
                    'TagSpecifications':  [
                        {
                            'ResourceType': 'instance',
                            'Tags' : [{
                                'Key': 'Name',
                                'Value': self.name
                            }]
                        }
                    ],
                })

        request = self.ec2.request_spot_fleet(
            SpotFleetRequestConfig={
                'TargetCapacity': self.num,
                'ValidFrom': date_from.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'ValidUntil':  date_to.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'TerminateInstancesWithExpiration': True,
                'IamFleetRole': self.spec['fleet_role'],
                'LaunchSpecifications': launch_specs,
                'Type': 'maintain',
                'AllocationStrategy': 'lowestPrice',
                # 'InstancePoolsToUseCount': len(launch_specs)
            }
        )
        self.fleet_id = request['SpotFleetRequestId']
        print('fleet success:', self.fleet_id)

    
    async def monitor(self, timeout=10000000000000000):
        """Monitor instance and die after `timeout` seconds."""
        end_time = time.time()+timeout
        while self.instance_id and time.time() < end_time:
            ret = self.ec2.describe_instances(
                InstanceIds=[self.instance_id],
            )
            try:
                assert ret['Reservations'][0]['Instances'][0]['State']['Name'] == 'running'
            except Exception:
                self.instance_id = None
            else:
                await asyncio.sleep(60)
        raise Exception('fleet terminated')

    async def __aexit__(self, exc_type, exc, tb):
        if self.fleet_id:
            print('terminating spot fleet')
            self.ec2.cancel_spot_fleet_requests(
                SpotFleetRequestIds=[self.fleet_id],
                TerminateInstances=True,
            )
            print('fleet terminated')


class TempS3File:
    """Upload a file for temporary use to an S3 bucket"""
    def __init__(self, s3, bucket, data=None, filename=None, url_expiration_sec=3600):
        self.s3 = s3
        self.bucket = bucket
        self.data = data
        self.filename = filename
        self.object_name = None
        self.uuid = None
        self.url_expiration_sec = url_expiration_sec
        self.obj_url = None

    async def __aenter__(self):
        """
        Upload to s3 bucket
        """
        
        if self.data is None and self.filename is not None:
            print('reading input data from {}'.format(self.filename))
            with open(self.filename, 'rb') as f:
                self.data = f.read()
        
        # create a temporary object name
        uuid = hashlib.sha256(self.data).hexdigest()
        object_name = uuid + '.dat'
        print('will upload data as {} to bucket {}'.format(object_name, self.bucket))
        
        fo = io.BytesIO(self.data)
        try:
            response = self.s3.upload_fileobj(fo, self.bucket, object_name)
        except ClientError as e:
            print('upload failed.')
            del fo
            self.data = None
            raise

        self.object_name = object_name
        self.uuid = uuid
        
        print('upload success. creating pre-signed URL..')
        
        response = self.s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': self.bucket,
                    'Key': self.object_name},
            ExpiresIn=self.url_expiration_sec)

        assert response is not None
        
        self.obj_url = response

        print('success.')
                                

    async def __aexit__(self, exc_type, exc, tb):
        if self.object_name:
            print('deleting s3 object')
            self.s3.delete_object(
                Bucket=self.bucket,
                Key=self.object_name
            )
            print('s3 object deleted')

def create_presigned_put_url(s3, bucket, key, timeout_hours=24):
    return s3.generate_presigned_url(
        'put_object', 
        Params={'Bucket':bucket,'Key':key}, 
        ExpiresIn=3600*timeout_hours, 
        HttpMethod='PUT'
        )


async def main():
    parser = argparse.ArgumentParser(description='launch ec2 pool')
    parser.add_argument('-f', '--in-file', help="input .i3 data in JSON format",
                        type=str, default=None)
    parser.add_argument('-n','--num', default=1, type=int,
                        help='number of servers in the worker pool')
    parser.add_argument('--collector-num', default=2, type=int,
                        help='number of servers in the collector pool')
    parser.add_argument('-b','--bucket', default='icecube-skymap-staging',
                        type=str, help='S3 bucket name for temporary file upload')
    parser.add_argument('-o','--outbucket', default='icecube-skymap-output',
                        type=str, help='S3 bucket name for final output')
    parser.add_argument('-i','--nside', default=1, type=int,
                        help='Healpix nside (number of pixels is 12*nside^2)')
    parser.add_argument('-p','--pulsar', default="pulsar+ssl://pulsar.api.icecube.aq:6651",
                        type=str, help='Pulsar server URL')
    parser.add_argument('-t','--token', default=None,
                        type=str, help='Pulsar authentication token')
    args = vars(parser.parse_args())

    if args['token'] is None:
        parser.error('You need to specify a pulsar authentication token --token=<token>')
    
    session = boto3.session.Session()

    spec = Specs()
    s3 = session.client(
        service_name='s3',
        region_name=spec['region'],
        config=botocore.client.Config(signature_version='s3v4')
    )
    ec2 = session.client(
        service_name='ec2',
        region_name=spec['region']
    )


    producer_spec = spec.copy()
    producer_spec['instance_type'] = 't2.small'
    producer_spec['price'] = '0.02'
    producer_spec['hours'] = 1
    producer_user_data = """\
    #!/bin/bash

    docker run --rm icecube/skymap_scanner:latest producer '{event_url}' --broker {queue_url} --auth-token {queue_token} --nside {nside} -n event_{uuid}
    shutdown -hP now
    """
    
    collector_spec = spec.copy()
    collector_spec['instance_type'] = 'r5.large'
    collector_spec['instance_types'] = {
        'r5.xlarge':  {'max_price': '0.1', 'cores': 1},
        'r5a.xlarge': {'max_price': '0.1', 'cores': 1},
        'r5n.xlarge': {'max_price': '0.1', 'cores': 1},
        'r4.xlarge':  {'max_price': '0.1', 'cores': 1},
    }

    collector_user_data = """\
    #!/bin/bash

    docker run --rm icecube/skymap_scanner:latest collector --broker {queue_url} --auth-token {queue_token}
    shutdown -hP now
    """
    
    worker_spec = spec.copy()
    worker_spec['instance_type'] = 't3a.small'
    worker_spec['instance_types'] = {
        'c5.4xlarge':   {'max_price': '0.012', 'cores': 16},
        'c5d.4xlarge':  {'max_price': '0.012', 'cores': 16},
        'c5n.4xlarge':  {'max_price': '0.012', 'cores': 16},
        'c5.9xlarge':   {'max_price': '0.012', 'cores': 36},
        'c5d.9xlarge':  {'max_price': '0.012', 'cores': 36},
        'c5n.9xlarge':  {'max_price': '0.012', 'cores': 36},
        'c5d.12xlarge': {'max_price': '0.012', 'cores': 48},
        'c5.18xlarge':  {'max_price': '0.012', 'cores': 72},
        'c5d.18xlarge': {'max_price': '0.012', 'cores': 72},
        'c5n.18xlarge': {'max_price': '0.012', 'cores': 72},
        'm5.4xlarge':   {'max_price': '0.012', 'cores': 16},
        'm5a.4xlarge':  {'max_price': '0.012', 'cores': 16},
        'm5n.4xlarge':  {'max_price': '0.012', 'cores': 16},
        'r5.4xlarge':   {'max_price': '0.012', 'cores': 16},
        'r5a.4xlarge':  {'max_price': '0.012', 'cores': 16},
        'r5n.4xlarge':  {'max_price': '0.012', 'cores': 16},
    }
    worker_user_data = """\
    #!/bin/bash
    
    cat >/root/supervisord.conf <<EOF
    [program:worker]
    command=docker run --rm --name %(program_name)s_%(process_num)02d icecube/skymap_scanner:latest worker --broker {queue_url} --auth-token {queue_token}

    numprocs=%(ENV_NUMPROCS)s
    process_name=%(program_name)s_%(process_num)02d

    stdout_logfile=/var/log/%(program_name)s_%(process_num)02d.log
    stdout_logfile_maxbytes=41943040
    redirect_stderr=true

    autostart=true
    autorestart=true
    stopsignal=INT

    startretries=10

    stopasgroup=true
    killasgroup=true

    [unix_http_server]
    file=/var/run/supervisor.sock
    chmod=0700

    [supervisord]
    logfile=/var/log/supervisor/supervisord.log
    pidfile=/var/run/supervisord.pid
    childlogdir=/var/log/supervisor

    [rpcinterface:supervisor]
    supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

    [supervisorctl]
    serverurl=unix:///var/run/supervisor.sock
    EOF

    NUMPROCS=`nproc` /usr/bin/supervisord --nodaemon -c /root/supervisord.conf
    
    #docker run --rm icecube/skymap_scanner:latest worker --broker {queue_url} --auth-token {queue_token}
    #shutdown -hP now
    """
    
    saver_spec = spec.copy()
    saver_spec['instance_type'] = 'r5.large'
    saver_user_data = """\
    #!/bin/bash

    docker run --rm icecube/skymap_scanner:latest saver --broker {queue_url} --auth-token {queue_token} --nside {nside} -n event_{uuid} -o '{out_url}'
    
    shutdown -hP now
    """

    
    futures = []
    to_await = []
    async with contextlib.AsyncExitStack() as stack:
        if args['in_file'] is not None:
            print('-- uploading input file to S3')
            input_file = TempS3File(s3, args['bucket'], filename=args['in_file'])
            print('-- await')
            await stack.enter_async_context(input_file)
            event_id = input_file.uuid[:12]
            print('-- Event ID: {}'.format(event_id))

            output_file_name = 'scanned_event_{}_nside{}.i3'.format(event_id, args['nside'])
            presigned_output_url = create_presigned_put_url(s3, bucket=args['outbucket'], key=output_file_name, timeout_hours=24)
            # print('-- output presigned url is {}'.format(presigned_output_url))

            print('-- bringing up Instance (producer)')
            producer = Instance(
                ec2,
                producer_user_data.format(
                    queue_url=args['pulsar'],
                    queue_token=args['token'],
                    event_url=input_file.obj_url,
                    nside=args['nside'],
                    uuid=event_id
                ),
                producer_spec,
                spot=True, # this will only run for a very short time while submitting all requests
                termination_not_an_error=True, # not an error if this terminates
                name='producer-' + event_id
            )
            to_await.append(stack.enter_async_context(producer))
            print('-- adding monitoring to futures (producer)')
            futures.append(producer.monitor())


        if args['collector_num'] > 0:
            print('-- bringing up Fleet (collector)')
            collector = SpotFleet(
                ec2,
                collector_user_data.format(
                    queue_url=args['pulsar'],
                    queue_token=args['token'],
                ),
                collector_spec,
                num=args['collector_num'],
                name='collector-fleet'
            )
            to_await.append(stack.enter_async_context(collector))

        if args['in_file'] is not None:
            print('-- bringing up Instance (saver)')
            saver = Instance(
                ec2,
                saver_user_data.format(
                    queue_url=args['pulsar'],
                    queue_token=args['token'],
                    nside=args['nside'],
                    uuid=event_id,
                    out_url=presigned_output_url
                ),
                saver_spec,
                spot=False, # could be long-running, do not use a spot instance
                # termination_not_an_error=True, # not an error if this terminates, in fact - we are done when this terminates
                name='saver-' + event_id
            )
            to_await.append(stack.enter_async_context(saver))
            print('-- adding monitoring to futures (saver)')
            futures.append(saver.monitor())


        if args['num'] > 0:
            print('-- bringing up Fleet (worker)')
            fleet = SpotFleet(
                ec2,
                worker_user_data.format(
                    queue_url=args['pulsar'],
                    queue_token=args['token'],
                ),
                worker_spec, 
                num=args['num'],
                name='worker-fleet'
            )
            to_await.append(stack.enter_async_context(fleet))
        
        print('-- awaiting startup')
        await asyncio.wait(to_await, return_when=asyncio.FIRST_EXCEPTION)
        print('-- startup completed')
        
        if args['in_file'] is None:
            print('-- waiting for spot fleet expiration')
            await asyncio.sleep( worker_spec['hours']*3600 )
            print('-- spot fleet expired')
        
        if len(futures) > 0:
            print('-- awaiting all monitoring futures')
            await asyncio.wait(futures, return_when=asyncio.FIRST_EXCEPTION)
            print('-- done')
        
    print('-- exit')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
