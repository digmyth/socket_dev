# 所有高性能相关（异步非阻塞知识，异步非阻塞web框架）

参考博客： 
http://www.cnblogs.com/wupeiqi/articles/6229292.html

http://www.cnblogs.com/wupeiqi/articles/6536518.html


## 一、 异步非阻塞知识

提高并发方法一： 多线程 多进程/线程池进程池

python2没有线程池，有进程池

python3有线程池，也有进程池

```
# from  threading import Thread
from  concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor
pool = ThreadPoolExecutor(10)    # 最多创建10个线程,要求不高的情况下，线程池就可以了
#pool = ProcessPoolExecutor(10)  # 最多创建10个进程
def task(url):
   pass
   
url_list = [...]
for url in url_list:
   pool.submit(task,url)
```

提高并发方法二： 异步非阻塞

异步IO性能比多进程多线程更高，一个线程完成有IO的并发操作: 有很多模块实现 asyncio 
```
非阻塞： 不等待
异步：   回调
IO多路复用：
select: 检测socket对象是否发生变化（是否连接成功，是否有数据到来）
```

socket客户端代码示例
```
import socket
client = socket.socket()

client.connect(('ip',80))  # 创建连接，这里默认是阻塞的
client.sendall(b"GET / HTTP/1.0 \r\nhost: www.baidu.com\r\n\r\n") # 发送HTTP请求
client.recv(8096) # 获取响应
print(data)
client.close() # 关闭连接
```

## select学习

### 几个简单问题带入学习

1  什么是协程?

协程就是单线程里在代码上实现切换运行，纯代码实现，对系统不可见，greenlet就是一个协程模块，gevent是一个greenlet + libevent实现的异步非阻塞IO模块
 
2 如何理解异步非阻塞？

   异步： 就是回调，利用select监听socket变化，执行某函数
   
   非阻塞： 不等待,比如 创建连接时，套接字setblocking(False)后就能批量发出请求，不管连接成功与否，连接成功与否交给select监听执行回调
   
3 异步IO模块本质？

   一类基于协程：   协程+非阻塞socket+select实现，如： gevent
   
   一类基于事件循环:完全通过socket + select实现， 如： Twisted/Tornado 

### select如何使用
select: 用select实现的伪异步IO多路复用
IO多路复用： 单线程里同时监听多个socket对象的变化，达到伪并发IO或异步非阻塞IO

socket+select简单示例

单线程里同时监听多个socket对象，实现了"伪"并发IO操作： IO多路复用
```
import select
import socket

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

``` 

r,w,e = select.select(inputs,w_inputs,[],0.05) 这句话会从inputs里取出对象，调用obj.fileno()方法,socket对象本身就有fileno()方法
如果一来，我们定义一个含有fileno()方法的类也是可以放在inputs列表里的

```
import select
import socket

class Foo():
    def __init__(self):
        self.sock = socket.socket()

    def fileno(self):
        return self.sock.fileno()

inputs = [Foo(),]
r,w,e = select.select(inputs,[],[],0.05)
```

socket_client客户端一个线程并发socket请求，就要用到socket+select,一般爬虫才有一个socket_client并发多个socket客户端请求



## 二、异步非阻塞web框架



阻塞模式： 在一个线程内，一个请求未处理完成，后续请求一直等待（Django，Flask,Bottle）
          对于阻塞模式提高性能： 多线程多进程
          
非阻塞模式：在一个线程内，一个请求在处理IO这段空闲时间内可以让后续请求进来继续处理，有请求处理结果返回时回调一个函数这种模式称为非阻塞模式

Tornado可以工作在阻塞模式，也可以工作在非阻塞模式

Tornado阻塞模式示例

```
# windows下无法运行，无法调用fork()
import tornado.web
import tornado.ioloop
from tornado.web import RequestHandler
from tornado.httpserver import  HTTPServer

class IndexHandler(RequestHandler):
    def get(self):
        print("start..")
        import time
        time.sleep(5)
        self.write("index page...")
        print("end...")

application = tornado.web.Application([
    (r"/index.html", IndexHandler),
])

if __name__ == "__main__":
    # application.listen(8888)
    # tornado.ioloop.IOLoop.instance().start()

    server = HTTPServer(application)
    server.bind(8888)
    server.start(3) # Forks multiple sub-processes
    tornado.ioloop.IOLoop.current().start()
```



Tornado非阻塞模式示例
```
import tornado.web
import tornado.ioloop
from tornado.web import RequestHandler
from tornado.httpserver import  HTTPServer
from tornado import gen
from tornado.concurrent import  Future
import time

class IndexHandler(RequestHandler):
    @gen.coroutine
    def get(self):
        print("start..")
        future = Future()
        tornado.ioloop.IOLoop.current().add_timeout(time.time() + 5, self.done)
        yield future
        print('end')

    def done(self, *args, **kwargs):
        self.write('async')
        self.finish()

application = tornado.web.Application([
    (r"/index.html", IndexHandler),
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

```




## 自定义web框架

 自定义web框架参考：http://www.cnblogs.com/wupeiqi/articles/6536518.html


以前我们学习异步IO模块都是写socket客户端，Tornado `from tornado import httpclient`用来提高爬虫效率也是相关于socket客户端。

这里我们是写socket服务端。

快速入手一个socket服务端程序
```
import socket,select,time

sock = socket.socket()
sock.bind(('127.0.0.1',9988))
sock.listen(10)

while True:
    client,addr = sock.accept()
    data=client.recv(8096)
    client.send(b'/ HTTP/1.1 200 OK\r\n\r\n')  # 注意正规的响应头，否则客户端接收不到响应数据
    client.send(b'xxxxx')
    client.close()
```

这种是阻塞式的，我们加上setblocking(False)变为非阻塞式，就要引入select监听socket来回调执行数据处理了
```
ss
```

