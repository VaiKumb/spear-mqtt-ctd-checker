# spear-mqtt-ctd-checker

Standalone Python library and CLI that connects to the Spear MQTT broker, reads CTD (Conductivity, Temperature, Depth) sensor messages, and checks whether water **temperature** readings are **plausible** (valid) or **implausible** (invalid).

This project is independent of the `edge-sensors` ROS/GUI codebase. It reuses the same CTD protobuf schema, MQTT broker config format, buoy serial → UUID algorithm, and seawater plausibility range as edge-sensors.

## What it does

1. Connects to the Spear MQTT broker over TLS
2. Subscribes to CTD topics: `devices/<buoy_uuid>/sensors/ctd`
3. Deserializes `CtdSensor` protobuf payloads
4. Evaluates temperature plausibility
5. Reports results via terminal output, CLI, or **callbacks** for integration into other programs

### Two run modes

| Mode | Description |
|------|-------------|
| **Monitor one buoy** | Live listening; prints on status change + optional 30s heartbeat; runs until Ctrl+C |
| **Snapshot all buoys** | One-time table for all 35 buoys in the edge-sensors GUI dropdown; collects for ~15s then exits |

## Features

- TLS MQTT with username/password (same YAML config as edge-sensors)
- Interactive buoy selection: `BEN` / `MDA` + unit number (e.g. `02` → `BEN001-0000-00002`)
- Fleet snapshot aligned with edge-sensors GUI dropdown (`spear_gui._buoy_strs`)
- Plausibility checks aligned with edge-sensors `atlas_ct` seawater range
- Importable Python API with callbacks for valid/invalid transitions
- Parse-only API (no MQTT) for testing or custom pipelines
- Unit tests (`pytest`)

## Requirements

- Python 3.10+
- `protoc` (Protocol Buffers compiler) only if regenerating `ctd_pb2.py` from `proto/ctd.proto`

```bash
# Ubuntu
sudo apt install protobuf-compiler

# macOS
brew install protobuf
```

## Install

```bash
git clone https://github.com/<your-org>/spear-mqtt-ctd-checker.git
cd spear-mqtt-ctd-checker
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Development and tests:

```bash
pip install ".[test]"
pytest -v
```

## Broker configuration

Use the same nested YAML format as edge-sensors (e.g. `~/.ros/mqtt-broker-spear-hivemq.yaml`):

```yaml
/**/*:
  ros__parameters:
    host: your-broker.example.com
    port: 8883
    user: mda-buoy
    pass: your-password
```

Do not commit credentials to git.

---

## How to run

### Interactive (prompts for mode, then buoy if monitoring one)

**CLI:**

```bash
spear-ctd-checker --config ~/.ros/mqtt-broker-spear-hivemq.yaml
```

**Example script:**

```bash
python examples/run_checker.py
```

You will see:

```text
Select mode:
  1) Monitor one buoy (live updates + heartbeat)
  2) Snapshot all buoys (one-time status list)
Choice (1/2):
```

- **Option 1** — prompts for `BEN`/`MDA` and unit (e.g. `02`), then live monitoring
- **Option 2** — snapshot of all GUI fleet buoys, then exit

Stop live monitoring with **Ctrl+C**.

If `spear-ctd-checker` is not found:

```bash
pip install .
# or
.venv/bin/spear-ctd-checker --config ~/.ros/mqtt-broker-spear-hivemq.yaml
```

### Monitor one buoy (flags, no mode prompt)

```bash
spear-ctd-checker \
  --config ~/.ros/mqtt-broker-spear-hivemq.yaml \
  --family MDA \
  --unit 27
```

Or full serial / UUID:

```bash
spear-ctd-checker --config ~/.ros/mqtt-broker-spear-hivemq.yaml --serial MDA001-0000-00027
spear-ctd-checker --config ~/.ros/mqtt-broker-spear-hivemq.yaml --buoy-uuid <uuid>
```

Optional tuning:

```bash
spear-ctd-checker \
  --config ~/.ros/mqtt-broker-spear-hivemq.yaml \
  --family BEN --unit 02 \
  --max-age-sec 60 \
  --max-step-c 2.0 \
  --heartbeat-sec 30
```

Set `--heartbeat-sec 0` to disable periodic status prints.

### Snapshot all buoys (one-shot)

```bash
spear-ctd-checker \
  --config ~/.ros/mqtt-broker-spear-hivemq.yaml \
  --snapshot
```

Longer collection window (if buoys publish CTD slowly):

```bash
spear-ctd-checker \
  --config ~/.ros/mqtt-broker-spear-hivemq.yaml \
  --snapshot \
  --snapshot-wait-sec 60
```

Example output:

```text
Snapshot results: 3 buoy(s) with data, 32 with no data
SERIAL                 STATUS                       TEMP
----------------------------------------------------------------
BEN001-0000-00002      PLAUSIBLE                 12.340 C
MDA001-0000-00027      NO DATA                          -
MDA001-0000-00003      IMPLAUSIBLE (above_range) 87.200 C
```

`NO DATA` means no CTD message arrived for that buoy during the snapshot window — not necessarily that the buoy is offline.

### Run tests (no broker required)

```bash
pytest -v
```

On systems with ROS installed, pytest is preconfigured in `pyproject.toml` to avoid plugin conflicts (`-p no:launch_testing`).

---

## Output behavior (monitor one buoy)

| Output | When |
|--------|------|
| `PLAUSIBLE` (green) | Status changes to valid |
| `IMPLAUSIBLE` (red) | Status changes to invalid |
| `WAITING` (yellow) | Heartbeat, no readings yet |
| Heartbeat every 30s | Repeats latest status even if unchanged |

Callbacks fire on **status change only**, not every MQTT message.

---

## Buoy serial format

Serials follow edge-sensors naming:

```text
{BEN|MDA}001-0000-{unit zero-padded to 5 digits}
```

Examples:

- `BEN` + `02` → `BEN001-0000-00002`
- `MDA` + `27` → `MDA001-0000-00027`

MQTT topics use the buoy **UUID**, not the serial. Conversion uses the same UUID v5 algorithm as edge-sensors (`serial_to_buoy_uuid`).

---

## Plausibility rules

| Check | Reason code | Default |
|-------|-------------|---------|
| Finite temperature | `not_finite` | reject NaN/inf |
| Seawater range (-6, 45) °C | `below_range`, `above_range` | matches edge-sensors `atlas_ct` |
| Reading age from protobuf `stamp` | `stale` | max 60 s (skipped if stamp missing) |
| Step from previous reading | `unstable` | max 2.0 °C (skipped on first reading) |

---

## Library usage (import into other programs)

Install the package, then import from `spear_mqtt_ctd`.

### Live MQTT with custom actions on valid/invalid

```python
from spear_mqtt_ctd import CtdMqttClient, serial_to_buoy_uuid

def on_valid(temp, ctd):
    # your action when reading becomes plausible
    ...

def on_invalid(temp, reason, ctd):
    # your action when reading becomes implausible
    # reason: not_finite, below_range, above_range, stale, unstable
    ...

client = CtdMqttClient(
    config_path="~/.ros/mqtt-broker-spear-hivemq.yaml",
    buoy_uuid=serial_to_buoy_uuid("MDA001-0000-00027"),
    on_plausible=on_valid,
    on_implausible=on_invalid,
)

client.connect()
client.start()   # background MQTT thread
# ... your program ...
client.stop()
```

### Parse-only (no MQTT)

```python
from spear_mqtt_ctd import (
    evaluate_temperature_plausibility,
    extract_temperature,
    parse_ctd_payload,
)

ctd = parse_ctd_payload(raw_payload_bytes)
temp = extract_temperature(ctd)
result = evaluate_temperature_plausibility(temp, stamp=ctd.stamp)

if result.plausible:
    handle_valid(temp)
else:
    handle_invalid(temp, result.reason)
```

### Fleet snapshot (programmatic)

```python
from spear_mqtt_ctd import run_fleet_snapshot

rows = run_fleet_snapshot("~/.ros/mqtt-broker-spear-hivemq.yaml", wait_sec=15)

for row in rows:
    if row.status is None:
        handle_no_data(row.serial)
    elif row.status.plausible:
        handle_valid(row.serial, row.status.temperature)
    else:
        handle_invalid(row.serial, row.status.temperature, row.status.reason)
```

### Public API (main exports)

`CtdMqttClient`, `evaluate_temperature_plausibility`, `parse_ctd_payload`, `serial_to_buoy_uuid`, `build_buoy_serial`, `run_fleet_snapshot`, `gui_fleet_serials`, `PlausibilityResult`, and others — see `src/spear_mqtt_ctd/__init__.py`.

---

## Project layout

```text
proto/ctd.proto                 # CTD protobuf schema (from edge-sensors)
src/spear_mqtt_ctd/
  config.py                     # Load broker YAML
  uuid.py                       # Serial/UUID, prompts, mode selection
  fleet.py                      # GUI fleet buoy list (35 serials)
  parser.py                     # Deserialize CTD protobuf
  health.py                     # Plausibility + stability checks
  mqtt_client.py                # MQTT client (one buoy)
  snapshot.py                   # Fleet snapshot (all buoys)
  heartbeat.py                  # Periodic status for live monitor
  terminal.py                   # Colored / table output
  cli.py                        # spear-ctd-checker command
  status.py                     # Latest reading snapshot
tests/                          # pytest unit tests
examples/run_checker.py         # Minimal interactive example
```

---

## Relationship to edge-sensors

| Shared with edge-sensors | This project |
|--------------------------|--------------|
| `proto/ctd.proto` | Same message format |
| MQTT broker YAML | Same config path/shape |
| `serial_to_buoy_uuid` | Same algorithm |
| Seawater range -6°C to 45°C | Same as `atlas_ct` |
| GUI dropdown buoy list | Used for fleet snapshot |

This repo does **not** require ROS or the Spear GUI to run.

---

## License

Proprietary
