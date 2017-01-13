""" Redis connection functions
"""

import os, datetime
import redis
from . import protocol

"""Add to Indexable Priority Queue
Example:

EVAL PQADD 1 ns 999 msgid bufferstring

Parameters

Keys 1. Namespace
Args 1. Sorted Set Score
Args 2. Identifer
Args 3. Value
"""
PQADD = "redis.call('ZADD', KEYS[1]..':pq', ARGV[1], ARGV[2])\n" \
    "redis.call('HSET', KEYS[1]..':index', ARGV[2], ARGV[3])"

"""Popup N item from Indexable Priority Queue
Example:

EVAL PQPOP 1 ns 10 1483598266

Parameters

Keys 1. Namespace
Args 1. Limit
Args 2. Now
"""
PQPOP = "local t = {}\n" \
    "local len = 0\n" \
    "local key = nil\n" \
    "for i, k in pairs(redis.call('ZRANGE', KEYS[1]..':pq', 0, ARGV[1], 'WITHSCORES')) do\n" \
        "if i % 2 == 1 then\n" \
            "key = k\n" \
        "else\n" \
            "if tonumber(ARGV[2]) < tonumber(k) then break end\n" \
            "len = len + 1\n" \
            "local v = redis.call('HGET', KEYS[1]..':index', key)\n" \
            "table.insert(t, #t + 1, v)\n" \
        "end\n" \
    "end\n" \
    "if len > 0 then\n" \
        "redis.call('ZREMRANGEBYRANK', KEYS[1]..':pq', 0, len)\n" \
    "end\n" \
    "return t"

"""Remove from Indexable Priority Queue
Example:

EVAL PQREM 1 ns msgid

Parameters

Keys 1. Namespace
Args 1. Identifer
"""
PQREM = "redis.call('ZREM', KEYS[1]..':pq', ARGV[1])\n" \
    "redis.call('HDEL', KEYS[1]..':index', ARGV[1])"

"""Pop from Hash
Example:

EVAL HPOP 2 key

Parameters

Keys 1. Hash Key
Keys 2. Field Key
"""
HPOP = "local v = redis.call('HGET', KEYS[1], KEYS[2])\n" \
    "redis.call('HDEL', KEYS[1], KEYS[2])\n" \
    "return v"

class NamespacedRedis(object):
    """ Provides a top level namespace to redis client object
    """
    def __init__(self, r, ns):
        self.redis = r
        self.namespace = ns

    def _encode_val(self, packet):
        retry_times = str(packet.retry_times)
        timestamp = str(packet.timestamp)
        return "%s:%s:%s" % (retry_times, timestamp, packet.buff)

    def _decode_val(self, val):
        [retry_times, timestamp, buff] = val.split(":", 2)
        retry_times = int(retry_times)
        timestamp = int(timestamp)
        packet = protocol.Packet.decode(buff)
        packet.retry_times = retry_times
        packet.timestamp = timestamp
        return packet

    def unique_id(self, scope):
        i_ =  self.redis.incr("%s:%s:uniqueid" % (self.namespace, scope))
        return i_ + (1 << 15)

    def eval_score(self, packet):
        return packet.timestamp

    def save(self, scope, packet):
        self.redis.eval(PQADD, 1, "%s:%s" % (self.namespace, scope), 
            self.eval_score(packet), packet.msg_id, self._encode_val(packet))

    def unconfirmed(self, scope, limit):
        now = int((datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds())
        buffers = self.redis.eval(PQPOP, 1, "%s:%s" % (self.namespace, scope), limit, now)
        return map(lambda buffer: self._decode_val(buffer), buffers)

    def confirm(self, scope, msg_id):
        self.redis.eval(PQREM, 1, "%s:%s" % (self.namespace, scope), msg_id)

    def receive(self, scope, msg_id, payload):
        self.redis.hset("%s:%s:payloads" % (self.namespace, scope), msg_id, payload)

    def release(self, scope, msg_id):
        return self.redis.eval(HPOP, 2, "%s:%s:payloads" % (self.namespace, scope), msg_id)

class Options(object):
    """ Redis build options
    """
    def __init__(self):
        self.redis_url = None
        self.max_connections = None
        self.redis_namespace = None

def determine_redis_provider():
    """ determine redis connection url
    """
    return os.environ.get("REDIS_URL", None) or "redis://localhost:6379/0"

def create(options=None):
    """ create redis client object
    """
    if options is not None and not isinstance(options, Options):
        raise TypeError("parameter options must be a Options instance, not %s" % \
            type(options).__name__)
    if options is None:
        options = Options()
    redis_url = options.redis_url or determine_redis_provider()
    max_connections = options.max_connections or None

    redis_ = redis.StrictRedis.from_url(redis_url, max_connections=max_connections)

    namespace = options.redis_namespace or "httppack"
    return NamespacedRedis(redis_, namespace)
