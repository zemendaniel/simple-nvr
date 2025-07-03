from flask_wtf import FlaskForm
from wtforms.fields.simple import StringField, BooleanField
from wtforms.validators import DataRequired, Optional


class AppConfigForm(FlaskForm):
    # root_folder = StringField('Root folder for clips', validators=[DataRequired()])
    discord_webhook = StringField('Discord webhook URL (optional)', validators=[Optional()])
    notifications_enabled = BooleanField('Notifications enabled')
    root_url = StringField('Your root url eg. https://example.com')
