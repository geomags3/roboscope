from enum import Enum  # noqa: N999

from matplotlib.ticker import EngFormatter
from robot.api import logger
from robot.api.deco import keyword, library

from roboscope.database import Database
from roboscope.models import BooleanMeasurement, MeasurementRecord, NumericMeasurement, SeriesMeasurement, StringMeasurement


class StringComparisonMode(str, Enum):
    LOG = "log"
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    REGEX = "regex"


@library(scope="GLOBAL", version="0.1.0")
class RoboScopeLib:
    """Robot Framework library for validating and recording measurements to RoboScope."""

    def __init__(self):
        self.db = None

    @keyword("Connect To RoboScope Database")
    def connect_to_database(self):
        self.db = Database()

    def _record_measurement(self, measurement: MeasurementRecord):
        if self.db:
            measurement.suite_id = self.db.current_suite_id
            measurement.test_id = self.db.current_test_id
            self.db.add_record(measurement)
        else:
            logger.warn(f"Database not connected. Measurement not recorded: {measurement}")

    @keyword("Check Numeric Measurement")
    def check_numeric_measurement(
        self,
        name: str,
        value: float,
        lower_limit: float | None = None,
        upper_limit: float | None = None,
        unit: str | None = None,
        error_message: str | None = None,
        meta: dict | None = None,
    ):
        value = float(value)
        lower_limit = float(lower_limit) if lower_limit is not None else None
        upper_limit = float(upper_limit) if upper_limit is not None else None
        unit = unit or ""
        error_message = f" {error_message}" if error_message else ""

        measurement = NumericMeasurement(
            name=name,
            value=value,
            lower_limit=lower_limit,
            upper_limit=upper_limit,
            unit=unit,
            meta=meta or {},
        )
        self._record_measurement(measurement)

        if unit:
            formatter = EngFormatter()
            lower_limit_str = formatter(lower_limit) if lower_limit is not None else "-inf"
            upper_limit_str = formatter(upper_limit) if upper_limit is not None else "inf"
            value_str = formatter(value)
        else:
            lower_limit_str = str(lower_limit)
            upper_limit_str = str(upper_limit)
            value_str = str(value)

        lower_limit = float(lower_limit) if lower_limit is not None else float("-inf")
        upper_limit = float(upper_limit) if upper_limit is not None else float("inf")

        if not lower_limit <= value <= upper_limit:
            raise AssertionError(
                f"Numeric check failed: "
                f"{value_str}{unit} not in [{lower_limit_str}{unit}...{upper_limit_str}{unit}]."
                f"{error_message}"
            )

    @keyword("Check String Measurement")
    def check_string_measurement(
        self,
        name: str,
        value: str,
        expected_value: str | None = None,
        mode: StringComparisonMode = StringComparisonMode.EQUAL,
        ignore_case: bool = False,
        error_message: str | None = None,
        meta: dict | None = None,
    ):
        measurement = StringMeasurement(
            name=name,
            value=value,
            expected_value=expected_value,
            mode=mode.value,
            ignore_case=ignore_case,
            meta=meta or {},
        )
        self._record_measurement(measurement)

        error_message = f" {error_message}" if error_message else ""

        if expected_value is None:
            return  # No check, just logging

        value_to_check = value.lower() if ignore_case else value
        expected_to_check = expected_value.lower() if ignore_case else expected_value

        if mode == StringComparisonMode.EQUAL:
            if value_to_check != expected_to_check:
                raise AssertionError(f"String check failed: '{value}' != '{expected_value}'.{error_message}")
        elif mode == StringComparisonMode.NOT_EQUAL:
            if value_to_check == expected_to_check:
                raise AssertionError(f"String check failed: '{value}' == '{expected_value}' (unexpected).{error_message}")
        elif mode == StringComparisonMode.REGEX:
            import re

            flags = re.IGNORECASE if ignore_case else 0
            if not re.match(expected_value, value, flags=flags):
                raise AssertionError(f"String regex check failed: '{value}' does not match '{expected_value}'.{error_message}")
        elif mode == StringComparisonMode.LOG:
            logger.info(f"String log: '{value}' (expected: '{expected_value}')")
        else:
            raise ValueError(f"Unsupported string comparison mode: {mode}")

    @keyword("Check Boolean Measurement")
    def check_boolean_measurement(
        self,
        name: str,
        value: bool,
        expected_value: bool = True,
        error_message: str | None = None,
        meta: dict | None = None,
    ):
        measurement = BooleanMeasurement(
            name=name,
            value=value,
            expected_value=expected_value,
            meta=meta or {},
        )
        self._record_measurement(measurement)

        error_message = f" {error_message}" if error_message else ""

        if value != expected_value:
            raise AssertionError(f"Boolean check failed: {value} != {expected_value}.{error_message}")

    @keyword("Check Series Measurement")
    def check_series_measurement(
        self,
        name: str,
        y_data: list[float],
        x_data: list[float] | None = None,
        y_lower_limits: list[float] | None = None,
        y_upper_limits: list[float] | None = None,
        x_label: str | None = None,
        y_label: str | None = None,
        x_unit: str | None = None,
        y_unit: str | None = None,
        error_message: str | None = None,
        meta: dict | None = None,
    ):
        measurement = SeriesMeasurement(
            name=name,
            x_data=x_data or [],
            y_data=y_data,
            x_label=x_label,
            y_label=y_label,
            x_unit=x_unit,
            y_unit=y_unit,
            lower_limits=y_lower_limits or [],
            upper_limits=y_upper_limits or [],
            meta=meta or {},
        )
        self._record_measurement(measurement)

        error_message = f" {error_message}" if error_message else ""

        for idx, y_value in enumerate(y_data):
            lower = y_lower_limits[idx] if y_lower_limits and idx < len(y_lower_limits) else float("-inf")
            upper = y_upper_limits[idx] if y_upper_limits and idx < len(y_upper_limits) else float("inf")

            if not lower <= y_value <= upper:
                raise AssertionError(f"Series check failed at index {idx}: {y_value} not in [{lower}...{upper}].{error_message}")
