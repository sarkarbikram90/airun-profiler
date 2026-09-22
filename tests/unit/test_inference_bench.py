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
