from collections.abc import Mapping
from datetime import timedelta

from robot import result, running
from robot.api import logger
from robot.api.interfaces import ListenerV3
from robot.libraries.BuiltIn import BuiltIn

from roboscope.database import Database
from roboscope.models import Failure, TestCase, TestSuite


class listener(ListenerV3):  # noqa: N801
    LOGGER_PREFIX = "[RoboScope Listener] "

    def __init__(self):
        self.db = None
        self.suite_stack = []
        self.current_test_id = None
        self.initialized = False

    def _initialize(self):
        """Initialize the listener and database connection."""
        logger.info(f"{self.LOGGER_PREFIX}Initializing RoboScopeListener")

        # Get variables from Robot Framework
        db_url = BuiltIn().get_variable_value("${RBS_DB_URL}", default="sqlite:///results.db")
        test_run_name = BuiltIn().get_variable_value("${RBS_RUN_NAME}", default="RoboScope Test")
        test_run_meta = BuiltIn().get_variable_value("${RBS_RUN_META}", default="")  # Format: "key1=value1,key2=value2"

        self.db = Database(db_url=db_url)
        self.db.start_new_run(
            run_name=test_run_name,
            run_meta=self._extract_run_metadata(test_run_meta),
        )
        self.initialized = True

    @staticmethod
    def _timedelta_to_seconds(value) -> float:
        """Convert timedelta to seconds."""
        if isinstance(value, timedelta):
            return value.total_seconds()
        return value

    def _extract_run_metadata(self, meta_string: str) -> dict:
        """Get meta information about the current run."""
        meta_dict = {}
        if meta_string:
            try:
                for item in meta_string.split(","):
                    key, value = item.split("=", 1)
                    meta_dict[key.strip()] = value.strip()
                logger.info(f"{self.LOGGER_PREFIX}Parsed run meta: {meta_dict}")
            except Exception as e:
                logger.error(f"{self.LOGGER_PREFIX}Error parsing meta string '{meta_string}': {e}")
                raise ValueError(f"Invalid meta string format: '{meta_string}'. Expected 'key1=value1,key2=value2'")
        return meta_dict

    def start_suite(self, data: running.TestSuite, result: result.TestSuite):
        if not self.initialized:
            self._initialize()

        # Allocate suite_id
        suite_id = self.db.allocate_suite_id()
        parent_suite_id = self.suite_stack[-1][0] if self.suite_stack else None
        logger.info(f"{self.LOGGER_PREFIX}Starting suite '{data}' (suite_id: {suite_id}, parent_suite_id: {parent_suite_id})")

        # Track in stack
        self.suite_stack.append((suite_id, data))

    def end_suite(self, data: running.TestSuite, result: result.TestSuite):
        suite_id, suite_data = self.suite_stack.pop()
        parent_suite_id = self.suite_stack[-1][0] if self.suite_stack else None

        logger.info(f"{self.LOGGER_PREFIX}Ending suite '{suite_data}' (suite_id: {suite_id})")

        metadata_dict = {}
        if hasattr(result, "metadata") and isinstance(result.metadata, Mapping):
            metadata_dict = dict(result.metadata)
        logger.info(f"{self.LOGGER_PREFIX}Parsed suite metadata: {metadata_dict}")

        # Record suite event
        self.db.add_record(
            TestSuite(
                suite_id=suite_id,
                parent_suite_id=parent_suite_id,
                meta=metadata_dict,
                name=getattr(result, "name", ""),
                start_time=getattr(result, "start_time", None),
                end_time=getattr(result, "end_time", None),
                elapsed_time=self._timedelta_to_seconds(result.elapsed_time) if hasattr(result, "elapsed_time") else None,
                status=getattr(result, "status", ""),
            )
        )

    def start_test(self, data: running.TestCase, result: running.TestCase):
        # Allocate test_id
        test_id = self.db.allocate_test_id()
        suite_id = self.suite_stack[-1][0] if self.suite_stack else None

        logger.info(f"{self.LOGGER_PREFIX}Starting test '{data.name}' (test_id: {test_id}, suite_id: {suite_id})")

        # Track current test_id
        self.current_test_id = test_id

    def end_test(self, data: running.TestCase, result: running.TestCase):
        suite_id = self.suite_stack[-1][0] if self.suite_stack else None

        logger.info(f"{self.LOGGER_PREFIX}Ending test '{data.name}' (test_id: {self.current_test_id}, suite_id: {suite_id})")

        tags_list = list(getattr(result, "tags", []))
        logger.info(f"{self.LOGGER_PREFIX}Test case '{data.name}' tags: {tags_list}")

        # Record test case event
        self.db.add_record(
            TestCase(
                suite_id=suite_id,
                test_id=self.current_test_id,
                tags=tags_list,
                name=getattr(result, "name", ""),
                start_time=getattr(result, "start_time", None),
                end_time=getattr(result, "end_time", None),
                elapsed_time=self._timedelta_to_seconds(result.elapsed_time) if hasattr(result, "elapsed_time") else None,
                status=getattr(result, "status", ""),
            )
        )

        # Reset test tracking
        self.current_test_id = None

    def end_keyword(self, data: running.Keyword, result: result.Keyword):
        # Record failure if keyword has failed
        if hasattr(result, "status") and result.status != "FAIL":
            return

        suite_id = self.suite_stack[-1][0] if self.suite_stack else None
        test_id = self.current_test_id

        logger.info(f"{self.LOGGER_PREFIX}Recording failure in keyword '{data}' (test_id: {test_id}, suite_id: {suite_id})")

        self.db.add_record(
            Failure(
                suite_id=suite_id,
                test_id=test_id,
                source=getattr(result, "name", ""),
                details=getattr(result, "message", ""),
                timestamp=getattr(result, "end_time", None),
            )
        )

    def close(self):
        logger.info("{self.LOGGER_PREFIX}Closing RoboScopeListener")
        if self.db:
            self.db.end_run()
            self.db.disconnect()
        else:
            logger.warn("Database was not initialized. Skipping end_run and disconnect.")
