from flask import redirect, url_for, flash, render_template
from blueprints.pages import bp
from .forms import AppConfigForm
from security.decorators import is_admin, is_fully_authenticated
from persistence.model.app_config import AppConfig


@bp.route('/')
@is_fully_authenticated
def home():
    return redirect(url_for('cams.list_all'))


@bp.route('/settings')
@is_fully_authenticated
@is_admin
def settings():
    config = AppConfig.get()
    form = AppConfigForm(obj=config)
    if form.validate_on_submit():
        form.populate_obj(config)
        config.save()
        flash('Settings modified successfully', 'success')
        return redirect(url_for('pages.settings'))

    return render_template('pages/settings.html', form=form)
