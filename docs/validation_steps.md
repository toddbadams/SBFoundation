Here’s the same end‑to‑end workflow, updated for a Python + Parquet setup:

**Problem**
Every night you land fresh Parquet tables into your “acquisition” folder. You need to pick up only the new rows, validate & clean them column‑by‑column, write the good ones out to a “validated” folder, dump the bad ones (with error info) to an “exceptions” folder, and keep a master log of what’s been processed so you never touch the same row twice.

> **Tip for operators:** the `poetry run validate` CLI accepts `--acq-date YYYY-MM-DD` to target a specific acquisition run. If omitted, it automatically selects the most recent date folder under the acquisition directory.

---

## 1. Define & store your rules

Keep a simple JSON (or YAML) file alongside your code, e.g. `validation_rules.json`:

```json
{
  "my_table": {
    "id":       {"type":"int"},
    "email":    {"type":"string", "regex":"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"},
    "amount":   {"type":"float",  "min":0.0},
    "signup":   {"type":"date",   "format":"%Y-%m-%d"}
  },
  "other_table": {
    …  
  }
}
```

This decouples logic from code—tweaking a rule is just editing JSON.

---

## 2. Maintain a “status” table of processed rows

Since you’re on Parquet, you can choose:

* **SQLite** (single‑file DB)—easy to query from Python
* **Parquet manifest** (a single Parquet file you append to each run)

For example, a Parquet manifest schema:

```python
# columns: table, pk_value, status, last_checked, error_msg
status_df = pd.DataFrame([], columns=[
    "table", "pk", "status", "last_checked", "error"
])
status_df.to_parquet("manifests/validation_status.parquet", index=False)
```

---

## 3. Skeleton of your Python ETL driver

```python
import pandas as pd
import json
from datetime import datetime
import os

# Load rules & status manifest
with open("validation_rules.json") as f:
    rules = json.load(f)
status = pd.read_parquet("manifests/validation_status.parquet")

def validate_row(row, table_rules):
    """Returns (is_valid, cleaned_row, error_msg)."""
    errors = []
    cleaned = {}
    for col, rule in table_rules.items():
        val = row.get(col)
        # 1) Type check
        if rule["type"] == "int":
            try:    v = int(val)
            except: errors.append(f"{col} not int")
        elif rule["type"] == "float":
            try:    v = float(val)
            except: errors.append(f"{col} not float")
        elif rule["type"] == "date":
            try:    v = datetime.strptime(val, rule["format"])
            except: errors.append(f"{col} bad date")
        else:
            v = val
        # 2) Regex / bounds
        if "regex" in rule:
            import re
            if not re.match(rule["regex"], str(val)):
                errors.append(f"{col} regex fail")
        if "min" in rule and v < rule["min"]:
            errors.append(f"{col}<min")
        if "max" in rule and v > rule["max"]:
            errors.append(f"{col}>max")
        cleaned[col] = v
    if errors:
        return False, None, "; ".join(errors)
    return True, cleaned, None

def process_table(table_name):
    table_rules = rules[table_name]
    # 1) Read acquisition parquet
    df = pd.read_parquet(f"acquisition/{table_name}.parquet")
    # 2) Identify new rows by primary key (e.g. 'id')
    processed_pks = set(status[status.table==table_name].pk)
    new_df = df[~df.id.isin(processed_pks)]
    if new_df.empty:
        print(f"No new rows for {table_name}")
        return

    valids, bads, updates = [], [], []
    for _, row in new_df.iterrows():
        ok, clean, err = validate_row(row.to_dict(), table_rules)
        if ok:
            valids.append(clean)
            updates.append({
                "table":table_name, "pk":row.id,
                "status":"SUCCESS", "last_checked":datetime.now(),
                "error":None
            })
        else:
            bad = row.to_dict()
            bad["error_msg"] = err
            bads.append(bad)
            updates.append({
                "table":table_name, "pk":row.id,
                "status":"FAILED", "last_checked":datetime.now(),
                "error": err
            })

    # 3) Write successes & failures
    pd.DataFrame(valids).to_parquet(
        f"validated/{table_name}.parquet", 
        index=False, append=True
    )
    pd.DataFrame(bads).to_parquet(
        f"exceptions/{table_name}.parquet", 
        index=False, append=True
    )

    # 4) Update manifest
    global status
    status = pd.concat([status, pd.DataFrame(updates)], ignore_index=True)
    status.to_parquet("manifests/validation_status.parquet", index=False)
    print(f"{table_name}: {len(valids)} OK, {len(bads)} FAILED")

# Main runner
for tbl in rules:
    process_table(tbl)
```

---

## 4. Atomicity & idempotence

* **Atomic writes**: write to a staging file then `os.replace()` into place, so you never end up with half‑written Parquets.
* **Idempotent runs**: the manifest check (`.isin(processed_pks)`) ensures re‑running won’t double‑process.

---

## 5. Scheduling

Crontab (or your orchestration tool) entry right after the nightly AP Ion job:

```
# 3:15 AM daily
15 3 * * * /usr/bin/python /opt/etl/validate_and_clean.py >> /var/log/etl/validate.log 2>&1
```

If you’re on Airflow, make this Python job a downstream `PythonOperator` with a dependency on the load task.

---

## 6. Monitoring & evolution

* **Dashboard**: spin up a quick Jupyter or Streamlit to chart daily pass/fail counts (read from `manifests/validation_status.parquet`).
* **Rule updates**: tweak your JSON → push → next run picks it up.
* **Notifications**: add an email or Slack alert when failures exceed a threshold.

---

That pattern will let you:

1. Only touch new rows
2. Enforce column‑level rules
3. Keep a “clean” Parquet zone and an “exceptions” zone
4. Log every decision for audit and retryability

Feel free to ask if you want more detail on any of the pieces (e.g. setting up atomic Parquet writes or building the monitoring dashboard)!
