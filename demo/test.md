

## 异步非阻塞入门demo示例代码

普通阻塞式socket 服务端示例
```
import socket
import time

sock = socket.socket()
sock.bind(('127.0.0.1',9999))
sock.listen(5)

def process_handler(client):
    data = client.recv(8096)
    print(data)
    client.sendall(b'/ HTTP/1.1  200 OK\r\n\r\ntest code ....')

while True:
    client,addr = sock.accept()
    process_handler(client)
    client.close()
```

非阻塞式socket服务端示例
```
import socket,select,time

sock = socket.socket()
sock.setblocking(False)
sock.bind(('127.0.0.1',9988))
sock.listen(10)

inputs = [sock,]

while True:
    r,w,e=select.select(inputs,[],[],0.05)

    for conn in r:
        if conn == sock:
            client,addr = sock.accept()
            client.setblocking(False)
            inputs.append(client)
        else:
            try:
                data=conn.recv(4096)
            except Exception as e:
                data = ""
            print(data)
            if data:
                conn.sendall(b'/ HTTP/1.1 200 OK\r\nHost: 127.0.0.1\r\n\r\nnwwwwx4')
            inputs.remove(conn)
            conn.close()
```

非阻塞式socket服务端示例的改进版
```
import socket,select,time

sock = socket.socket()
sock.setblocking(False)
sock.bind(('127.0.0.1',9988))
sock.listen(10)

inputs = [sock,]
conn_inputs=[]
while True:
    r,w,e=select.select(inputs,conn_inputs,[],0.05)

    for conn in r:
        if conn == sock:
            client,addr = sock.accept()
            client.setblocking(False)
            inputs.append(client)
        else:
            try:
                data = conn.recv(4096)
            except Exception as e:
                data = ""
            print(data)
            if data:
                conn_inputs.append(conn)
                inputs.remove(conn)
            else:
                conn_inputs.remove(conn)
                inputs.remove(conn)
                conn.close()
    for obj in w:
        obj.sendall(b'/ HTTP/1.1 200 OK\r\nHost: 127.0.0.1\r\n\r\nwwwwx4')
        conn_inputs.remove(obj)
```

再来编写socket客户端，让客户端批量并发请求(异步)验证socket服务端能否异步非阻塞式处理请求

socket_client01.py示例，多运行几次socket_client也可模拟多个请求
```
import socket

client = socket.socket()
client.connect(('127.0.0.1',8001))
while True:

    v = input(">>>")
    client.sendall(v.encode())
    ret = client.recv(1024)
    print("server response:",ret)
```

或者编写非阻塞式socket客户端,批量发送请求
```
import socket,time,select

def task():
    client = socket.socket()
    client.setblocking(False)
    try:
        client.connect(('127.0.0.1',9988))
    except BlockingIOError as e:
        pass
    inputs = []
    conn_inputs = [client,]
    while True:
        r,w,e=select.select(inputs,conn_inputs,[],0.05)
        for obj in w: # 连接成功
            v = "xxxttt"
            obj.sendall(v.encode())
            conn_inputs.remove(obj)
            inputs.append(obj)

        for obj in r: #  有数据来了
            data=obj.recv(4096)
            print(data)
            obj.close()
            inputs.remove(obj)

        if not inputs:
            break

for i in range(10):
    task()
```
