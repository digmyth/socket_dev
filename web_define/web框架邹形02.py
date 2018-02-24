
# 自定义web框架邹形02，未加入异步非阻塞式的future/yield牛逼的东东
# 直接运行即可访问接口： 127.0.0.1:8102/index
import re
import socket
import select
import time

class HttpResponse(object):
    """
    封装响应信息
    """
    def __init__(self, content=''):
        self.content = content

        self.headers = {}
        self.cookies = {}

    def response(self):
        print(self.content)
        return bytes(self.content, encoding='utf-8')


class HttpNotFound(HttpResponse):
    """
    404时的错误提示
    """
    def __init__(self):
        super(HttpNotFound, self).__init__('HTTP/1.1 404 code\r\n\r\n404 Not Found')

class HttpRequest(object):
    """
    用户封装用户请求信息
    """
    def __init__(self, conn):
        self.conn = conn

        self.header_bytes = bytes()
        self.header_dict = {}
        self.body_bytes = bytes()

        self.method = ""
        self.url = ""
        self.protocol = ""

        self.initialize()
        self.initialize_headers()

    def initialize(self):

        header_flag = False
        while True:
            try:
                received = self.conn.recv(8096)
            except Exception as e:
                received = None
            if not received:
                break
            if header_flag:
                self.body_bytes += received
                continue
            temp = received.split(b'\r\n\r\n', 1)
            if len(temp) == 1:
                self.header_bytes += temp
            else:
                h, b = temp
                self.header_bytes += h
                self.body_bytes += b
                header_flag = True

    @property
    def header_str(self):
        return str(self.header_bytes, encoding='utf-8')

    def initialize_headers(self):
        headers = self.header_str.split('\r\n')
        first_line = headers[0].split(' ')
        if len(first_line) == 3:
            self.method, self.url, self.protocol = headers[0].split(' ')
            for line in headers:
                kv = line.split(':')
                if len(kv) == 2:
                    k, v = kv
                    self.header_dict[k] = v


class Snow(object):
    """
    微型Web框架类
    """
    def __init__(self, routes):
        self.routes = routes
        self.inputs = set()
        self.request = None
        self.async_request_handler = {}

    def run(self, host='localhost', port=9999):
        """
        事件循环
        :param host:
        :param port:
        :return:
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port,))
        sock.setblocking(False)
        sock.listen(128)
        sock.setblocking(0)
        self.inputs.add(sock)
        try:
            while True:
                readable_list, writeable_list, error_list = select.select(self.inputs, [], self.inputs,0.005)
                for conn in readable_list:
                    if sock == conn:
                        client, address = conn.accept()
                        client.setblocking(False)
                        self.inputs.add(client)
                    else:
                        gen = self.process(conn)
                        conn.sendall(gen.response())
                        self.inputs.remove(conn)
                        conn.close()

        except Exception as e:
            pass
        finally:
            sock.close()


    def process(self, conn):
        """
        处理路由系统以及执行函数
        :param conn:
        :return:
        """
        self.request = HttpRequest(conn)
        func = None
        for route in self.routes:
            regex_str = "^{}$".format(route[0])
            if re.match(regex_str, self.request.url):
                func = route[1]
                break
        if not func:
            return HttpNotFound()
        else:
            return func(self.request)


def index(request):
    return HttpResponse('HTTP/1.1 200 OK\r\n\r\ntest code')

routes = [
    (r'/index', index),
]

app = Snow(routes)
app.run(port=8012)


