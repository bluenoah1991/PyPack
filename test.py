import gevent
from gevent.server import StreamServer
from pypack import PyPack

def recieved_msg(scope, payload):
    print('%s: %s' % (scope, payload))
    # PyPack.commit(scope, "First reply message!", 0)
    # PyPack.commit(scope, "Second reply message! (Qos 1)", 1)
    # PyPack.commit(scope, "Third reply message! (Qos 2)", 2)

def test(socket, address):
    PyPack.commit(address[1], "First bootstrap message!", 0)
    PyPack.commit(address[1], "Second bootstrap message! (Qos 1)", 1)
    PyPack.commit(address[1], "Third bootstrap message! (Qos 2)", 2)
    PyPack.hold(address[1], socket.makefile(), recieved_msg)

if __name__ == '__main__':
    server = StreamServer(('0.0.0.0', 8080), test)

    print('Starting test server on port 8080')
    server.serve_forever()