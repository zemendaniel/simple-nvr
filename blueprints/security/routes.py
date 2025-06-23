from urllib.parse import urlsplit
from persistence.repository.user import UserRepository
from flask import g, redirect, url_for, session, flash, request, render_template
from blueprints.security import bp
from .forms import LoginForm


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if g.user is not None:
        return redirect(url_for('pages.home'))

    form = LoginForm()

    if form.validate_on_submit():
        user = UserRepository.find_by_name(form.name.data.strip())

        if user is not None and user.check_password(form.password.data):
            session['user_id'] = user.id
            session.permanent = True
            flash('Sign In successful.', 'success')
            if request.args.get('redirect') is not None and urlsplit(request.args.get('redirect')).netloc == '':
                return redirect(request.args.get('redirect'))
            else:
                return redirect(url_for('pages.home'))

        elif user is None:
            flash('Incorrect username.', 'error')
        elif not user.check_password(form.password.data):
            flash("Incorrect password.", 'error')

    return render_template('security/login.html', form=form)
