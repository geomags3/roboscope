from dataclasses import fields as dataclass_fields
from datetime import UTC, datetime

from robot.api import logger
from sqlalchemy import create_engine, func, inspect
from sqlalchemy.orm import sessionmaker

from roboscope.models import Failure, Record, TestCase, TestRun, TestSuite
from roboscope.query import QueryBuilder
from roboscope.schema import generate_database_class


class Database:
    _instance = None
    LOGGER_PREFIX = "[RoboScope DB] "

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_url: str = "sqlite:///results.db"):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.inspector = inspect(self.engine)

        self.model_to_db_class = {}
        self._run_id = None
        self._suite_counter = 0
        self._test_counter = 0

        # Create core tables
        self.initialize_table(TestRun)
        self.initialize_table(TestSuite)
        self.initialize_table(TestCase)
        self.initialize_table(Failure)

        logger.debug(f"{self.LOGGER_PREFIX}Database connected: {db_url}")

    @property
    def run_id(self) -> int:
        if self._run_id is None:
            raise RuntimeError(
                "No active test run.\n"
                "- If you are using RoboScope manually, call 'start_new_run()' before recording data.\n"
                "- If you are using RoboScope with Robot Framework, make sure to pass '--listener roboscope.listener' "
                "when running tests to auto-start a run.\n"
            )
        return self._run_id

    @property
    def current_suite_id(self) -> int:
        return self._suite_counter

    @property
    def current_test_id(self) -> int:
        return self._test_counter

    def check_table_exists(self, model) -> bool:
        if model in self.model_to_db_class:
            return self.model_to_db_class[model]

        db_class = generate_database_class(model)
        table_name = db_class.__tablename__

        if not self.inspector.has_table(table_name):
            return False
        else:
            self.model_to_db_class[model] = db_class
            return True

    def initialize_table(self, model) -> type:
        if model in self.model_to_db_class:
            return self.model_to_db_class[model]

        db_class = generate_database_class(model)
        self.model_to_db_class[model] = db_class

        table_name = db_class.__tablename__
        if not self.inspector.has_table(table_name):
            db_class.__table__.create(bind=self.engine, checkfirst=True)
            logger.debug(f"{self.LOGGER_PREFIX}Table '{table_name}' created.")
        return db_class

    def allocate_run_id(self) -> int:
        db_class = self.model_to_db_class[TestRun]
        with self.Session() as session:
            result = session.query(func.max(db_class.run_id)).scalar()
            return (result or 0) + 1

    def allocate_suite_id(self) -> int:
        self._suite_counter += 1
        return self._suite_counter

    def allocate_test_id(self) -> int:
        self._test_counter += 1
        return self._test_counter

    def start_new_run(self, run_name: str, run_meta: dict):
        self._run_id = self.allocate_run_id()
        self._suite_counter = 0
        self._test_counter = 0
        logger.debug(f"{self.LOGGER_PREFIX}New run started with run_id: {self._run_id}")

        new_run = TestRun(run_id=self._run_id, name=run_name, meta=run_meta)
        self.add_record(new_run)

    def end_run(self):
        db_class = self.model_to_db_class[TestRun]
        suite_class = self.model_to_db_class[TestSuite]

        with self.Session() as session:
            # 1. Check statuses of all TestSuites for this run
            suite_statuses = session.query(suite_class.status).filter(suite_class.run_id == self._run_id).all()
            suite_statuses = [status[0] for status in suite_statuses]

            if not suite_statuses:
                final_status = "PASS"
                logger.warn(f"{self.LOGGER_PREFIX}No TestSuites found for run {self._run_id}. Defaulting status to PASS.")
            elif "FAIL" in suite_statuses:
                final_status = "FAIL"
            else:
                final_status = "PASS"

            # 2. Calculate start time, end time, elapsed time
            times = (
                session.query(
                    func.min(suite_class.start_time),
                    func.max(suite_class.end_time),
                )
                .filter(suite_class.run_id == self._run_id)
                .first()
            )

            start_time, end_time = times

            if start_time and end_time:
                elapsed_time = (end_time - start_time).total_seconds()
            else:
                # If no suites, fallback to current time
                start_time = end_time = datetime.now(UTC)
                elapsed_time = 0.0
                logger.warn(f"{self.LOGGER_PREFIX}No suite timings found for run {self._run_id}. Setting elapsed time to 0.")

            # 3. Update TestRun record
            run_record = session.query(db_class).filter(db_class.run_id == self._run_id).first()

            if run_record:
                run_record.status = final_status
                run_record.start_time = start_time
                run_record.end_time = end_time
                run_record.elapsed_time = elapsed_time

                session.commit()

                logger.debug(
                    f"{self.LOGGER_PREFIX}Run {self._run_id} marked as {final_status}. "
                    f"Start: {start_time}, End: {end_time}, Elapsed: {elapsed_time:.3f} seconds."
                )
            else:
                logger.warn(f"{self.LOGGER_PREFIX}No TestRun record found for run_id {self._run_id}.")

    def disconnect(self):
        logger.debug("{self.LOGGER_PREFIX}Database disconnected.")
        self.engine.dispose()

    def add_record(self, record: Record):
        with self.Session() as session:
            try:
                record.run_id = self.run_id
                db_class = self.model_to_db_class.get(type(record))

                if not db_class:
                    db_class = self.initialize_table(type(record))

                db_obj = db_class.from_model(record)
                session.add(db_obj)
                session.commit()
                logger.debug(f"{self.LOGGER_PREFIX}Record added: {record}")

            except Exception as e:
                logger.error(f"{self.LOGGER_PREFIX}Error adding record: {e}")
                session.rollback()

    def _db_to_model(self, db_obj, model_class):
        model_field_names = {f.name for f in dataclass_fields(model_class)}
        db_data = {column.name: getattr(db_obj, column.name) for column in db_obj.__table__.columns}
        filtered_data = {k: v for k, v in db_data.items() if k in model_field_names}
        return model_class(**filtered_data)

    def query(self, model) -> QueryBuilder:
        """
        Create a QueryBuilder for the specified model.

        :param model: Dataclass model (e.g., TestRun, TestSuite)
        :return: QueryBuilder instance
        """
        if not self.check_table_exists(model):
            raise ValueError(f"Model '{model.__name__}' does not exist in the database.")

        return QueryBuilder(self, model)
