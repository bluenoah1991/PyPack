""" Redis connection functions
"""

import os
import redis
from pypack import protocol

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

EVAL PQPOP 1 ns 10

Parameters

Keys 1. Namespace
Args 1. Limit
"""
PQPOP = "local t = {}\n" \
    "for i, k in pairs(redis.call('ZRANGE', KEYS[1]..':pq', 0, ARGV[1])) do\n" \
        "local v = redis.call('HGET', KEYS[1]..':index', k)\n" \
        "table.insert(t, t + 1, v)\n" \
    "end\n" \
    "redis.call('ZREMRANGEBYRANK', KEYS[1]..':pq', 0, ARGV[1])\n" \
    "return t"

"""Remove from Indexable Priority Queue
Example:

EVAL PQPOP 1 ns msgid

Parameters

Keys 1. Namespace
Args 1. Identifer
"""
PQREM = "redis.call('ZREM', KEYS[1]..':pq', ARGV[1])\n" \
    "redis.call('HDEL', KEYS[1]..':index', ARGV[1])"

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
        [retry_times, timestamp, buff] = val.split(":")
        retry_times = int(retry_times)
        timestamp = int(timestamp)
        packet = protocol.Packet.decode(buff)
        packet.retry_times = retry_times
        packet.timestamp = timestamp
        return packet

class Options(object):
    """ Redis build options
    """
    def __init__(self):
        self.redis_url = None

def determine_redis_provider():
    """ determine redis connection url
    """
    return os.environ.get("REDIS_URL", None) or "redis://localhost:6379/0"

def create(options=None):
    """ create redis client object
    """
    if options is None or not isinstance(options, Options):
        raise TypeError("parameter options must be a Options instance, not %s" % \
            type(options).__name__)
    redis_url = options.redis_url or determine_redis_provider()
    max_connections = options.max_connections or None

    redis_ = redis.StrictRedis.from_url(redis_url, max_connections=max_connections)

    namespace = options.redis_namespace or "httppack"
    redis_ = NamespacedRedis(redis_, namespace)
