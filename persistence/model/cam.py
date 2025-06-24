from alchemical import Model
from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from persistence.model.app_config import AppConfig
import os
import shutil
from flask import g


class Cam(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    # folder: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    fps: Mapped[int] = mapped_column(Integer(), nullable=False)
    width: Mapped[int] = mapped_column(Integer(), nullable=False)
    height: Mapped[int] = mapped_column(Integer(), nullable=False)
    sensitivity: Mapped[int] = mapped_column(Integer(), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean(), default=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean(), default=True)

    def save(self):
        g.session.add(self)
        g.session.commit()
        os.makedirs(f"{AppConfig.get().root_folder}/cams/{self.id}", exist_ok=True)

    def delete(self):
        g.session.delete(self)
        g.session.commit()
        if os.path.exists(f"{AppConfig.get().root_folder}/cams/{self.id}"):
            shutil.rmtree(f"{AppConfig.get().root_folder}/cams/{self.id}")


from persistence.repository.cam import CamRepository
