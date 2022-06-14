"""MQ Tools for use in IceTray

Based on cloud_tools/pulsar_icetray.py
"""

# fmt: off
# pylint: skip-file

import copy
import hashlib
import random
import re
import time

import pulsar
from icecube import dataclasses, icetray


def pulsar_send_return_msgid(producer, content, **kwargs):
    def send_callback(res, msg):
        send_callback.msgid = msg
        send_callback.res = res
    send_callback.msgid=None
    send_callback.res=None

    producer.send_async(content=content, callback=send_callback, **kwargs)

    while send_callback.msgid is None:
      producer.flush()

    if send_callback.res != pulsar.Result.Ok:
        raise RuntimeError("Message send failed")

    return send_callback.msgid


class PulsarClientService():
    def __init__(self,
        BrokerURL='pulsar://localhost:6650', # The Apache Pulsar broker URL
        AuthToken=None, # The Apache Pulsar authentication token to use
        logger=None
        ):

        # connect to the broker
        if AuthToken is not None:
            self._client = pulsar.Client(
                service_url=BrokerURL,
                authentication=pulsar.AuthenticationToken(AuthToken)
                )
        else:
            self._client = pulsar.Client(
                service_url=BrokerURL
                )

        self._broker_url = BrokerURL

    def get(self):
        return self._client

    def broker_url(self):
        return self._broker_url

    def __del__(self):
        self._client.close()
        del self._client

    def __str__(self):
        return "<PulsarClientService instance>"

    def __repr__(self):
        return "<PulsarClientService instance>"

class SendPFrame(icetray.I3Module):
    def __init__(self, ctx):
        super(SendPFrame, self).__init__(ctx)
        self.AddParameter("ClientService", "A PulsarClientService instance encapsulating the Apache Pulsar connection", None)

        self.AddParameter("Topic", "The Apache Pulsar topic to send to (can be either a string or a function converting an input topic name to an output name)", None)
        self.AddParameter("PartitionKey", "A function or string (or None) with the partition key for this frame. All frames with the same partition key end up in the same topic partition.", None)

        self.AddParameter("SendToSinglePartitionIndex", "Choose a single partition and stick with it forever.", None)

        self.AddParameter("ProducerName", "Name of the producer (uses a random unique name if not specified)", None)
        self.AddParameter("I3IntForSequenceID", "Name of the I3Int frame object to use as a unique sequence ID within the topic. We will use a simple P-frame counter if nothing is specified. Make sure to use a unique ID object if you use a ProducerName and you are not sure you are the only producer.", None)

        self.AddParameter("IgnoreStops", "Ignore these frame stream stops", [icetray.I3Frame.Stream('\03')])

        self.AddParameter("ProducerCacheSize", "The maximum number of (dynamic) producer connections to keep open", 5)

        self.AddOutBox("OutBox")

    def Configure(self):
        self.client_service = self.GetParameter("ClientService")

        self.topic = self.GetParameter("Topic")
        self.partition_key = self.GetParameter("PartitionKey")

        self.send_to_single_partition_index = self.GetParameter("SendToSinglePartitionIndex")

        self.producer_name = self.GetParameter("ProducerName")
        self.i3int_for_sequence_id = self.GetParameter("I3IntForSequenceID")

        self.ignore_stops = self.GetParameter("IgnoreStops")

        self.producer_cache_size = self.GetParameter("ProducerCacheSize")

        if self.client_service is None:
            raise RuntimeError("You have to provide a ClientService parameter to SendPFrame")

        # first, connect to the broker
        self.client = self.client_service.get()

        if callable(self.topic):
            # topic is a function, so let's initialize self.producer lazily later
            self.producer = None
            self.producer_cache = []
        elif isinstance(self.topic, str):
            # create a producer now, there is only one topic
            self.producer = self.create_producer(self.topic)
        else:
            raise RuntimeError("Topic parameter needs to be either a callable or a string")

        # Initialize an event counter so we have a unique sequence id
        # for each frame we push. (We will use this if the user did
        # not configure anything else.)
        self.event_number = 0

    def create_producer(self, topic_name):
        if self.send_to_single_partition_index is None:
            final_topic = topic_name
        elif isinstance(self.send_to_single_partition_index, str) and (self.send_to_single_partition_index == 'random'):
            all_partitions = self.client.get_topic_partitions(
                topic=topic_name
            )

            final_topic = random.choice(all_partitions)
            print("Randomly chose to send to partition {} (out of {})".format(final_topic, all_partitions))
        else:
            # get all partition names
            all_partitions = self.client.get_topic_partitions(
                topic=topic_name
            )

            # sort the partition names into an array by their partition index number
            sorted_partitions = [None] * len(all_partitions)
            for entry in all_partitions:
                split_topic_name = entry.split('-')
                if (len(split_topic_name) < 3) or (split_topic_name[-2] != 'partition'):
                    raise RuntimeError("Unexpected topic partition name: {}".format(final_topic))
                partition_index = int(split_topic_name[-1])

                if sorted_partitions[partition_index] is not None:
                    raise RuntimeError("Two partition names have the same index! new:{} old:{}".format(entry, sorted_partitions[partition_index]))

                sorted_partitions[partition_index] = entry

            final_topic = all_partitions[self.send_to_single_partition_index]
            print("Chose to send to partition {} (index {}) (out of {})".format(final_topic, self.send_to_single_partition_index, all_partitions))

        # Create the producer we will use to send messages.
        producer = self.client.create_producer(
            topic=final_topic,
            producer_name=self.producer_name,
            send_timeout_millis=0,
            block_if_queue_full=True,
            batching_enabled=True,
            compression_type=pulsar.CompressionType.ZSTD
            )
        # sanity check
        if self.producer_name is None:
            if producer.last_sequence_id() != -1:
                raise RuntimeError("No producer name is set, so we were assigned one by Pulsar. However, we did get a starting sequence offset which is unexpected for a globally unique name. last_sequence_id=={}".format( producer.last_sequence_id()))
        return producer

    def send_physics(self, frame):

        if callable(self.topic):
            # We need to dynamically generate the topic from information in the P-frame
            # if self.topic is a function (instead of a fixed string name).
            new_topic = self.topic(frame) # call the callback function to retrieve a new topic name

            # see if it exists in the cache
            new_producer = None
            for entry in self.producer_cache:
                if entry[0] == new_topic:
                    new_producer = entry[1]
                    break
            # not found in cache, create a new producer
            if new_producer is None:
                # make sure to expunge old items
                while len(self.producer_cache)+1 > self.producer_cache_size:
                    removed_item = self.producer_cache.pop(0) # remove the frontmost item
                    icetray.logging.log_debug("disconnecting old producer for topic {}...".format(removed_item[0]), unit=__name__)
                    removed_item[1].close()
                    del removed_item
                    icetray.logging.log_debug("disconnected.", unit=__name__)

                icetray.logging.log_debug("connecting producer to new topic {}...".format(new_topic), unit=__name__)
                new_producer = self.create_producer(new_topic)
                icetray.logging.log_debug("connected.", unit=__name__)
                self.producer_cache.append( (new_topic, new_producer) )

            # now set the producer to use
            self.producer = new_producer

        # serialize the frame
        frame_copy = copy.copy(frame)
        frame_copy.purge() # remove non-native stops
        data = frame_copy.dumps()
        del frame_copy

        # determine the sequence id
        if self.i3int_for_sequence_id is None:
            # use the event counter if nothing else is configured
            sequence_id = self.event_number
        else:
            if self.i3int_for_sequence_id not in frame:
                raise RuntimeError("I3Int \"{}\" to be used for sequence ID is not in frame.".format(self.i3int_for_sequence_id))
            sequence_id = frame[self.i3int_for_sequence_id].value

        # figure out the partition key
        if self.partition_key is None:
            this_partition_key = None
        elif callable(self.partition_key):
            this_partition_key = self.partition_key(frame)
            if not isinstance(this_partition_key, str):
                raise RuntimeError("PartitionKey callback did not return a string")
        elif isinstance(self.partition_key, str):
            this_partition_key = self.partition_key
        else:
            raise RuntimeError("PartitionKey parameter needs to be either a callable, a string or None")

        ignore = False
        if self.producer_name is not None:
            if sequence_id <= self.producer.last_sequence_id():
                ignore = True

        if not ignore:
            self.producer.send(
                content=data,
                properties={'GCD_url': 'or something like that'},  # TODO - we need to attach GCD info here
                sequence_id=sequence_id,
                partition_key=this_partition_key
                )
            icetray.logging.log_debug("physics frame sent -> sequence {}".format(sequence_id), unit=__name__)
        else:
            icetray.logging.log_debug("physics frame NOT sent because sequence is being re-started after sequence id {} -> sequence id {}".format(self.producer.last_sequence_id(), sequence_id), unit=__name__)

        self.event_number += 1


    def Process(self):
        frame = self.PopFrame()
        if frame is None:
            raise RuntimeError("AcknowledgeReceivedPFrame did not receive a frame")

        if frame.Stop in self.ignore_stops:
            # ignore, just push it and exit
            self.PushFrame(frame)
            return

        if frame.Stop == icetray.I3Frame.Physics:
            # it's a Physics frame
            self.send_physics(frame)

        self.PushFrame(frame)

    def Finish(self):
        if self.producer is not None:
            self.producer.close()
        if self.producer is not None:
            del self.producer

# Instantiate this service and use the same instance for
# ReceivePFrame and AcknowledgeReceivedPFrame.
class ReceiverService():
    def __init__(self,
        topic, # The Apache Pulsar topic name to receive frames from
        client_service, # An PulsarClientService instance for the pulsar connection
        subscription_name='skymap-worker-sub', # Name of the subscription
        force_single_consumer=False,
        topic_is_regex=False,
        subscribe_to_single_random_partition=False,
        receiver_queue_size=None
        ):

        self._client = client_service.get()

        if force_single_consumer:
            consumer_type = pulsar.ConsumerType.Failover
            icetray.logging.log_debug("Creating consumer with a Failover subscription named {}".format(subscription_name), unit=__name__)
        else:
            consumer_type = pulsar.ConsumerType.Shared
            icetray.logging.log_debug("Creating consumer with a Shared subscription named {}".format(subscription_name), unit=__name__)

        if topic_is_regex and subscribe_to_single_random_partition:
            raise RuntimeError("Subscribing to a regex topic and selecting only a single topic simultaneously is not supported")

        if topic_is_regex:
            use_topic = re.compile(topic)
        else:
            use_topic = topic

        max_total_receiver_queue_size_across_partitions = 50000

        if subscribe_to_single_random_partition:
            # subscribe to *one* of the partitions
            all_partitions = self._client.get_topic_partitions(
                topic=use_topic
            )

            final_topic = random.choice(all_partitions)

            if len(all_partitions) == 0:
                self._chosen_partition_index = 0
                self._chosen_partition = final_topic
            else:
                split_topic_name = final_topic.split('-')
                if (len(split_topic_name) < 3) or (split_topic_name[-2] != 'partition'):
                    raise RuntimeError("Unexpected topic partition name: {}".format(final_topic))
                self._chosen_partition_index = int(split_topic_name[-1])
                self._chosen_partition = final_topic

            print("Chose to read from partition {}: index {} (out of {})".format(final_topic, self._chosen_partition_index, all_partitions))

            if receiver_queue_size is None:
                receiver_queue_size = 1 # TODO: can we use 0 here? might need to get rid of the timeout below
                max_total_receiver_queue_size_across_partitions = 1
        else:
            # subscribe to *all* partitions
            final_topic = use_topic
            if receiver_queue_size is None:
                receiver_queue_size = 1
                max_total_receiver_queue_size_across_partitions
            self._chosen_partition_index = None
            self._chosen_partition = final_topic

        self._consumer = self._client.subscribe(
            topic=final_topic,
            subscription_name=subscription_name,
            receiver_queue_size=receiver_queue_size,
            max_total_receiver_queue_size_across_partitions=max_total_receiver_queue_size_across_partitions,
            consumer_type=consumer_type,
            initial_position=pulsar.InitialPosition.Earliest
            )

        icetray.logging.log_debug("Set up consumer for topic \"{}\".".format(final_topic, client_service.broker_url()), unit=__name__)


        self.message_in_flight_dict = {}

    def chosen_partition_index(self):
        return self._chosen_partition_index

    def chosen_partition(self):
        return self._chosen_partition

    def client(self):
        return self._client

    def consumer(self):
        return self._consumer

    def __del__(self):
        self._consumer.close()
        del self._consumer

    def __str__(self):
        return "<ReceiverService instance>"

    def __repr__(self):
        return "<ReceiverService instance>"

class ReceivePFrame(icetray.I3Module):
    def __init__(self, ctx):
        super(ReceivePFrame, self).__init__(ctx)
        self.AddParameter("ReceiverService", "An instance of ReceiverService owning the broker connection", None)
        self.AddParameter("MaxCacheEntriesPerFrameStop", "The number of entries this service can cache per frame stop", 10)

        self.AddOutBox("OutBox")

    def Configure(self):
        self.receiver_service = self.GetParameter("ReceiverService")
        if self.receiver_service is None:
            raise RuntimeError("Have to provide a `ReceiverService` to ReceivePFrame")

        self.max_entries_per_frame_stop = self.GetParameter("MaxCacheEntriesPerFrameStop")

    def Process(self):
        # driving module - we will be called repeatedly by IceTray with no input frames
        if self.PopFrame():
            raise RuntimeError("ReceivePFrame needs to be used as a driving module")

        # icetray.logging.log_debug("Waiting for message...", unit=__name__)

        # Make `receive()` time out, but retry indefinitely to make sure
        # we pick up newly created topics.
        try:
            msg = self.receiver_service.consumer().receive(timeout_millis=500)
        except Exception as e:
            if str(e) == "Pulsar error: TimeOut":
                # Re-try by just returning from Process() without pushing a frame.
                # We will be called again.
                return
            else:
                # some other exception. re-raise.
                raise

        msgid = msg.message_id()
        icetray.logging.log_debug("Message received. [msgid={}, topic={}]".format(msgid, msg.topic_name()), unit=__name__)
        serialized_msgid = msgid.serialize()

        # make sure we do not work on a message we are already working on
        if serialized_msgid in self.receiver_service.message_in_flight_dict:
            icetray.logging.log_debug("Message is already being processed. Ignoring. [msgid={}, topic={}]".format(msgid, msg.topic_name()), unit=__name__)
            # self.receiver_service.consumer().acknowledge(msg)

        # retrieve the GCD stuff
        gcd_url = msg.properties()
        # TODO - get GCD frame from url (or a cache, but abstract that away)
        gcd_frame = object()
        frame = icetray.I3Frame()
        # TODO - log
        self.PushFrame(frame.loads(gcd_frame))

        # now load the actual P-frame and push it
        frame = icetray.I3Frame()
        frame.loads(msg.data())

        icetray.logging.log_debug("Pushing frame stop {}[should be Physics] [msgid={}]".format(frame.Stop, msgid), unit=__name__)
        self.PushFrame(frame)
        del frame # make sure to not re-use this frame, the frmework will mess with it

        # save a copy of the message in flight
        self.receiver_service.message_in_flight_dict[serialized_msgid] = msg

        # also push a special delimiter frame with the msgid so we can acknowledge it at the
        # end of the tray
        delimiter_frame = icetray.I3Frame(icetray.I3Frame.Stream('\03'))
        delimiter_frame['__msgid'] = dataclasses.I3String( serialized_msgid )
        icetray.logging.log_debug("Pushing frame stop '\\03' [\"__msgid\"={}]".format(msgid), unit=__name__)
        self.PushFrame(delimiter_frame)

    def Finish(self):
        del self.receiver_service

class AcknowledgeReceivedPFrame(icetray.I3Module):
    def __init__(self, ctx):
        super(AcknowledgeReceivedPFrame, self).__init__(ctx)
        self.AddParameter("ReceiverService", "An instance of ReceiverService owning the broker connection", None)

    def Configure(self):
        self.receiver_service = self.GetParameter("ReceiverService")
        if self.receiver_service is None:
            raise RuntimeError("Have to provide a `ReceiverService` to AcknowledgeReceivedPFrame")

    def Process(self):
        frame = self.PopFrame()
        if frame is None:
            raise RuntimeError("AcknowledgeReceivedPFrame did not receive a frame")

        if frame.Stop == icetray.I3Frame.Stream('\03'):
            if '__msgid' not in frame:
                raise RuntimeError("Expected \"__msgid\" frame object in special delimiter ('\\03') frame")
            msgid_str = frame["__msgid"].value
            msgid = pulsar.MessageId.deserialize(msgid_str)

            if msgid_str not in self.receiver_service.message_in_flight_dict:
                raise RuntimeError("Message id {} was not in flight, cannot acknowledge.".format(str(msgid)))

            # retrieve and remove message from dictionary
            msg = self.receiver_service.message_in_flight_dict[msgid_str]
            del self.receiver_service.message_in_flight_dict[msgid_str]

            icetray.logging.log_debug("Delimiter frame received. Acknowledging message id {}.".format(str(msgid)), unit=__name__)
            self.receiver_service.consumer().acknowledge(msg)
            icetray.logging.log_debug("Acknowledged.", unit=__name__)

        self.PushFrame(frame)

    def Finish(self):
        del self.receiver_service
