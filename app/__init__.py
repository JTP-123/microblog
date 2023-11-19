from flask import Flask, request, current_app
from config import Config 
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate 
from flask_login import LoginManager
import logging, os
from flask_mail import Mail 
from flask_bootstrap import Bootstrap
from flask_moment import Moment 
from flask_babel import Babel
from flask_babel import lazy_gettext as _l
from logging.handlers import SMTPHandler, RotatingFileHandler
from elasticsearch import Elasticsearch
from flask_pagedown import PageDown
from flask_avatars import Avatars

mail = Mail() # create an instance that is not attached to the application
db = SQLAlchemy()
migrate = Migrate()
moment = Moment()
babel = Babel()
pagedown = PageDown()

login = LoginManager()
login.login_view = 'auth.login'
login.login_message = _l('Please log in to access this page.') # 用户重定向至登录页面时, flask login会闪现消息, 该消息来自flask-login本身而非request
bootstrap = Bootstrap()
avatars = Avatars()

def create_app(config_class=Config):
   app = Flask(__name__)
   """ 
      app.config是字典子类, 通常的配置方式是键值对添加app.config[key]=value;
      而方法from_config(obj)可以作为替代实现, 其中obj可以是模块或者类;
      from_config通常加载模块或者类的大写属性来配置config, 故Config类属性须大写.
   """
   app.config.from_object(config_class)
   app.config.from_prefixed_env()


   mail.init_app(app) # bind instance to application
   db.init_app(app)
   migrate.init_app(app, db)
   moment.init_app(app)
   babel.init_app(app)
   login.init_app(app)
   bootstrap.init_app(app)
   pagedown.init_app(app)
   avatars.init_app(app)
   app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
      if app.config['ELASTICSEARCH_URL'] else None

   from app.errors import bp as errors_bp  # import blueprint
   app.register_blueprint(errors_bp)  # 注册蓝图

   from app.auth import bp as auth_bp 
   app.register_blueprint(auth_bp, url_prefix='/auth') # 对于auth下的路由,url_for会自动生成包含的前缀/auth, 故装饰器url可以省略/auth前缀

   from app.main import bp as main_bp 
   app.register_blueprint(main_bp)

   from app.api import bp as api_bp
   app.register_blueprint(api_bp, url_prefix='/api')

   if not app.debug and not app.testing: # 若app处于非debug模式下且非测试状态下
      if app.config['MAIL_SERVER']:
         auth = None
         if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD']) # 利用元组的不可变, auth:=tuple()
         secure = None 
         if app.config['MAIL_USE_SSL']:
            secure = () 
         mail_handler = SMTPHandler(
            mailhost = (app.config['MAIL_SERVER'], app.config['MAIL_PORT']), # mailhost:=元组(host, post) in order to speicfy non-standard SMTP port
            fromaddr = 'no-reply@' + app.config['MAIL_SERVER'],
            toaddrs = app.config['ADMINS'], subject = 'Microblog Failure', 
            credentials = auth, # SMTP需要验证, 则参数credentials需要被指定成(username, password)的元组的形式
            secure = secure
         )
         mail_handler.setLevel(logging.ERROR) # 设置调试级别为Error模式, 则只发送报错信息邮件
         app.logger.addHandler('mail_handler')
   
      if not os.path.exists('logs'): # 处理日志信息
         os.mkdir('logs')
         """
         RotatingFileHandler(filename, mode='a', maxBytes=0, backupCount=0,
                              encoding=None, delay=Flase)->生成滚动日志, 可控制日志文件大小
         params: maxBytes: 指定单个日志文件存储最大字节;
               backupCount: 指定备份日志文件数量上限, 所有日志文件都以.log后缀结尾,
                              若backupCount=5, 则在日志文件末尾添加后缀为'.1', '.2', ...
                              故此时日志文件为app.log, app.log.1, app.log.2, ..., app.log.5
               delay: 决定日志文件是否同时打开, 若为True,则当前文件直到上个日志输出记录后才被打开
               mode: open文件打开方式, 默认是附加写的方式'a', 在文件末尾追加内容, 不可读.文件名不存在可重新创建文件.
         """
         file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240, backupCount=10)
         file_handler.setFormatter(logging.Formatter(
            # %(asctime)s是logging模块用来获取日志记录logRecord对象属性的占位符,属性存储在字典中, 记号(asctime)标识字典的键,将值插入格式化字符串中
            # %(asctime)s: 当前时间；
            # %(levelaname)s: 日志级别名称；
            # %(message)s: 日志信息；
            # %(pathname)s: 程序执行路径；
            # %(lineno)d: 输出日志代码所在行数；
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'  # customize log message format
         ))
         file_handler.setLevel(logging.INFO)
         app.logger.addHandler(file_handler)
      
      app.logger.setLevel(logging.INFO)
      app.logger.info('Microblog startup')

   return app

@babel.localeselector
def get_locale(): # 匹配应用支持语言里在浏览器请求头accept-language里占有最大比重的语种
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])



from app import models