from typing import TYPE_CHECKING, Any, Self

from sqlalchemy import func

if TYPE_CHECKING:
    from roboscope.database import Database


class QueryBuilder:
    def __init__(self, db: "Database", model):
        self.db = db
        self.model = model
        self.db_class = db.model_to_db_class[model]
        self.query = db.Session().query(self.db_class)

    def where(self, **kwargs) -> Self:
        for attr, value in kwargs.items():
            if hasattr(self.db_class, attr):
                self.query = self.query.filter(getattr(self.db_class, attr) == value)
            else:
                raise ValueError(f"'{attr}' is not a valid attribute of {self.model.__name__}")
        return self

    def filter(self, filter_func) -> Self:
        self.query = self.query.filter(filter_func(self.db_class))
        return self

    def order_by(self, attr, order="asc") -> Self:
        if not hasattr(self.db_class, attr):
            raise ValueError(f"'{attr}' is not a valid attribute of {self.model.__name__}")

        sort_column = getattr(self.db_class, attr)
        self.query = self.query.order_by(sort_column.desc() if order == "desc" else sort_column.asc())
        return self

    def all(self) -> list:
        results = self.query.all()
        return [self.db._db_to_model(obj, self.model) for obj in results]

    def first(self) -> Any | None:
        result = self.query.first()
        return self.db._db_to_model(result, self.model) if result else None

    def limit(self, limit: int) -> Self:
        self.query = self.query.limit(limit)
        return self

    def offset(self, offset: int) -> Self:
        self.query = self.query.offset(offset)
        return self

    def values(self, *fields) -> list:
        if not all(hasattr(self.db_class, field) for field in fields):
            raise ValueError("One or more fields are invalid.")
        results = self.db.Session().query(*(getattr(self.db_class, f) for f in fields)).all()
        return results

    def max(self, field) -> Any:
        if not hasattr(self.db_class, field):
            raise ValueError(f"'{field}' is not a valid attribute of {self.model.__name__}")
        return self.query.with_entities(func.max(getattr(self.db_class, field))).scalar()

    def min(self, field) -> Any:
        if not hasattr(self.db_class, field):
            raise ValueError(f"'{field}' is not a valid attribute of {self.model.__name__}")
        return self.query.with_entities(func.min(getattr(self.db_class, field))).scalar()

    def where_in(self, field, values) -> Self:
        if not hasattr(self.db_class, field):
            raise ValueError(f"'{field}' is not a valid attribute of {self.model.__name__}")
        self.query = self.query.filter(getattr(self.db_class, field).in_(values))
        return self

    def group_by(self, *fields):
        field_objects = []
        for field in fields:
            if isinstance(field, str):
                if not hasattr(self.model, field):
                    raise AttributeError(f"{self.model.__name__} has no attribute '{field}'")
                field_objects.append(getattr(self.model, field))
            else:
                field_objects.append(field)
        self._query = self.query.group_by(*field_objects)
        return self

    def count(self) -> int:
        return self.query.count()

    def explain(self) -> Self:
        # Print the raw SQL query
        print(str(self.query.statement.compile(compile_kwargs={"literal_binds": True})))
        return self

    def as_dataframe(self) -> Any:
        """
        Convert the query results to a pandas DataFrame.
        """
        import pandas as pd

        results = self.all()
        if not results:
            return pd.DataFrame()

        # Convert list of dataclass instances to list of dictionaries
        data = [record.__dict__ for record in results]
        return pd.DataFrame(data)
