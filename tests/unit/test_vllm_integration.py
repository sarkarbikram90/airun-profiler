"""Tests for deep vLLM reference integration and hardware telemetry profiler."""

from airun.integrations.vllm import (
    VLLMProfiler,
    VLLMRequestSpan,
)


def test_vllm_profiler_empty():
    profiler = VLLMProfiler(model="qwen-2.5-32b")
    diag = profiler.diagnose()
    assert diag.total_requests == 0
    assert diag.data_source == "EMPTY"


def test_vllm_profiler_detects_kv_cache_thrashing():
    profiler = VLLMProfiler(model="qwen-2.5-32b")

    for i in range(10):
        span = VLLMRequestSpan(
            request_id=f"req_{i}",
            model="qwen-2.5-32b",
            prompt_tokens=4000,
            output_tokens=150,
            queue_time_ms=50.0,
            prefill_time_ms=210.0,
            decode_time_ms=800.0,
            total_time_ms=1060.0,
            ttft_ms=260.0,
            tpot_ms=5.3,
            kv_blocks_allocated=260,
            gpu_cache_usage_pct=99.2,
            swapped_blocks=14,  # Triggers KV swap
            prefix_cache_hit=False,
            sm_active_pct=34.0,
            dram_active_pct=42.0,
            pcie_throughput_mb_s=14200.0,  # Saturated bus
            gpu_power_w=195.0,
        )
        profiler.record_request(span)

    diag = profiler.diagnose()
    assert diag.total_requests == 10
    assert "KV-Cache Thrashing" in diag.primary_bottleneck
    assert "swapped to host RAM" in diag.root_cause_explanation
    assert any("--enable-prefix-caching" in r for r in diag.recommended_parameters)
    assert any("--gpu-memory-utilization" in r for r in diag.recommended_parameters)


def test_vllm_profiler_detects_queue_saturation():
    profiler = VLLMProfiler(model="llama-3-70b")

    for i in range(10):
        span = VLLMRequestSpan(
            request_id=f"req_{i}",
            model="llama-3-70b",
            prompt_tokens=2000,
            output_tokens=200,
            queue_time_ms=450.0,  # High queue time
            prefill_time_ms=180.0,
            decode_time_ms=600.0,
            total_time_ms=1230.0,
            ttft_ms=630.0,
            tpot_ms=3.0,
            kv_blocks_allocated=140,
            gpu_cache_usage_pct=72.0,
            swapped_blocks=0,
            prefix_cache_hit=False,
            sm_active_pct=65.0,
            dram_active_pct=60.0,
            pcie_throughput_mb_s=1200.0,
            gpu_power_w=310.0,
        )
        profiler.record_request(span)

    diag = profiler.diagnose()
    assert "Scheduler Queue Saturation" in diag.primary_bottleneck
    assert any("--enable-chunked-prefill" in r for r in diag.recommended_parameters)


def test_vllm_profiler_detects_memory_bandwidth_bound():
    profiler = VLLMProfiler(model="deepseek-r1")

    for i in range(5):
        span = VLLMRequestSpan(
            request_id=f"req_{i}",
            model="deepseek-r1",
            prompt_tokens=500,
            output_tokens=800,
            queue_time_ms=20.0,
            prefill_time_ms=40.0,
            decode_time_ms=2400.0,
            total_time_ms=2460.0,
            ttft_ms=60.0,
            tpot_ms=3.0,
            kv_blocks_allocated=80,
            gpu_cache_usage_pct=50.0,
            swapped_blocks=0,
            prefix_cache_hit=True,
            sm_active_pct=42.0,
            dram_active_pct=88.0,  # High DRAM saturation during decode
            pcie_throughput_mb_s=800.0,
            gpu_power_w=280.0,
        )
        profiler.record_request(span)

    diag = profiler.diagnose()
    assert "Memory-Bandwidth Bound" in diag.primary_bottleneck
    assert any("FP8" in r or "quantization" in r for r in diag.recommended_parameters)
