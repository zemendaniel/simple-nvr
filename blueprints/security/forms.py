from flask_wtf import FlaskForm
from wtforms.fields.simple import PasswordField, SubmitField, StringField
from wtforms.validators import DataRequired, length


class LoginForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), length(min=1, max=32)])
    password = PasswordField('Password', validators=[DataRequired(), length(min=4, max=32)])
    submit = SubmitField('Sign In')
