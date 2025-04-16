# RoboScope

**A Python toolkit for recording structured test measurements in Robot Framework using SQLite or PostgreSQL.**

RoboScope is a database-backed test automation framework designed for **hardware test environments**. It allows you to **record structured measurements** (numeric, string, boolean, series, etc.) during Robot Framework test execution and store them in a clean, queryable format using SQLite or PostgreSQL.


## ✨ Features

- ✅ Simple setup with SQLite or PostgreSQL
- 📐 Structured measurement types (numeric, boolean, string, series, condition)
- 🧩 Easy integration with Robot Framework as a test library
- 🧾 Built-in listener to capture run/suite/test metadata
- 📊 Designed for post-test analysis (supports Streamlit Dashboards via [RoboScope UI](https://github.com/geomags3/roboscope-ui))
- 💡 Easily extendable with custom measurement dataclasses


## 📦 Installation

```bash
pip install roboscope
```

## 🛠️ Usage in Robot Framework

### 1. Add RoboScopeLib to your test suite

```robot
*** Settings ***
Library    RoboScopeLib.py
Test Setup    Connect To RoboScope Database
```

### 2. Record measurements in your test cases

```robot
*** Test Cases ***
Temperature Test
    Check Numeric Measurement    name=Temperature    value=${temperature}
    ...    lower_limit=${TEMP_LIMIT_LOW}    upper_limit=${TEMP_LIMIT_HIGH}    meta=${meta}    unit=°C
    ...    error_message=Temperature out of range

Device Firmware Test
    Check String Measurement    name=Device Firmware Version    value=${fw_version}    expected_value=^FW-\\d{3}\\.rev\\d$
    ...    mode=regex    meta=${meta}    error_message=Firmware version format mismatch

Device Status Test
    Check Boolean Measurement    name=Device Status    value=${device_status}    expected_value=${True}
    ...    meta=${meta}    error_message=Device status is not True

Signal Validation Test
    Check Series Measurement    name=Signal Validation
    ...    y_data=${amplitudes}    x_data=${timestamps}    x_label=Time    y_label=Amplitude
    ...    y_lower_limits=${lower_limit}    y_upper_limits=${upper_limit}    meta=${meta}    error_message=Amplitude out of range
```

### 3. Run your tests with the RoboScope listener
You can run your tests with the RoboScope listener to capture test metadata and measurements.

```bash
robot --listener roboscope.listener path/to/tests/
```

The listener supports the following **optional Robot Framework variables**:

| Variable          | Description                                                      | Default                |
| ----------------- | ---------------------------------------------------------------- | ---------------------- |
| `${RBS_DB_URL}`   | Database URL (`sqlite:///results.db`, `postgresql://...`)        | `sqlite:///results.db` |
| `${RBS_RUN_NAME}` | Name of the test run (appears in dashboard)                      | `RoboScope Test`       |
| `${RBS_RUN_META}` | Metadata for the test run in `key=value` format, comma-separated | `None`                 |

**Example with custom parameters:**

```bash
robot \
  --variable RBS_DB_URL:sqlite:///my_test_results.db \
  --variable RBS_RUN_NAME:"Release 1.2.0" \
  --variable RBS_RUN_META:"build=1.2.0,env=staging" \
  --listener roboscope.listener \
  path/to/tests/
```

## 📁 Project Structure

```bash
roboscope/
├── database.py          # Database module with query functions
│   listener.py          # Robot Framework listener for capturing test run, suite, test, and failure data
├── models.py            # Built-in measurement dataclasses (Numeric, String, Boolean, Series) (extendable)
├── RoboScopeLib.py      # Main library for Robot Framework. Contains measurement functions and database connection
└── ...
```

## 📈 Visualizing Results
Use the companion UI tool [RoboScope UI](https://github.com/geomags3/roboscope-ui) to visualize and filter your test measurements.

## 🧩 Custom Measurements
You can create custom measurement classes by extending the `MeasurementRecord` class. This allows you to define your own measurement types and validation logic.

```python
from roboscope import MeasurementRecord
from dataclasses import dataclass

@dataclass
class VoltageDrop(MeasurementRecord):
    value: float
    expected: float
    meta: dict = field(default_factory=dict)
```

And record it in your test case:

```robot
*** Test Cases ***
Voltage Drop Test
    Check Voltage Drop    name=Voltage Drop    value=${voltage_drop}    expected=${expected_drop}    meta=${meta}
```

## 📄 License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 💬 Contributing
Pull requests and feedback are more than welcome! 🙌