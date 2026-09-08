# Invitation to External AI Engineers: Early Access & Feedback

**Subject**: Looking for 15-minute feedback on a lightweight local AI profiler (`airun`)

Hi [Name],

I noticed you're building [Agent / LLM System / AI Feature at Company].

We've built an open-source, local-first runtime profiler called **`airun`** designed to answer one straightforward question:
> **"What exactly happened during this AI workload, and what did it cost?"**

Unlike heavy cloud dashboards, `airun` runs 100% locally with zero configuration:
- Visual execution tree in your terminal (no web UI required on Day 1).
- Exact USD cost calculations per step, model, and tool call.
- Critical-path bottleneck detection (identifying the slowest sequential dependencies).
- Strict privacy: your prompts and completions never leave your machine; API keys are automatically redacted.

### What We're Asking:
1. Try running `airun demo` (zero API keys or setup required).
2. Add `@trace` to one of your non-sensitive agent scripts.
3. Run `airun report latest`.
4. Spend 10 minutes sharing what was confusing, what metrics were missing, and where your agents get unexpectedly slow or expensive.

If you're open to giving it a quick spin, here is the repo / install guide:
[Quickstart Guide](../docs/quickstart.md) • [GitHub Repository](https://github.com/sarkarbikram90/airun-tracing)

Thanks so much for your time,
[Your Name]
