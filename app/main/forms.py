from flask_wtf import FlaskForm
from flask_babel import _,  lazy_gettext as _l # _l is function lazy_gettext() as a convention
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Length
from flask import request
from app.models import User 
from flask_wtf.file import FileField, FileRequired
from flask_pagedown.fields import PageDownField

class EditProfileForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    about_me = TextAreaField(_l('About me'), validators=[Length(min=0, max=140)])
    submit = SubmitField(_l('Submit'))

    # EditProfileForm继承父类FlaskForm, edit页面可以包含很多内容, 所有属性数量应该和父类FlaskForm一样是任意的, 除了自有属性原用户名
    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username: # 如果更改的用户名和原用户名一样, 则通过验证
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError(_('Sorry, this username has already been registered.'))

class PostForm(FlaskForm):
    post = PageDownField(_l('Say something'), validators=[DataRequired()]) # Length(min=1, max=140)
    submit = SubmitField(_l('Submit'))

class EmptyForm(FlaskForm): # bridge to implement follow or unfollow action
    submit = SubmitField('Submit')

class SearchForm(FlaskForm):
    q = StringField(_l('Search'), validators=[DataRequired()])

    def __init__(self, *args, **kwargs): # class flask_wtf_FlaskForm(*args, **kwargs)
        if 'formdata' not in kwargs: # typically form submission lurks in request.form which is under post request, but search doesn't change anything but submit data, so get request is apporiate
            kwargs['formdata'] = request.args # get request entails a field values in the query string, flask-wtf writes query string arguments in request.args
        if 'meta' not in kwargs: # csrf protects web from malicious link, in order to make clickable search link work, disbale csrf 
            kwargs['meta'] = {'csrf': False} # class wtforms.form.Form(formdata=None, obj=None, prefix='', data=None, meta=None, **kwargs)
        super(SearchForm, self).__init__(*args, **kwargs)

class CommentForm(FlaskForm):
    body = PageDownField('', validators=[DataRequired()])
    submit = SubmitField(_l('Submit'))

class FileForm(FlaskForm):
    file = FileField(validators=[FileRequired()])
    submit = SubmitField(_l('Submit'))

class DeletePostForm(FlaskForm):
    Delete = SubmitField(_l('Delete'))

class DeleteCommentForm(FlaskForm):
    Delete = SubmitField(_l('Delete'))

class MessageForm(FlaskForm):
    message = TextAreaField(_l('Message'), validators=[DataRequired(), Length(min=0, max=140)])
    submit = SubmitField(_l('Submit'))


