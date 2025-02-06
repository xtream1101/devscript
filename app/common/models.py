from collections import defaultdict

from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    @property
    def as_dict(self):
        output_dict = defaultdict(lambda: None)

        mapper = inspect(self)
        for column in mapper.attrs:
            try:
                output_dict[column.key] = column.value
            except Exception:
                # If the column is relational, and has not been loaded, it will raise an exception
                continue

        return output_dict
