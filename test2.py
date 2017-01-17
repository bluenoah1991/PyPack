from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from pypack import PyPack

class TestHTTPHandler(BaseHTTPRequestHandler):
    def callback(self, scope, payload):
        if payload == 'do you copy?':
            PyPack.commit(scope, "First reply message!", 0)
            PyPack.commit(scope, "Second reply message! (Qos 1)", 1)
            PyPack.commit(scope, "Third reply message! (Qos 2)", 2)
        print payload

    def write(self, response):
        self.protocal_version = "HTTP/1.1"
        self.send_response(200)  
        # self.send_header("Welcome", "Contect")         
        self.end_headers()  
        self.wfile.write(response)

    def do_POST(self):
        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        response_body = PyPack.parse_body('one', post_body, self.callback)
        self.write(response_body)

if __name__ == '__main__':
    http_server = HTTPServer(('0.0.0.0', 8080), TestHTTPHandler)
    http_server.serve_forever()