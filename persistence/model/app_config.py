from alchemical import Model
from sqlalchemy import Boolean, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from flask import g


class AppConfig(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=True)
    discord_webhook: Mapped[str] = mapped_column(Text, nullable=True)
    root_folder: Mapped[str] = mapped_column(Text, nullable=False)

    @staticmethod
    def get():
        return g.session.get(AppConfig, 1)

    def save(self):
        g.session.add(self)
        g.session.commit()
