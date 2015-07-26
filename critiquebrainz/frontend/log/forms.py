from flask_wtf import Form
from flask_babel import gettext
from wtforms import TextAreaField, validators


class AdminActionForm(Form):
    reason = TextAreaField(validators=[
        validators.DataRequired(message=gettext("You need to sepicify a reason for taking this action."))
    ])
