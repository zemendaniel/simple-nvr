from flask_wtf import FlaskForm
from wtforms.fields.simple import StringField
from wtforms.fields.numeric import IntegerField
from wtforms.validators import DataRequired, length
from wtforms.validators import NumberRange


class CamForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), length(min=1, max=32)])
    url = StringField('URL - eg. /dev/video0, http://cam.local/video, rtsp://cam.local', validators=[DataRequired(), length(min=1, max=255)])
    fps = IntegerField('FPS', validators=[DataRequired(), NumberRange(1, 60)])
    width = IntegerField('Width - eg. 1280, 1920', validators=[DataRequired(), NumberRange(1, 2000)])
    height = IntegerField('Height - eg. 720, 1080', validators=[DataRequired(), NumberRange(1, 2000)])
    sensitivity = IntegerField('Sensitivity - 1: most sensitive, 10000: least sensitive',
                               validators=[DataRequired(), NumberRange(1, 10000)])
    folder = StringField('Folder (make sure permissions are correct) - eg. /mnt/clips, clips', validators=[DataRequired(), length(min=1, max=255)])
