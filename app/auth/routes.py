from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user, logout_user
from flask_babel import _ 
from werkzeug.urls import url_parse
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from app.auth.email import send_password_reset_email
from app.auth import bp 
from app import db 
from app.models import User 

@bp.route('/login', methods=['GET', 'POST']) # url_prefix='/auth' automatically incorporates the prefix, thus omits '/auth' 
def login():
    if current_user.is_authenticated: # current_user获取代表请求端的用户对象
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit(): # don't have to pass request.form, 
        # it will be load automaticlly, validate_on_submit check if it is a post and if it is valid, returns True
        # validate_on_submit()通过调用表单类字段中传入的验证函数以及自动调用validate_fieldname形式的自定义验证方法来确定提交是否合法
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash(_('Invalid username or password'))
            return redirect(url_for('auth.login')) # 定义在蓝图内部的视图函数, url_for(arg)中参数必须是'blueprint_name.fuction_name'的形式
        login_user(user, remember=form.remember_me.data)
        # 用户尝试访问某些特定需要登录才能访问的页面page_url时, 会重定向至登陆页面, 并且会在登录页面URL即'/login'末尾添加next查询字符串参数,
        # 生成完整URL:='/login?next=page_url’ 以便登录成功后重定向至page_url页面.(添加方式是以键值对的形式)
        next_page = request.args.get('next') # request包含了客户端请求信息, request.args以MutiDict形式包含查询字符串内容, get(key, defalut=None, type=None): type is callable and will convert key's value or return default's value.
        if not next_page or url_parse(next_page).netloc != '': # 若netloc不空, 即包含域名domain, 出于安全考虑得在当前网站范围内跳转,
            next_page = url_for('main.index')                       # 而不是可能重定向至外部网站，故令next_page='index'重定向网站主页.
        return redirect(next_page)
    return render_template('auth/login.html', form=form, title=_('Sign In'))

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_('Congratulations, you are now a registered user!'))
        return redirect(url_for('auth.login')) # 注册成功就转至登录页面
    return render_template('auth/register.html', title=_('Register'), form=form)

@bp.route('/reset_password_request', methods=['GET','POST'])
def reset_password_request(): # 重置密码仅限于欲登录但是遗忘密码的用户, 故已登录用户无须重置
    if current_user.is_authenticated: # 若用户已登录, 则重定向主页
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first() # 输入绑定的邮箱地址, 接收验证链接
        if user:
            send_password_reset_email(user)
        flash(_('Check your password for the instructions to reset your password'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', title=_('Reset Password'), form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('Your password has been reset successfully.'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)