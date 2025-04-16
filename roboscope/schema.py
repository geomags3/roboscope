import re
from dataclasses import fields, is_dataclass
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


sqlalchemy_type_mapping = {
    bool: Integer,
    float: Float,
    int: Integer,
    str: String,
    datetime: DateTime,
    list: JSON,
    dict: JSON,
}


def camel_to_snake(name: str) -> str:
    """
    Convert CamelCase to snake_case
    """
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def generate_database_class(dataclass_type: type):
    """
    Generate a SQLAlchemy database class from a dataclass.

    Args:
        dataclass_type: The dataclass type to convert.

    Raises:
        TypeError: If the provided type is not a dataclass.
        ValueError: If the dataclass contains unsupported field types.

    Returns:
        A new SQLAlchemy model class with the same fields as the dataclass.
    """
    if not is_dataclass(dataclass_type):
        raise TypeError(f"{dataclass_type.__name__} is not a dataclass")

    table_name = camel_to_snake(dataclass_type.__name__)

    attrs = {
        "__tablename__": table_name,
        "id": Column(Integer, primary_key=True),
    }

    for f in fields(dataclass_type):
        if f.name == "run_id":
            attrs[f.name] = Column(Integer)
        elif f.type in sqlalchemy_type_mapping:
            attrs[f.name] = Column(sqlalchemy_type_mapping[f.type])
        else:
            raise ValueError(f"Unsupported field type: {f.name} {f.type}")

    @classmethod
    def from_model(cls, model):
        return cls(**model.__dict__)

    attrs["from_model"] = from_model

    return type(dataclass_type.__name__ + "DB", (Base,), attrs)
