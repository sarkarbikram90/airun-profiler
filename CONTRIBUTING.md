# Contributing to `airun`

Thank you for your interest in contributing to `airun`!

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sarkarbikram90/airun-profiler.git
   cd airun-profiler
   ```

2. **Python SDK & CLI Setup**:
   ```bash
   pip install -e ".[dev,otel]"
   pytest -v
   ruff check src tests examples
   ruff format src tests examples
   ```

3. **Rust Data Plane Collector (`crates/airun-collector`)**:
   ```bash
   cargo test --manifest-path crates/airun-collector/Cargo.toml
   cargo build --manifest-path crates/airun-collector/Cargo.toml
   ```

4. **TypeScript Control Plane (`packages/control-plane`)**:
   ```bash
   cd packages/control-plane
   npm install
   npm run build
   cd ../..
   ```

## Pull Request Guidelines

- Ensure all Python unit/integration tests (110 tests), Rust collector tests (10 tests), and TypeScript tests (7 tests) pass before opening a PR.
- Preserve the **Zero-Crash Guarantee** on SDK entry points: profiling errors must never fail host workloads.
- Maintain **Privacy-by-Default**: never capture raw prompt/completion text without explicit user configuration, and auto-redact secrets.
