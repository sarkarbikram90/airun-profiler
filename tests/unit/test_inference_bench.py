"""Tests for Inference Engine Benchmarking Suite."""

from airun.benchmarks.inference import (
    run_inference_benchmark,
)


def test_run_inference_benchmark_default():
    suite = run_inference_benchmark(model="qwen3-8b", gpu="l4")

    assert suite.model == "qwen3-8b"
    assert suite.gpu == "l4"
    assert "vLLM" in suite.results_by_engine
    assert "SGLang" in suite.results_by_engine

    vllm = suite.results_by_engine["vLLM"]
    sglang = suite.results_by_engine["SGLang"]

    assert vllm.ttft_p50_ms > 0
    assert vllm.throughput_tokens_sec > 0
    assert sglang.throughput_tokens_sec > 0
    assert suite.winner_throughput in ("vLLM", "SGLang")
    assert suite.winner_cost in ("vLLM", "SGLang")


def test_run_inference_benchmark_all_engines():
    suite = run_inference_benchmark(
        model="llama3-70b",
        engines=["vllm", "sglang", "tensorrt-llm"],
        gpu="h100",
        concurrency=[1, 16, 64],
    )

    assert len(suite.results_by_engine) == 3
    assert "TensorRT-LLM" in suite.results_by_engine
    trt = suite.results_by_engine["TensorRT-LLM"]
    assert trt.throughput_tokens_sec >= 1000.0
    assert suite.concurrency == [1, 16, 64]


def test_inference_benchmark_markdown_and_dict():
    suite = run_inference_benchmark(model="deepseek-r1-qwen-32b", gpu="a100")
    md = suite.to_markdown()

    assert "| Metric |" in md
    assert "TTFT p50" in md
    assert "Throughput" in md
    assert "Cost / 1M Tokens" in md
    assert "AIRUN BENCHMARK: DEEPSEEK-R1-QWEN-32B (A100)" in md

    d = suite.to_dict()
    assert d["model"] == "deepseek-r1-qwen-32b"
    assert d["gpu"] == "a100"
    assert "results" in d
    assert "winner_throughput" in d
    assert "winner_cost" in d
    assert "vLLM" in d["results"]
    assert "ttft_p95_ms" in d["results"]["vLLM"]
    assert "sample_count" in d["results"]["vLLM"]


def test_run_benchmark_from_config_file(tmp_path):
    from airun.benchmarks.inference import run_benchmark_from_config

    config_yaml = """
schema_version: "1.0"
benchmark_name: "test-serving-suite"
environment:
  accelerator: "l4"
workload:
  model: "qwen3-8b"
  concurrency_levels: [1, 8]
engines:
  - name: "vllm"
  - name: "sglang"
gate_thresholds:
  max_ttft_p95_ms: 180.0
  min_throughput_tokens_sec: 800.0
"""
    cfg_file = tmp_path / "bench.yaml"
    cfg_file.write_text(config_yaml, encoding="utf-8")

    suite = run_benchmark_from_config(cfg_file)
    assert suite.benchmark_name == "test-serving-suite"
    assert suite.overall_gate_status == "PASS"
    assert suite.results_by_engine["vLLM"].gate_status == "PASS"
    assert suite.results_by_engine["SGLang"].gate_status == "PASS"


def test_run_benchmark_from_config_gate_failure(tmp_path):
    from airun.benchmarks.inference import run_benchmark_from_config

    config_yaml = """
schema_version: "1.0"
benchmark_name: "strict-gate-suite"
environment:
  accelerator: "l4"
workload:
  model: "qwen3-8b"
engines:
  - name: "sglang"
gate_thresholds:
  max_ttft_p95_ms: 150.0  # SGLang p95 is ~172.4ms, must fail
"""
    cfg_file = tmp_path / "strict.yaml"
    cfg_file.write_text(config_yaml, encoding="utf-8")

    suite = run_benchmark_from_config(cfg_file)
    assert suite.overall_gate_status == "FAIL"
    sglang = suite.results_by_engine["SGLang"]
    assert sglang.gate_status == "FAIL"
    assert any("150.0ms" in f for f in sglang.gate_failures)

