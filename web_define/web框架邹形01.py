# 访问http://127.0.0.1:9000/index.html

import socket,select

def f1(request):
    return 'txt1'

def f2(request):
    return 'txt2'

routers = [
    ('/index.html',f1),
    ('/home.html',f2),
]

sock = socket.socket()
sock.setblocking(False)
sock.bind(('127.0.0.1',9000))
sock.listen(5)
inputs = [sock,]
while True:
    r,w,e = select.select(inputs,[],[],0.05)
    for conn in r:
        if conn == sock:
            client, addr = sock.accept()
            client.setblocking(False)
            inputs.append(client)
        else:
            data=conn.recv(4096)
            print(data)
            inputs.remove(conn)
            request_url = '/index.html' # 假如这是从data里取出的
            func = None
            for x in routers:
                if x[0] == request_url:
                    func = x[1]
                break
            response = func(data)
            v='/ HTTP/1.1  200 OK\r\n\r\n%s' %(response)
            conn.sendall(v.encode())
            conn.close()
