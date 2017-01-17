"""  Class and function related to protocol operation
"""

import datetime
import struct

MSG_TYPE_SEND = 0x1
MSG_TYPE_ACK = 0x2
MSG_TYPE_RECEIVED = 0x3
MSG_TYPE_RELEASE = 0x4
MSG_TYPE_COMPLETED = 0x5

QOS0 = 0
QOS1 = 1
QOS2 = 2

# MAX_DATETIME = int((datetime.datetime(2500, 1, 1) - datetime.datetime(1970, 1, 1)).total_seconds())

class Packet(object):
    """ This is a class that describe an incoming or outgoing message

    Members:

    msg_type : Enum. message type
    qos : Enum. quality of service level
    dup : Bool. whether the message is resent
    msg_id : Number. message id
    remaining_length : Number. payload length
    total_length : Number. buffer length
    payload : String. message body
    buff : String. full message
    confirm : whether the message is answered
    retry_times : resent times
    timestamp : next send time
    """
    def __init__(self, msg_type=MSG_TYPE_SEND, qos=QOS0, dup=False, msg_id=0, payload=None):
        self.msg_type = msg_type
        self.qos = qos
        self.dup = dup
        self.msg_id = msg_id
        if payload is not None and not isinstance(payload, str):
            raise TypeError("parameter payload must be str, not %s" % type(payload).__name__)
        self.payload = payload
        if payload is None:
            self.remaining_length = 0
        else:
            self.remaining_length = len(payload)
        self.total_length = 5 + self.remaining_length
        self.confirm = False
        self.retry_times = 0
        self.timestamp = 0
        self.buff = None

    @staticmethod
    def encode(packet):
        """ Encode packet object and fill buff field
        """
        buff = bytearray()
        fixed_header = (packet.msg_type << 4) | (packet.qos << 2) | (packet.dup << 1)
        buff.extend(struct.pack("!B", fixed_header))
        buff.extend(struct.pack("!H", packet.msg_id))
        buff.extend(struct.pack("!H", packet.remaining_length))
        if packet.payload is not None:
            buff.extend(packet.payload)
        packet.buff = str(buff)

    @staticmethod
    def decode(buff):
        """ Convert buff string to packet object
        """
        (fixed_header, msg_id, remaining_length) = struct.unpack("!BHH", buff[:5])
        msg_type = fixed_header >> 4
        qos = (fixed_header & 0xf) >> 2
        dup = (fixed_header & 0x3) >> 1
        if len(buff) >= 5 + remaining_length:
            (_, payload) = struct.unpack("!5s%ss" % remaining_length, buff[:5 + remaining_length])
            packet = Packet(msg_type, qos, dup, msg_id, payload)
            packet.buff = buff
            return packet
        else:
            return None
