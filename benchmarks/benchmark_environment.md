# Benchmark Environment & Hardware Specifications

This document describes the execution environment and hardware configuration under which the official `airun` benchmarks were captured.

---

## Reference Host Environment

| Parameter | Specification |
| :--- | :--- |
| **Processor** | Intel64 Family 6 Model 189 Stepping 1, GenuineIntel (x86_64) |
| **Logical Cores** | 16 Cores |
| **Operating System** | Windows 11 Pro 64-bit (Build 26100) / Linux Kernel 6.8+ validated |
| **Python Runtime** | CPython 3.14.7 (also validated against Python 3.11, 3.12, and 3.13) |
| **Compiler / Toolchain** | MSVC / GCC 13.2 / Rust 1.84+ (for `airun-collector`) |
| **Timer Mechanism** | `time.perf_counter_ns()` backed by high-precision hardware TSC |
| **Disk Subsystem** | NVMe PCIe 4.0 SSD (NTFS with WAL journal mode) |

---

## Storage Engine Configuration

The SQLite benchmarks execute against the default production configuration instantiated by `SQLiteTraceStore`:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
```

- **WAL Mode**: Write-Ahead Logging allows concurrent readers while a single writer appends to the log without locking the database file.
- **Synchronous = NORMAL**: Balances crash-safety with disk I/O performance by syncing WAL checkpoints rather than every single write transaction.

---

## Reproducing in CI / Linux Cloud Environments

To reproduce these benchmarks on an AWS EC2 instance (e.g., `c6i.2xlarge`) or GCP Compute Engine (`c2-standard-8`):

```bash
# Clone the repository
git clone https://github.com/sarkarbikram90/airun-profiler.git
cd airun-profiler

# Create a clean virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Run the full benchmark suite
python benchmarks/trace_overhead.py
python benchmarks/critical_path.py
python benchmarks/sqlite_persistence.py
```

Results are saved to `benchmarks/results/` as JSON objects for programmatic ingestion into automated regression tracking or dashboard visualizers.
