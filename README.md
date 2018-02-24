
# 网络编程、异步IO模块、高性能异步非阻塞框架

## 一、网络编程
python中网络编程主要有socket/socketserver（socket这里包括自己用select实现的伪异步IO多路复用）和异步相关的Twisted/tornado/

[参考博客select/poll/epoll](http://www.cnblogs.com/jasonwang-2016/p/5663013.html)

4.1 示例一

web浏览器和socket_server交互,浏览器将收到服务端返回的数据,这里只能监听一个socket，多个浏览器请求到达accept时阻塞。
```
# socket_server.py
import socket

def handle_process(client):
    data = client.recv(1024)
    print(data.decode("utf-8"))
    client.send(b"HTTP/1.1 200 OK\r\n\r\n")#一定要先发送合规请求头
    client.send(b'hello worldfdds')

def main():
    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.bind(('127.0.0.1',8003))
    sock.listen(5)

    while True:
        conn,addr = sock.accept()
        handle_process(conn)
        conn.close()

if __name__ == '__main__':
    main()
```

4.2 示例二

socket + select 实现IO多路复用，所谓多路复用就是利用select实现监同时监听多个socket,但同一个socket收到多个浏览器请求到达accept时还是阻塞。
```
# socket_server.py
import select
import socket
# 单线程里同时监听多个socket对象，实现了"伪"并发IO操作： IO多路复用
sk1 = socket.socket()
sk1.bind(('127.0.0.1',8001))
sk1.listen(5)

sk2 = socket.socket()
sk2.bind(('127.0.0.1',8002))
sk2.listen(5)

inputs = [sk1,sk2]
w_inputs = []
while True:
    # IO多路复用：
    # select: 内部循环，主动查看
    # poll:   内部循环，主动查看
    # epoll:  非循环，  异步回调或被动通知
    r,w,e = select.select(inputs,w_inputs,[],0.05)
    for obj in r:
        if obj in [sk1,sk2]:
            print("新的连接来了。。")
            conn,addr = obj.accept()
            inputs.append(conn)
        else:
            print("新的数据来了")
            try:
                data=obj.recv(1024)
            except Exception as e:
                data = ""
            if data:
                # obj.sendall(data)
                w_inputs.append(obj)
            else:
                inputs.remove(obj)
                w_inputs.remove(obj)
                obj.close()
    for obj in w:
        obj.sendall(b'ok')
        w_inputs.remove(obj)
```

定义2个socket_client

```
# socket_client01.py
import socket

client = socket.socket()
client.connect(('127.0.0.1',8001))
while True:

    v = input(">>>")
    client.sendall(v.encode())
    ret = client.recv(1024)
    print("server response:",ret)
```

```
# socket_client02.py
import socket

client = socket.socket()
client.connect(('127.0.0.1',8002))
while True:
    v = input(">>>")
    client.sendall(v.encode())
    ret = client.recv(1024)
    print("server response:",ret)
```

测试服务端并发： 先启动socket_server.py,后启动socket_clientx.py


小结：

服务端单线程同时监听了多个socket对象，表明实现了并发连接或IO多路复用，但真正实现了并发吗？
当并发边连接有IO请求时还是占住了资源,那么在下一个例子中用线程处理IO请求实现真正的IO并发。
 

4.2 示例三

select + 线程实现真正的多并发
当服务端accept()连接成功后，可以另开启线程处理收发数据IO请求，以提高效率，但同一个socket收到多个浏览器请求到达accept时还是阻塞。

```
import select
import socket
import threading

def process_request(conn):

    while True:
        v = conn.recv(1024)
        conn.sendall(b'HTTP/1.1 200 OK\r\n\r\ndownload page ...')
        conn.close()
        break  # 任务处理完成后终止这个线程

sk1 = socket.socket()
sk1.bind(('127.0.0.1',8009))
sk1.listen(5)

inputs = [sk1,]
while True:
    r,w,e = select.select(inputs,[],[],0.05)
    for obj in r:
        if obj in [sk1,]:
            conn,addr = obj.accept()
            t=threading.Thread(target=process_request,args=(conn,))
            t.start()
```

设计思路可参考 socketserver源代码
```
import socketserver
class MyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        pass
    
server = socketserver.ThreadingTCPServer(('127.0.0.1',8001),MyHandler)
server.serve_forever()
```

4.2 示例四

为了实现不阻塞，需要撑握知识点
```
sock = socket.socket()
sock.setblocking(False)   #不阻塞了，这里是对accept()生效
sock.bind(('127.0.0.1',8008))
```

```
client,addr = sock.accept()    # accept()成功后马上recv()阻塞
client.setblocking(False)        #recv()不阻塞了，这里是对recv()生效
```

浏览器会自动向服务端请求头的一些数据，process_data()函数对请求头做了结构化处理，同时浏览器请求什么URL，服务端就会返回什么URL
在此基础上可以用类封装为一个web框架邹形。

一个不阻塞的web框架邹形
```
import select
import socket

def process_data(client):
    data = bytes()
    while True:
        try:
            chunk = client.recv(1024)
        except Exception as e:
            chunk = None
        if not chunk:
            break
        data += chunk
    data_str = str(data, encoding="utf-8")
    header,body = data_str.split('\r\n\r\n',1)
    header_list = header.split('\r\n',1)
    header_dict = {}
    for line in header_list:
        value = line.split(':', 1)
        if len(value) == 2:
            k, v = value
            header_dict[k] = v
        else:
            header_method, header_url, header_protocal = line.split(" ")
            header_dict["header_method"] = header_method
            header_dict["header_url"] = header_url
            header_dict["header_protocal"] = header_protocal

    return header_dict,body

sock = socket.socket()
sock.setblocking(False)                     # setblocking表示是否设置为阻塞模式,这里是对accept生效
sock.bind(('127.0.0.1',8008))
sock.listen(5)

# while True:
#     conn,addr = sock.accept()             # setblocking(False)后不阻塞了，有连接就拿连接，没有连接就直接报错
#     conn.setblocking(False)
#     conn.recv(1024)                       # 有数据拿数据，没有数据就直接报错
inputs = [sock,]
while True:
    rList,wList,eList = select.select(inputs,[],[],0.05)
    for client in rList:
        if client == sock:  # 建立新的连接
            conn,addr = client.accept()
            conn.setblocking(False)         # 有数据拿数据，没有数据就直接报错
            inputs.append(conn)
        else:
            header_dict,body=process_data(client)
            request_url=header_dict['header_url']
            client.send(b'HTTP/1.1 200 OK\r\n\r\n')
            client.send(request_url.encode("utf-8"))
            inputs.remove(client)
            client.close()
```




## 二、多线程、多进程

当我们用requests.ge扒取网页时可以用进程池或线程池提高并发，并采用回调机制处理返回数据.

这里有一个知识点就是future对象，`fu = pool.submit(download,url)` submit()返回的就是future对象，download()函数返回的结果封装在fu.result()里，
当回调时，fu.add_done_callback(write) ，fu对象被当作参数传给write(fu)函数，write(fu)函数内部用fu.result()可以得到download函数返回的结果。

```
import requests

from concurrent.futures import ThreadPoolExecutor
pool = ThreadPoolExecutor(2)

url_list = [
    'http://www.baidu.com',
    'http://www.digmyth.com',
    'http://www.github.com',
]

def write(future):
    response = future.result()
    with open('a.txt','wb+') as f:
        f.write(response.content)

def download(url):
    response = requests.get(url)
    print('download complete',url)
    return  response

for url in url_list:
    print('starting down', url)
    fu = pool.submit(download,url) # submit()返回future对象
    fu.add_done_callback(write)
```

对这段代码进一步封装
nb_thread.py示例代码
```
import requests
from  concurrent.futures import ThreadPoolExecutor
def download(url):
    response=requests.get(url)
    return response
def run(url_list=None):
    pool = ThreadPoolExecutor(2)
    for item in url_list:
        url = item['url']
        callback = item['callback']
        future=pool.submit(download, url)
        future.add_done_callback(callback)
```

test.py示例代码
```
from pro_threading import nb_thread

def f1(future):
    print(future.result().content)
def f2(arg):
    print("future")
def f3(future):
    print("future")
url_list = [
    {'url':'http://www.baidu.com','callback':f1},
    {'url':'http://www.digmyth.com','callback':f2},
    {'url':'http://www.github.com','callback':f3},
]

nb_thread.run(url_list)
```

先对上面代码作一个总结:

```
1 future对象对数据的封装，后续还要进一步学习future.set_result(666), 如何在回调函数中取得666,只有fu.set_result()才会断开连接
2 多进程，多线程在一定程序上提高了并发，但在单线程里如何实现并发，这就要用到异步非阻塞知识了。
```

## 异步IO模块

学习异步非阻塞知识前先来学习下python内置异步IO模块

#### 内置异步IO模块

有协程实现的异步IO模块
	
pip3 instal gevent

```
import gevent
import requests
def func(url):
    response = requests.get(url)
    print(response.url)
gevent.joinall([
    gevent.spawn(func,'http://www.baidu.com'),
    gevent.spawn(func,'http://www.digmyth.com'),
    gevent.spawn(func,'http://www.github.com'),
])
```

#### 自定义异步IO模块

socket_client客户端一个线程并发socket请求，就要用到socket+select,一般爬虫才有一个socket_client并发多个socket客户端请求

在爬虫项目中为了提高socket客户端并发，一般会用到异步IO模块： asyncio/gevent/,那么我们这里自定义IO模块就是编写socket客户端程序

Tornado虽然是web框架，但 `from tornado import httpclient`是socket客户端socket，用于并发http请求，这点注意

```
s

```



## 三、高性能异步非阻塞框架

参考链接:   

https://github.com/digmyth/socket_dev/blob/master/web_high_performance/ReadMe.md





