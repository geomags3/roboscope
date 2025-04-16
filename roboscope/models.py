from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Record:
    pass


@dataclass
class EventRecord(Record):
    run_id: int = None
    name: str = ""
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime = None
    elapsed_time: float = 0.0
    status: str = ""


@dataclass
class MeasurementRecord(Record):
    run_id: int = None
    suite_id: int = None
    test_id: int = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class TestRun(EventRecord):
    meta: dict = field(default_factory=dict)


@dataclass
class TestSuite(EventRecord):
    suite_id: int = None
    parent_suite_id: int = None  # None if top-level suite
    meta: dict = field(default_factory=dict)  # Meta info defined in the test suite


@dataclass
class TestCase(EventRecord):
    suite_id: int = None
    test_id: int = None
    tags: list = field(default_factory=list)  # Tags defined in the test case


@dataclass
class Failure(Record):
    run_id: int = None
    suite_id: int = None
    test_id: int = None
    source: str = ""
    details: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# Measurement Models


@dataclass
class NumericMeasurement(MeasurementRecord):
    meta: dict = field(default_factory=dict)
    name: str = None
    value: float = None
    lower_limit: float = None
    upper_limit: float = None
    unit: str = None


@dataclass
class StringMeasurement(MeasurementRecord):
    meta: dict = field(default_factory=dict)
    name: str = None
    value: str = None
    expected_value: str = None
    mode: str = None
    ignore_case: bool = False


@dataclass
class BooleanMeasurement(MeasurementRecord):
    meta: dict = field(default_factory=dict)
    name: str = None
    value: bool = None
    expected_value: bool = None


@dataclass
class SeriesMeasurement(MeasurementRecord):
    meta: dict = field(default_factory=dict)
    name: str = None
    x_data: list = field(default_factory=list)
    y_data: list = field(default_factory=list)
    lower_limits: list = field(default_factory=list)
    upper_limits: list = field(default_factory=list)
    x_label: str = None
    y_label: str = None
    x_unit: str = None
    y_unit: str = None
