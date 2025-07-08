# alembic/env.py
from app.settings import db_url
config.set_main_option("sqlalchemy.url", db_url())