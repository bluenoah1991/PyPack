""" Defined the main interface classes
"""

import struct, socket, copy, datetime
import gevent
from . import redis_connection
from . import protocol

class AsyncObj(object):
    def __init__(self, value):
        self.value = value

    def set(self, value):
        self.value = value

    def val(self):
        return self.value

class PyPack(object):
    """ PyPack main class
    """
    redis_conn = None

    @classmethod
    def redis(cls):
        """ return a new Redis connection object for a singleton
        """
        if cls.redis_conn is None:
            cls.redis_conn = redis_connection.create()
        return cls.redis_conn

    @classmethod
    def read_packet(cls, fileno):
        """ Read a packet object from file-like object
        """
        try:
            buff = fileno.read(5)
            if len(buff) < 5:
                return None
            (_, remaining_length) = struct.unpack("!3sH", buff)
            payload = fileno.read(remaining_length)
            if len(payload) < remaining_length:
                return None
            return protocol.Packet.decode(buff + payload)
        except socket.error:
            return None

    @classmethod
    def handle(cls, scope, packet, callback):
        """ Respond packet and invoke callback
        """
        if packet.msg_type == protocol.MSG_TYPE_SEND:
            if packet.qos == protocol.QOS0:
                callback(scope, packet.payload)
            elif packet.qos == protocol.QOS1:
                reply = protocol.Packet(protocol.MSG_TYPE_ACK, protocol.QOS0, False, packet.msg_id)
                protocol.Packet.encode(reply)
                cls.redis().save(scope, reply)
                callback(scope, packet.payload)
            elif packet.qos == protocol.QOS2:
                cls.redis().receive(scope, packet.msg_id, packet.payload)
                reply = protocol.Packet(protocol.MSG_TYPE_RECEIVED, protocol.QOS0, False, packet.msg_id)
                protocol.Packet.encode(reply)
                cls.redis().save(scope, reply)
        elif packet.msg_type == protocol.MSG_TYPE_ACK:
            cls.redis().confirm(scope, packet.msg_id)
        elif packet.msg_type == protocol.MSG_TYPE_RECEIVED:
            cls.redis().confirm(scope, packet.msg_id)
            reply = protocol.Packet(protocol.MSG_TYPE_RELEASE, protocol.QOS1, False, packet.msg_id)
            protocol.Packet.encode(reply)
            cls.redis().save(scope, reply)
        elif packet.msg_type == protocol.MSG_TYPE_RELEASE:
            payload = cls.redis().release(scope, packet.msg_id)
            if payload is not None:
                callback(scope, payload)
            reply = protocol.Packet(protocol.MSG_TYPE_COMPLETED, protocol.QOS0, False, packet.msg_id)
            protocol.Packet.encode(reply)
            cls.redis().save(scope, reply)
        elif packet.msg_type == protocol.MSG_TYPE_COMPLETED:
            cls.redis().confirm(scope, packet.msg_id)

    @classmethod
    def read(cls, scope, fileno, callback, cont):
        """ Decode Packet from fileno and handle it
        """
        while cont.val():
            packet = cls.read_packet(fileno)
            if packet is None:
                cont.set(False)
                break
            cls.handle(scope, packet, callback)
            gevent.sleep(0) # yield to other thread

    @classmethod
    def write(cls, scope, fileno, cont):
        """ Read Packet from storage and write into fileno
        """
        while cont.val():
            packets = cls.redis().unconfirmed(scope, 5)
            if packets is not None and len(packets) > 0:
                for packet in packets:
                    retry_packet = cls.retry(packet)
                    if retry_packet is not None:
                        cls.redis().save(scope, retry_packet) 
                try:
                    for packet in packets:
                        fileno.write(packet.buff)
                    fileno.flush()
                except socket.error:
                    cont.set(False)
                    break
                gevent.sleep(0) # yield to other thread
            else:
                gevent.sleep(1)

    @classmethod
    def retry(cls, packet):
        if packet.qos == protocol.QOS0:
            return None
        retry_packet = None
        now = int((datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds())
        if packet.retry_times > 0:
            retry_packet = copy.deepcopy(packet)
            retry_packet.retry_times += 1
            retry_packet.timestamp = now + retry_packet.retry_times * 5
        else:
            retry_packet = protocol.Packet(packet.msg_type, packet.qos, True, packet.msg_id, packet.payload)
            protocol.Packet.encode(retry_packet)
            retry_packet.retry_times = 1
            retry_packet.timestamp = now + retry_packet.retry_times * 5
        return retry_packet

    # public methods

    @classmethod
    def hold(cls, scope, fileno, callback):
        """ Hold on file object, and trigger callback
        """
        if not hasattr(fileno, 'read') or not hasattr(fileno, 'write'):
            raise TypeError("argument fileno must be file-like object, not %s" % \
                type(fileno).__name__)
        cont = AsyncObj(True)
        read_thread = gevent.spawn(cls.read, scope, fileno, callback, cont)
        write_thread = gevent.spawn(cls.write, scope, fileno, cont)
        gevent.joinall([read_thread, write_thread])

    @classmethod
    def commit(cls, scope, payload, qos=protocol.QOS0):
        packet = protocol.Packet(protocol.MSG_TYPE_SEND, qos, False, cls.redis().unique_id(scope), payload)
        protocol.Packet.encode(packet)
        cls.redis().save(scope, packet)
