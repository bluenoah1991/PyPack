""" Defined the main interface classes
"""

import struct
from pypack import redis_connection
from pypack import protocol

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
        buff = fileno.read(5)
        if len(buffer) < 5:
            return None
        (_, remaining_length) = struct.unpack("!3BH", buff)
        payload = fileno.read(remaining_length)
        if len(payload) < remaining_length:
            return None
        return protocol.Packet.decode(buff + payload)

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
                # TODO

    @classmethod
    def parse(cls, scope, fileno, callback):
        """ Parser buff string, and trigger callback
        """
        if not isinstance(fileno, str):
            raise TypeError("argument fileno must be file-like object, not %s" % \
                type(fileno).__name__)
        while True:
            packet = cls.read_packet(fileno)
            if packet is None:
                break
            cls.handle(scope, packet, callback)


