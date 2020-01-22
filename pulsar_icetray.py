import pickle
import time
import re
import copy
import hashlib

import pulsar

from icecube import icetray, dataclasses

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


class SendPFrameWithMetadata(icetray.I3Module):
    def __init__(self, ctx):
        super(SendPFrameWithMetadata, self).__init__(ctx)
        self.AddParameter("BrokerURL", "The Apache Pulsar broker URL", 'pulsar://localhost:6650')

        self.AddParameter("Topic", "The Apache Pulsar topic to send to (can be either a string or a function converting an input topic name to an output name)", None)
        self.AddParameter("PartitionKey", "A function or string (or None) with the partition key for this frame. All frames with the same partition key end up in the same topic partition.", None)

        self.AddParameter("ProducerName", "Name of the producer (random unique name of not specified)", None)
        self.AddParameter("I3IntForSequenceID", "Name of the I3Int frame object to use as a unique sequence ID within the topic. We will use a simple P-frame counter if nothing is specified. Make sure to use a unique ID object if you use a ProducerName and you are not sure you are the only producer.", None)

        self.AddParameter("MetadataTopicBase", "The Apache Pulsar topic for metadata frame information", None)

        self.AddParameter("IgnoreStops", "Ignore these frame stream stops", [icetray.I3Frame.Stream('\03')])

        self.AddOutBox("OutBox")

    def Configure(self):
        self.broker_url = self.GetParameter("BrokerURL")

        self.topic = self.GetParameter("Topic")
        self.partition_key = self.GetParameter("PartitionKey")

        self.producer_name = self.GetParameter("ProducerName")
        self.i3int_for_sequence_id = self.GetParameter("I3IntForSequenceID")

        self.metadata_topic_base = self.GetParameter("MetadataTopicBase")
        self.metadata_producer = None
        
        self.ignore_stops = self.GetParameter("IgnoreStops")
        
        self.producer_cache_size = 5
        
        # first, connect to the broker
        self.client = pulsar.Client(self.broker_url)
        
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

        self.metadata_frames_list = [] # list of dicts

    def create_producer(self, topic_name):
        # Create the producer we will use to send messages.
        producer = self.client.create_producer(
            topic=topic_name,
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
        
    def create_metadata_producer(self, topic_name):
        # Create the producer we will use to send metadata messages.
        producer = self.client.create_producer(
            topic=topic_name,
            send_timeout_millis=0,
            block_if_queue_full=True,
            batching_enabled=False,
            compression_type=pulsar.CompressionType.ZSTD
            )
        return producer

    def add_or_replace_metadata_frame(self, frame):
        known_messageid = None
        known_metadata_topic = None
        
        # check if there is a known messageid/metadata_topic
        # (this could happen because we received this frame
        # earlier and it was read from a metadata queue).
        if ('__msgid' in frame) and ('__msgtopic' in frame):
            known_messageid = frame['__msgid'].value
            known_metadata_topic = frame['__msgtopic'].value
        elif ('__msgid' in frame) or ('__msgtopic' in frame):
            # only one in frame but not the other...
            raise RuntimeError("only one of \"__msgid\" and \"__msgtopic\" in frame, both need to exist")
        
        stop_id = frame.Stop.id
        
        for entry in self.metadata_frames_list:
            if entry['stop'] == stop_id:
                # already in list, replace
                entry['frame'] = frame
                # invalidate the message id (or re-use an existing one if we know it)
                entry['messageid'] = known_messageid 
                entry['metadata_topic'] = known_metadata_topic
                return
        
        # not yet in list, add it
        self.metadata_frames_list.append( {
            'stop': stop_id,
            'frame': frame,
            # invalidate the message id (or re-use an existing one if we know it)
            'messageid': known_messageid,
            'metadata_topic': known_metadata_topic,
            })

    def send_metadata_frames(self):
        for entry in self.metadata_frames_list:
            if entry['messageid'] is not None:
                # nothing to udpate, skip
                continue
            
            if self.metadata_topic_base is None:
                raise RuntimeError("SendPFrameWithMetadata is not configured with the MetadataTopic option. All metadata frames need to have been received from a queue already if you want this to work.")

            frame_copy = copy.copy(entry['frame'])
            frame_copy.purge() # remove non-native stops
            pickled_frame = pickle.dumps(frame_copy)

            if self.metadata_producer is None:
                # We need to create a metadata producer. We base its name on a
                # (heavily truncated) hash of the first (i.e. this) frame.
                # TODO: There is probably a better way. Consider going for per-frame
                # topics (and/or a frame hash as partition key).
                metadata_topic = self.metadata_topic_base + hashlib.sha256(pickled_frame).hexdigest()[:4]
                print("Sending metadata to topic {}".format(metadata_topic))
                self.metadata_producer = self.create_metadata_producer(metadata_topic)
                
            # send the frame and record its generated message id
            msgid = pulsar_send_return_msgid(
                self.metadata_producer,
                content=pickled_frame, 
                )
            
            entry['messageid'] = msgid.serialize()
            entry['metadata_topic'] = metadata_topic
            
            print("metadata frame sent {} -> msgid {}".format(entry['stop'], msgid))

    def send_physics(self, frame):
        # make sure all entries have a 'messageid' set and have the same 'metadata_topic'
        metadata_topic_to_send = None
        for entry in self.metadata_frames_list:
            if (entry['messageid'] is None) or (entry['metadata_topic'] is None):
                raise RuntimeError("logic error: physics frame metadata entry has no messageid set")
            if metadata_topic_to_send is None:
                metadata_topic_to_send = entry['metadata_topic']
            elif metadata_topic_to_send != entry['metadata_topic']:
                raise RuntimeError("internal error: all metadata frames for a physics frame need to be on the same topic")
        
        properties = {
            'metadata': pickle.dumps( [ entry['messageid'] for entry in self.metadata_frames_list ] ),
            'metadata_topic': metadata_topic_to_send,
        }
        
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
                    print("disconnecting old producer for topic {}...".format(removed_item[0]))
                    removed_item[1].close()
                    del removed_item
                    print("disconnected.")

                print("connecting producer to new topic {}...".format(new_topic))
                new_producer = self.create_producer(new_topic)
                print("connected.")
                self.producer_cache.append( (new_topic, new_producer) )

            # now set the producer to use
            self.producer = new_producer
        
        # pickle the frame
        frame_copy = copy.copy(frame)
        frame_copy.purge() # remove non-native stops
        data = pickle.dumps(frame_copy)
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
                properties=properties,
                sequence_id=sequence_id,
                partition_key=this_partition_key
                )
            print("physics frame sent -> sequence {}".format(sequence_id))
        else:
            print("physics frame NOT sent because sequence is being re-started after sequence id {} -> sequence id {}".format(self.producer.last_sequence_id(), sequence_id))

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
            self.send_metadata_frames()
            self.send_physics(frame)
        else:
            # it's a metadata frame such as Geometry, ...
            self.add_or_replace_metadata_frame(frame)

        self.PushFrame(frame)
        
    def Finish(self):
        if self.metadata_producer is not None:
            self.metadata_producer.close()
        if self.producer is not None:
            self.producer.close()
        self.client.close()
        if self.metadata_producer is not None:
            del self.metadata_producer
        if self.producer is not None:
            del self.producer
        del self.client

# Instantiate this service and use the same instance for
# ReceivePFrameWithMetadata and AcknowledgeReceivedPFrame.
class ReceiverService():
    def __init__(self,
        topic, # The Apache Pulsar topic name to receive frames from
        broker_url='pulsar://localhost:6650', # The Apache Pulsar broker URL
        subscription_name='skymap-worker-sub', # Name of the subscription
        force_single_consumer=False,
        topic_is_regex=False,
        ):
        
        # connect to the broker
        self._client = pulsar.Client(broker_url)
        
        if force_single_consumer:
            consumer_type = pulsar.ConsumerType.Failover
            print("Creating consumer with a Failover subscription named {}".format(subscription_name))
        else:
            consumer_type = pulsar.ConsumerType.Shared
            print("Creating consumer with a Shared subscription named {}".format(subscription_name))
        
        if topic_is_regex:
            use_topic = re.compile(topic)
        else:
            use_topic = topic
        
        self._consumer = self._client.subscribe(
            topic=use_topic,
            subscription_name=subscription_name,
            receiver_queue_size=1,
            consumer_type=consumer_type,
            initial_position=pulsar.InitialPosition.Earliest
            )
        
        print("Set up consumer for topic \"{}\" on broker \"{}\".".format(topic, broker_url))


        self.message_in_flight_dict = {}

    def client(self):
        return self._client
        
    def consumer(self):
        return self._consumer
        
    def __del__(self):
        self._consumer.close()
        self._client.close()
        del self._consumer
        del self._client
            
    def __str__(self):
        return "<ReceiverService instance>"
    
    def __repr__(self):
        return "<ReceiverService instance>"

class ReceivePFrameWithMetadata(icetray.I3Module):
    def __init__(self, ctx):
        super(ReceivePFrameWithMetadata, self).__init__(ctx)
        self.AddParameter("ReceiverService", "An instance of ReceiverService owning the broker connection", None)

        self.AddOutBox("OutBox")

    def Configure(self):
        self.receiver_service = self.GetParameter("ReceiverService")
        if self.receiver_service is None:
            raise RuntimeError("Have to provide a `ReceiverService` to ReceivePFrameWithMetadata")

        self.metadata_cache = {}
        self.pushed_metadata_msgids = []
        self.max_entries_per_frame_stop = 10
        
        # the Pulsar metadata reader will be instantiated lazily later
        self.metadata_reader = None
        self.metadata_topic = None

    def is_metadata_msgid_pushed_and_active(self, msgid):
        for entry in self.pushed_metadata_msgids:
            if entry[1] == msgid:
                return True
        return False

    def retrieve_metadata_frame_from_cache(self, msgid):
        for stream, items in self.metadata_cache.items():
            for i in range(len(items)):
                if items[i][0] == msgid:
                    # move to the end of the cache (most recent) for this stream
                    item = items[i]
                    del items[i]
                    items.append(item)
                    
                    print("Frame on Stop {} FOUND in cache. [msgid={}]".format(stream, str(msgid)))
                    return item[1]
        print("Frame not found in cache. [msgid={}]".format(str(msgid)))
        return None

    def add_frame_to_cache(self, frame, msgid):
        frame_stream = frame.Stop.id
        
        if frame_stream not in self.metadata_cache:
            self.metadata_cache[frame_stream] = []
        cache_for_stream = self.metadata_cache[frame_stream]
        
        # add to cache
        cache_for_stream.append( [msgid, frame] )
        print("Added frame on Stop {} to cache. [msgid={}]".format(frame.Stop, str(msgid)))
        
        # delete old entries
        while len(cache_for_stream) > self.max_entries_per_frame_stop:
            # remove the first element
            just_removed = cache_for_stream.pop(0)
            print("Cache too full, removed a message. [Stop={}, msgid={}]".format(just_removed[1].Stop, str(just_removed[0])))
            
        

    def push_metadata_frame_and_update_state(self, frame, msgid):
        frame_stream = frame.Stop.id
        for i in range(len(self.pushed_metadata_msgids)):
            entry = self.pushed_metadata_msgids[i]
            if entry[0] == frame_stream:
                del self.pushed_metadata_msgids[i]
                # start over..
                return self.push_metadata_frame_and_update_state(frame, msgid)
        
        # no elements were deleted, add our frame to the end of the list
        self.pushed_metadata_msgids.append( [ frame_stream, msgid ] )
        
        print("Pushing frame stop {} [msgid={}]".format(frame.Stop, str(msgid)))
        frame_copy = copy.copy(frame) # push a copy, the framework will mess with the frame we push
        self.PushFrame(frame_copy)
        
    def retrieve_metadata_frame_from_pulsar(self, msgid):
        retries = 10
        while True:
            if self.metadata_reader.has_message_available():
                print("Reading metadata frame from pulsar..".format(msgid))
                msg = self.metadata_reader.read_next()
                print("Metadata frame read. It is msgid={}.".format(msg.message_id()))
                if msg.message_id() == msgid:
                    frame = pickle.loads(msg.data())
                    print("Loaded {} frame from pulsar".format(frame.Stop))
                    
                    # add two I3String items to the frame to mark where we got it from
                    frame['__msgid']    = dataclasses.I3String( msgid.serialize() )
                    frame['__msgtopic'] = dataclasses.I3String( self.metadata_topic )
                    
                    return frame

            # it wasn't just the next message,
            # so let's seek to a new position
            # and try again
            print("about to seek to {}...".format(msgid))
            self.metadata_reader.seek(msgid)
            time.sleep(0.2)
            print("seek done.")

            if retries <= 0:
                raise RuntimeError("Seek to message id for metadata frame failed.")
            retries -= 1
            
            continue

    def Process(self):
        # driving module - we will be called repeatedly by IceTray with no input frames
        if self.PopFrame():
            raise RuntimeError("ReceivePFrameWithMetadata needs to be used as a driving module")
            
        # print("Waiting for message...")
        
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
        print("Message received. [msgid={}, topic={}]".format(msgid, msg.topic_name()))
        serialized_msgid = msgid.serialize()

        # make sure we do not work on a message we are already working on
        if serialized_msgid in self.receiver_service.message_in_flight_dict:
            print("Message is already being processed. Ignoring. [msgid={}, topic={}]".format(msgid, msg.topic_name()))
            # self.receiver_service.consumer().acknowledge(msg)

        # load metadata list for this frame
        msg_properties = msg.properties()
        if 'metadata' not in msg_properties:
            print("Invalid frame received - no metadata info - ignoring")
            return
        if 'metadata_topic' not in msg_properties:
            print("Invalid frame received - no metadata_topic info - ignoring")
            return
        metadata_info = pickle.loads(msg_properties['metadata'])        
        metadata_message_ids = [pulsar.MessageId.deserialize(i) for i in metadata_info]
        del metadata_info
        
        if (self.metadata_topic is None) or (self.metadata_topic != msg_properties['metadata_topic']):
            print("Need to (re-)subscribe to metadata stream: {}".format(msg_properties['metadata_topic']))
            self.metadata_topic = msg_properties['metadata_topic']
            if self.metadata_reader is not None:
                self.metadata_reader.close()
                del self.metadata_reader
            
            # invalidate cache
            self.metadata_cache = {}
            self.pushed_metadata_msgids = []

            # (re-)subscribe through Pulsar
            self.metadata_reader = self.receiver_service.client().create_reader(
              topic=self.metadata_topic,
              start_message_id=pulsar.MessageId.earliest,
              receiver_queue_size=1)

        del msg_properties
        
        # retrieve the metadata if necessary
        for metadata_msgid in metadata_message_ids:
            if self.is_metadata_msgid_pushed_and_active(metadata_msgid):
                # metadata frame already pushed and active
                continue
            
            # metadata frame not active, but maybe it is in the cache
            frame = self.retrieve_metadata_frame_from_cache(metadata_msgid)
            if frame is None:
                # metadata is not in cache, we need to retrieve it from Pulsar
                frame = self.retrieve_metadata_frame_from_pulsar(metadata_msgid)
                    
                # store in cache
                self.add_frame_to_cache(frame, metadata_msgid)
            
            # now push it
            self.push_metadata_frame_and_update_state(frame, metadata_msgid)
        
        # now load the actual P-frame and push it
        frame = pickle.loads(msg.data())
        
        print("Pushing frame stop {}[should be Physics] [msgid={}]".format(frame.Stop, msgid))
        self.PushFrame(frame)
        del frame # make sure to not re-use this frame, the frmework will mess with it
        
        # save a copy of the message in flight
        self.receiver_service.message_in_flight_dict[serialized_msgid] = msg
        
        # also push a special delimiter frame with the msgid so we can acknowledge it at the
        # end of the tray
        delimiter_frame = icetray.I3Frame(icetray.I3Frame.Stream('\03'))
        delimiter_frame['__msgid'] = dataclasses.I3String( serialized_msgid )
        print("Pushing frame stop '\\03' [\"__msgid\"={}]".format(msgid))
        self.PushFrame(delimiter_frame)
        
    def Finish(self):
        if self.metadata_reader is not None:
            self.metadata_reader.close()
            del self.metadata_reader
        
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
            
            print("Delimiter frame received. Acknowledging message id {}.".format(str(msgid)))
            self.receiver_service.consumer().acknowledge(msg)
            print("Acknowledged.")
            
        self.PushFrame(frame)

    def Finish(self):
        del self.receiver_service

