from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from flask_babel import _, lazy_gettext as _l
from app.models import User

class LoginForm(FlaskForm): # 继承FlaskForm的表单, 发送请求都有CSRF安全保护, 确保在模板中可添加form.csrf_token和form.hidden_tag
    # field is defined as memebers on a form(字段)
    # StringField, PasswordField, BooleanField is subclass of base class field
    username = StringField(_l('Username'), validators=[DataRequired()]) # represents and render<input type='text'> {{ form.username(size=20) }}
    password = PasswordField(_l('Password'), validators=[DataRequired()]) # represents and render<input type="password">
    remember_me = BooleanField(_l('Remember Me')) # represents and render<input type="checkbox">
    submit = SubmitField(_l('Sign In')) # represents and render <input type="submit">

class RegistrationForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    email = StringField(_l('Email'), validators=[DataRequired(), Email()]) # 函数Email()验证email地址正确性, 需要额外安装pip install email-validator
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    # 字段password2用来验证用户输入第一次输入的字段password正确无误, EqualTo验证字段值匹配第一个password
    password2 = PasswordField(_l('Repeat Password'), validators=[DataRequired(), EqualTo('password')]) 
    submit = SubmitField(_l('Register'))

    # 以validate_fieldname(form_instance, fieldname)形式命名的表单类方法, 在validate_on_submit()验证时会自动调用该方法, 类似unittest类下的test_name方法
    def validate_username(self, username): 
        # 用username过滤来查询是否和数据库User中字段user重名, 若是则返回验证错误
        user = User.query.filter_by(username=username.data).first() 
        if user is not None: 
            # ValidationError(message)返回验证失败, message作为报错信息在在浏览器中提示给用户.
            raise ValidationError(_('Please enter a different username.'))

    def validate_email(self, email):
        # email过滤查询是否和数据库User中email重名，若是返回验证错误
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(_('Please enter a different email.'))

class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    submit = SubmitField(_l('Request Password Reset'))

class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(_l('Repeat Password'), validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(_l('Request Password Reset'))
