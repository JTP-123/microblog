from datetime import datetime 
from werkzeug.security import check_password_hash, generate_password_hash
from app import db, login
from flask_login import UserMixin 
from flask import current_app, url_for
from hashlib import md5 
from time import time 
import jwt, bleach, json 
from app.search import add_to_index, remove_from_index, query_index
from markdown import markdown
import base64, os
from datetime import datetime, timedelta

class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        """
        ids:= list of revelant id;
        total:= the number of revelant matching results;
        params: cls.__tablename__ is defined as name which flask-sqlalchemy assigned to relational table,
                                namely tablename, often is classname if __tablename__ is not written;
        query_index returns a multi-layer dict ordered by decreasing matching revelation, thus id 1 > 2 > 3 > ... on revelation;
        """
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0: # if nothing matches, then model class queries obj whose id equals 0, total=0 #
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i)) # list of tuple (id, i), i indicates the rank of matching, rank(1) > rank(2) > rank(3) > ...
        """
        in_: query method to find out and return those cls.id in ids;
        db.case: like if-else statment, sql syntax: 'case when condition then statement else statement', 
                it has equivalent case(when, value=column_compared), when is a dict or tuple;
        order_by: order cls.id in ids by corrsponding matching rank(i), ascending order by default;
        """
        return cls.query.filter(cls.id.in_(ids)).order_by(db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session): # writes changes into _changes before session is commited beacuse session's lifetime ends once browser closed
        session._changes = { # session words pretty muck like dictionary, contains a dict obj call _changes
            'add': list(session.new), # save add, update, delete operation for index record
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session): # make changes on corresponding elasticsearch side, namely change retrive record.
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin): # check whether an object is a instance of class SearchbleMixin or not.
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls): # refresh index: add all new obj like posts from sqlalchemy database to search index
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)

"""
event.listen(target, identifier, listener_function):
    params::target: concrete object;
            indentifier: a string identifies the event to be intercepted;
            lister_function: user-defined listening function
make sure sqlalchemy call before and after commit respectively
"""
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit) 

followers = db.Table('followers',
    # 'follower_id' 设置字段名, 可通过第1个位置参数来指定, 或者关键字参数name=value. 若不指定, 默认类属性名为字段名
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')), 
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class PaginatedAPIMixin():
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        resources = query.paginate(page=page, per_page=page, error_out=False)
        data = {
            'items': [item.to_dict() for item in resources.items],
            '_meta': {
                'page': page, 
                'per_page': per_page, 
                'total_page': resources.page, 
                'total_items': resources.total
            },
            '_links': {
                'self': url_for(endpoint, page=page, per_page=per_page,
                                **kwargs),
                'next': url_for(endpoint, page=page + 1, per_page=per_page,
                                **kwargs) if resources.has_next else None,
                'prev': url_for(endpoint, page=page - 1, per_page=per_page,
                                **kwargs) if resources.has_prev else None
            }
        }
        return data

class User(db.Model, UserMixin, PaginatedAPIMixin): # UserMixin类包含了与用户有关的is_authenticated, is_activate, is_anonymous三个属性以及get_id()方法
    """
    posts并非真实的字段,也就是不存在于数据库表中, 而是user和posts之间的一种关系的高观点视角.
    db.relationship函数通常被定义在'一对多(one-to-many)'关系中的one上,即代表one的X类上. 譬如表达式user1.posts查询返回的是user1写得所有帖子.
    db.relationship:第一个参数是代表了many的映射Y类, 若Y被定义在后面, 则此时可以参数值是Y类名.
                    第二个参数backref=value:定义了被添加进类Y的属性value, 可以通过表达式y.value反向to one, 获取X类中实例,
                                            此处post.author可以获取写该post的author, 和正向获取author->post顺序相反.
                    第三个参数lazy仅用于'一对多'或者'多对多'关系中, 为所有读取操作生成查询对象而非加载数据, 再近一步过滤, 优化性能.
    """
    id = db.Column(db.Integer, primary_key=True)
    # index=True创建为username列创建索引，unique=True则该列不允许出现重复的值
    username = db.Column(db.String(64), index=True, unique=True) # unique=True设置db.Column实例username是唯一的, 不可重复
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140)) # 个性简介
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)
    # followed查询关系是否存在, 是模型类的一个查询(query)属性, sqlalchemy提供了查询属性用来获取记录的过滤和查询方法
    followed = db.relationship('User', secondary=followers,  # secondary:= association table
                                # primaryjoin代表关系的左半部分,是从左边即关注者follower出发连接关联表的条件, 连接条件是关系左边用户id匹配关联表中的列字段follower_id
                                primaryjoin=(followers.c.follower_id == id), 
                                # secondaryjoin代表关系的右半部分, 从关联表出发连接右边被关注者followed的条件, 即关系右边用户id匹配关联表中列字段followed_id
                                secondaryjoin=(followers.c.followed_id == id),
                                # backref定义反向查询关系, 这里是从左边followed-->右边followers的查询被关注者人数, 
                                # 内部第一个参数是位于右边的类名, lazy定义了查询模式, 'dynamic'禁止自动查询, 可添加过滤器.
                                # 类似上面定义的, 直接在User类中添加了followers属性, 为指定lazy参数, 故用了db.backref()函数.
                                backref=db.backref('followers', lazy='dynamic'), lazy='dynamic') # lazy是db.relationship的参数, 定义从左边发起的查询mode
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='author', lazy='dynamic')
    messages_received = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime)
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')

    def __repr__(self): # 操作符重载, 自动打印类对象, 一般用于调试
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    


    def is_following(self, user):
        # self位于关系followed的左边, user位于关系右边, 通过对类属性followed来调用filter方法过滤结果, 再用count返回查询数量
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def follow(self, user):
        if not self.is_following(user): # 若实例self尚未关注user, 则添加关注. 否则无需再次关注
            self.followed.append(user) # 关系followed的建立生成list-like的对象, 可以提供类似列表操作

    def unfollow(self, user):
        if self.is_following(user): # 若实例self关注了user, 才能取消关注, 否则无法unfollow
            self.followed.remove(user)

    def followed_posts(self):
        # Post.query.join(association_table, join_condition)连接followers和Post, 建立临时表格.
        # join条件是发布帖子的用户是有被其他人关注的.
        # filter过滤方法查询发布帖子且被人关注的用户中被当前用户关注的.
        # order_by令查询结果以时间戳字段降序排列
        followed = Post.query.join(followers, (followers.c.followed_id == Post.user_id)).filter(
            followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id) 
        return followed.union(own).order_by(Post.timestamp.desc()) # union operation adds own post into followed posts 

    def get_reset_password_token(self, expires_in=600): # jwt.encode(payload, secret_key, algorithm)
        # payload形式是一个字典, payload:={'reset_password': user_id, 'exp': token_expiration_time}, 
        # 第一个键的值是修改密码的用户id, 第二个键的值是token有效时间=当前时间 + 持续时间, 若解码后发现时间超出令牌有效时间(字典不相等),则token无效
        # 密钥secret_key用来生成加密签名.
        return jwt.encode({'reset_password': self.id, 'exp': time() + expires_in},
                        current_app.config['SECRET_KEY'], algorithm='HS256') # jwt加密生成比特序列, 转换成适合字符串序列
    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['reset_password'] # 解码令牌返回payload字典
        except:
            return
        return User.query.get(id)

    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(Message.timestamp > last_read_time).count()

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n 
    
    def to_dict(self, include_email=False):
        data = {
            'id': self.id,
            'username': self.username,
            'last_seen': self.last_seen.isoformat() + "Z", 
            'about_me': self.about_me,
            'post_count': self.posts.count(),
            'follower_count': self.followers.count(),
            'followed_count': self.followed.count(),
            '_links': {
                'self': url_for('api.get_user', id=self.id),
                'followers': url_for('api.get_followers', id=self.id),
                'followed': url_for('api.get_followed', id=self.id),
            }
        }
        if include_email:
            data['email'] = self.email
        return data
    
    def from_dict(self, data, new_user=False):
        for field in ['username', 'email', 'about_me']:
            if field in data:
                setattr(self, field, data[field])
        if new_user and 'password' in data:
            self.set_password(data['password'])

    def get_token(self, expires_in=3600):
        now = datetime.utcnow()
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token 
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token
    
    def revoke_token(self):
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.uctnow():
            return None
        return user 

class Post(SearchableMixin, db.Model):
    __searchable__ = ['body']
    """
    时间戳timestamp: 第一个参数db.DateTime是字段类型.
                    第二个参数index=True:设置索引, 可以让帖子按照时间发生顺序来查询帖子.
                    第三个参数default: 传递给utcnow函数本身, 而不是函数值utcnow()使得时间不是固定的,
                                    一旦传递的是函数本身, SQLAlchemy会将字段设置成调用函数时返回的值,也就是当前时间, 
                                    并且在用户浏览时会自动转换成当地时间.
    user_id初始化为user.id的外键, 来引用user表的id, db.ForeignKey位于多的一方.
    """
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text) # set db.Text to allow for multi-line text instead of db.string(140)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    language = db.Column(db.String(5)) # lang code is no more than 5 digits long
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    body_html = db.Column(db.Text)

    def __repr__(self):
        return '<Post {}>'.format(self.body)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', # define allowed html tags for Markdown
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul', 
                        'h1', 'h2', 'h3', 'p', 'img', 'kbd', 'sup', 'sub', 'br', 
                        'table', 'footer', 'thead', 'tbody', 'tr', 'th', 'td', 
                        'small', 'big', 'div', 'span']
        extensions = ['pymdownx.arithmatex']
        target.body_html = bleach.linkify(markdown(value, extensions=extensions,
                                    extension_configs={
                                        'pymdownx.arithmatex': {
                                            'generic': True
                                        }
                                    }))
        """target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html', 
                    extensions=extensions,
                    extension_configs={
                        "pymdownx.arithmatex": {
                            "generic": True
                        }
                    }),
            tags=allowed_tags, strip=False))"""
        
db.event.listen(Post.body, 'set', Post.on_changed_body)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True) 
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    body_html = db.Column(db.Text)

    def __repr__(self):
        return '<Comment {}>'.format(self.body)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', # define allowed html tags for Markdown
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul', 
                        'h1', 'h2', 'h3', 'p', 'img', 'kbd', 'sup', 'sub', 'br', 
                        'table', 'footer', 'thead', 'tbody', 'tr', 'th']
        extensions = ['mdx_math', 'pymdownx.arithmatex', 'pymdownx.b64', 'pymdownx.emoji']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html', 
                    extensions=extensions,
                    extension_configs={
                        'mdx_math': {
                            'enable_dollar_delimiter': True,
                            'add_preview': True
                        }
                    }),
            tags=allowed_tags, strip=True))

db.event.listen(Comment.body, 'set', Comment.on_changed_body)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return "<Message {}>".format(self.body)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))
    

@login.user_loader
def load_user(id):
    return User.query.get(int(id))



