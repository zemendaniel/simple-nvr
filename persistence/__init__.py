import os

from werkzeug.security import generate_password_hash
import click
from alchemical.flask import Alchemical
from flask import g

db = Alchemical()


def init_app(app):
    app.cli.add_command(__install_command)
    app.cli.add_command(__reset_admin_command)
    app.before_request(__on_before_request)
    app.teardown_appcontext(__on_teardown_appcontext)

    db.init_app(app)


def install():
    db.drop_all()
    db.create_all()
    reset_admin()

    default_root = 'clips'
    os.makedirs(default_root, exist_ok=True)

    config = AppConfig(
        id=1,
        root_folder=default_root
    )
    with db.Session() as session:
        session.add(config)
        session.commit()

    with open("INSTALLED", "w"):
        pass


def reset_admin():
    with db.Session() as session:
        admin = session.scalar(User.select().where(User.role == 'admin'))
        if admin:
            session.delete(admin)
            session.commit()
        admin = User()
        admin.name = input("Admin username:\n").strip()
        admin.role = "admin"
        admin.password = generate_password_hash(input("Admin password (min 4 chars):\n"))

        session.add(admin)
        session.commit()


@click.command('install')
def __install_command():
    install()
    click.echo('Application installation successful.')


@click.command('reset-admin')
def __reset_admin_command():
    reset_admin()
    click.echo('Admin reset successful.')


def __on_before_request():
    if 'session' in g:
        g.session.close()
        del g.session

    g.session = db.Session()


def __on_teardown_appcontext(e):
    if 'session' in g:
        g.session.close()
        del g.session


from persistence.model.user import User
from persistence.model.app_config import AppConfig
