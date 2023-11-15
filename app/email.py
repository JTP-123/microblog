from flask_mail import Message 
from flask import current_app
from app import mail
from threading import Thread 

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body 
    msg.html = html_body 
    # Constructor Tread(group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None)
    # target是异步调用对象, args是参数target引用的形参的元组, 其余参数默认为None
    # 每次构造函数Thread建立线程对象,则至多可调用一次start()方法, start()方法在一个单独线程中调用run()方法
    # run()方法代表开启的线程活动, 会调用来自Thread中的形参target, 同时会调用分别来自args和kwargs的位置参数和关键词参数, 如果有的话
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start() # current_app, g, request, session is a proxy for real object, _get_current_object obtains real object



