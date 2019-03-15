try:
    from unittest.mock import patch
except ImportError:
    from mock import patch  # type: ignore

from decorator import decorator
from psycopg2 import connect, extensions
from sqlalchemy import create_engine
from sqlalchemy.sql.elements import TextClause

from pytest_mock_resources.container.postgres import config
from pytest_mock_resources.patch.redshift.create_engine import (
    execute_mock_s3_copy_command,
    execute_mock_s3_unload_command,
)
from pytest_mock_resources.patch.redshift.mock_s3_copy import strip


class CustomCursor(extensions.cursor):
    """A custom cursor class to define a custom execute method."""

    def execute(self, sql, args=None):
        dsn_params = self.connection.get_dsn_parameters()
        engine = create_engine(
            "postgresql://{user}:{password}@{hostname}:{port}/{dbname}".format(
                user=dsn_params["user"],
                password=config["password"],
                hostname=dsn_params["host"],
                port=dsn_params["port"],
                dbname=dsn_params["dbname"],
            )
        )
        if not isinstance(sql, TextClause) and strip(sql).lower().startswith("copy"):
            return execute_mock_s3_copy_command(sql, engine)
        if not isinstance(sql, TextClause) and strip(sql).lower().startswith("unload"):
            return execute_mock_s3_unload_command(sql, engine)
        return extensions.cursor.execute(self, sql, args)


@decorator
def patch_psycopg2_connect(func, path=None, *args, **kwargs):
    """Patch any occourances of `psycopg2.connect` with mock_psycopg2_connect function."""
    if path is None:
        raise ValueError("Path cannot be None")

    with patch(path, new=mock_psycopg2_connect):
        return func(*args, **kwargs)


def mock_psycopg2_connect(*args, **kwargs):
    """Substitute the default cursor with a custom cursor."""
    conn = connect(cursor_factory=CustomCursor, *args, **kwargs)
    return conn