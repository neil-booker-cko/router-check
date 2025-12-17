# Network Compliance Auditor

A Python-based automation tool to audit Cisco IOS/IOS-XE routing tables, BGP neighbors, and OSPF adjacencies against a defined "Gold Standard."

Built using **Nornir** for concurrency, **Genie** for parsing, and **Pytest** for validation.

## 📋 Features

- **Concurrency:** Audits multiple routers simultaneously (threaded).
- **Structured Parsing:** Uses Cisco Genie to convert CLI output (`show ip route`, etc.) into Python dictionaries—no Regex required.
- **YAML-based Rules:** Compliance logic is defined in simple YAML files, separating logic from configuration.
- **Audit Trail:** Generates a persistent log file (`compliance.log`) tracking every pass/fail event.
- **Test Suite:** Includes Pytest fixtures to validate the auditing logic without connecting to real devices.

## 🛠️ Prerequisites

- Python 3.8+
- Access to Cisco IOS/IOS-XE devices via SSH.

## 📦 Installation

1. Clone this repository or create the directory structure.
1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

*(See `requirements.txt` for the full list: `nornir`, `nornir_netmiko`, `genie`, `pyyaml`, `pytest`, etc.)*

## 🚀 Usage

### 1. Define your Inventory

Edit `hosts.yaml` to list your target routers.

```yaml
R1:
  hostname: "192.168.1.1"
  groups: ["core_routers"]
R2:
  hostname: "192.168.1.2"
  groups: ["access_switches"]
```

### 2. Define Compliance Rules

Edit `compliance_rules.yaml` to set your expected state.

```yaml
static_routes:
  - prefix: "192.168.10.0/24"
    next_hop: "10.1.1.2"

bgp:
  neighbors:
    - ip: "10.2.2.2"
      state: "Established"
```

### 3. Run the Auditor

Execute the main script:

```bash
python runner.py
```

You will see a summary on the console. Detailed PASS/FAIL logs are written to `compliance.log`.

### 4. Advanced: Role-Based Compliance

If you have different requirements for different devices (e.g., Core vs. Access), you can structure your `compliance_rules.yaml` by group keys matching your inventory groups:

```yaml
core_routers:
  bgp:
    local_asn: 65001
  static_routes: [...]

access_switches:
  # Switches might not need BGP checks
  static_routes:
    - prefix: "0.0.0.0/0"
      next_hop: "192.168.1.1"
```

*Note: You will need to update `runner.py` to select the specific rule block based on `task.host.groups[0]`.*

### 5. Handling Variable Data (Per-Site ASNs)

For values that vary by site (like AS Numbers), it is best practice to define the expected value in the inventory (`hosts.yaml`) rather than a static rule file.

**hosts.yaml**

```yaml
R1:
  hostname: "192.168.1.1"
  data:
    expected_asn: 65100  # <--- Site A ASN
R2:
  hostname: "192.168.2.1"
  data:
    expected_asn: 65200  # <--- Site B ASN
```

**runner.py Adjustment**

When checking compliance, reference the host data instead of the YAML rule file for these specific values:

```python
# In your audit function:
expected_asn = task.host['expected_asn']
actual_asn = bgp_data['vrf']['default']['local_as']
```

## 🧪 Testing

This project includes a test suite to verify the auditing logic using **Mock Data**. This ensures the script correctly identifies failures without needing to connect to a real lab environment.

To run the tests:

```bash
pytest -v
```

The tests are located in `tests/test_audit.py` and use fixtures from `tests/conftest.py` to simulate router output.

## 📂 Project Structure

```text
.
├── compliance_rules.yaml    # The "Gold Standard" definitions
├── config.yaml              # Nornir runner configuration
├── hosts.yaml               # Device Inventory
├── runner.py                # Main execution script
├── compliance.log           # Generated audit logs
├── requirements.txt         # Dependency list
└── tests/                   # Test suite
    ├── conftest.py          # Mock Genie data
    └── test_audit.py        # Unit tests
```
