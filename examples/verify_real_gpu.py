"""Real GPU Verification Script for airun-profiler.

Run this script on any physical machine with an NVIDIA GPU attached (e.g. H100, A100, L40S, RTX 4090)
to verify hardware discovery, live telemetry scraping, and Time-Window correlation.

Usage:
    python examples/verify_real_gpu.py
"""

from __future__ import annotations

import shutil
import subprocess
import time
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from airun import SpanKind, set_span_metadata, trace
from airun.analysis.correlation import PhysicalTelemetrySample, TimeWindowCorrelator
from airun.cli.formatting import render_hardware_bleed_panel
from airun.store import get_trace_store

console = Console()


def query_nvidia_smi() -> dict[str, Any] | None:
    """Query live physical GPU hardware info via nvidia-smi."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return None
    try:
        cmd = [
            smi,
            "--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode != 0 or not res.stdout.strip():
            return None
        lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
        if not lines:
            return None
        parts = [col.strip() for col in lines[0].split(",")]
        return {
            "name": parts[0],
            "driver": parts[1],
            "memory_total_mb": float(parts[2]),
            "memory_used_mb": float(parts[3]),
            "utilization_pct": float(parts[4]),
            "temperature_c": float(parts[5]),
            "power_w": float(parts[6]),
            "gpu_count": len(lines),
        }
    except Exception:
        return None


def run_gpu_compute_benchmark():
    """Run real GPU tensor operations if PyTorch CUDA is present, or simulate if CPU."""
    gpu_available = False
    torch_available = False

    try:
        import torch
        torch_available = True
        gpu_available = torch.cuda.is_available()
    except ImportError:
        pass

    if torch_available and gpu_available:
        import torch
        console.print(f"[bold green][OK] PyTorch CUDA Active:[/] {torch.cuda.get_device_name(0)}")
        console.print(f"     Allocated: {torch.cuda.memory_allocated() / 1e6:.1f} MB | Reserved: {torch.cuda.memory_reserved() / 1e6:.1f} MB\n")

        # Execute live GEMM workload on GPU inside airun trace
        with trace("physical_gpu_matrix_multiplication", kind=SpanKind.WORKFLOW) as root:
            set_span_metadata({"device": "cuda:0", "tensor_dim": "8192x8192"})
            with trace("tensor_allocation_and_warmup", kind=SpanKind.AGENT_STEP):
                a = torch.randn(8192, 8192, device="cuda", dtype=torch.float16)
                b = torch.randn(8192, 8192, device="cuda", dtype=torch.float16)
                torch.cuda.synchronize()

            with trace("fp16_gemm_forward_pass", kind=SpanKind.AGENT_STEP):
                c = torch.matmul(a, b)
                torch.cuda.synchronize()
                del a, b, c
                torch.cuda.empty_cache()

        trace_id = root.trace_id
    else:
        # Fallback demonstration trace
        if not torch_available:
            console.print("[dim yellow][!] PyTorch not installed in current Python env. Generating standard trace...[/dim yellow]")
        elif not gpu_available:
            console.print("[dim yellow][!] No CUDA device detected by PyTorch. Generating standard trace...[/dim yellow]")

        with trace("simulated_gpu_compute_workload", kind=SpanKind.WORKFLOW) as root:
            with trace("simulated_gemm_step", kind=SpanKind.AGENT_STEP):
                time.sleep(0.1)
        trace_id = root.trace_id

    return trace_id


def main():
    console.print("\n[bold cyan]====================================================================[/bold cyan]")
    console.print("[bold cyan]       Airun Real GPU Hardware Verification & Profiling Benchmark   [/bold cyan]")
    console.print("[bold cyan]====================================================================[/bold cyan]\n")

    # Step 1: Physical GPU Discovery
    hw = query_nvidia_smi()
    if hw:
        grid = Table.grid(padding=(0, 2))
        grid.add_column("Property", style="bold white")
        grid.add_column("Value", style="cyan")
        grid.add_row("Detected Accelerator", f"[bold green]{hw['name']}[/bold green] (x{hw['gpu_count']} GPUs)")
        grid.add_row("NVIDIA Driver Version", hw['driver'])
        grid.add_row("VRAM Total", f"{hw['memory_total_mb'] / 1024:.1f} GB")
        grid.add_row("VRAM Currently Used", f"{hw['memory_used_mb'] / 1024:.1f} GB")
        grid.add_row("Current SM Utilization", f"{hw['utilization_pct']:.1f}%")
        grid.add_row("Current Temperature", f"{hw['temperature_c']:.1f} C")
        grid.add_row("Current Power Draw", f"{hw['power_w']:.1f} Watts")

        console.print(Panel(grid, title="[bold green][OK] Physical Silicon Hardware Detected[/bold green]", border_style="green", expand=False))
    else:
        console.print(Panel(
            "[yellow]No physical NVIDIA GPU detected via nvidia-smi CLI.[/yellow]\n"
            "If running in Docker/K8s, ensure NVIDIA Container Toolkit is enabled with --gpus all.\n"
            "Testing will proceed in emulated architectural fallback mode.",
            title="[yellow]Hardware Status: Emulated Fallback[/yellow]",
            border_style="yellow",
            expand=False,
        ))

    console.print("\n[bold]Step 1: Running Workload with airun Tracing...[/bold]")
    trace_id = run_gpu_compute_benchmark()
    console.print(f"[green][OK][/green] Captured trace ID: [bold]{trace_id}[/bold]")

    # Step 2: Correlate with Hardware Telemetry
    console.print("\n[bold]Step 2: Correlating Trace with Physical Silicon Telemetry...[/bold]")
    store = get_trace_store()
    record = store.get_trace(trace_id)

    if record:
        # Pull live sample if available or construct sample from query
        sm_pct = hw["utilization_pct"] if hw else 78.5
        temp = hw["temperature_c"] if hw else 62.0
        pwr = hw["power_w"] if hw else 450.0

        sample = PhysicalTelemetrySample(
            timestamp=time.time(),
            gpu_id=0,
            sm_util_pct=sm_pct,
            temperature_c=temp,
            power_watts=pwr,
            memory_used_mb=hw["memory_used_mb"] if hw else 40960.0,
            memory_total_mb=hw["memory_total_mb"] if hw else 81920.0,
        )

        accelerator_name = "h100" if (hw and "h100" in hw["name"].lower()) else ("a100" if (hw and "a100" in hw["name"].lower()) else "h100")
        correlator = TimeWindowCorrelator(accelerator=accelerator_name, num_gpus=hw["gpu_count"] if hw else 8)
        diagnosis = correlator.diagnose_trace(record, telemetry=[sample])

        console.print("\n", render_hardware_bleed_panel(diagnosis), "\n")

    console.print("[bold cyan]====================================================================[/bold cyan]")
    console.print("[bold green]Verification Complete![/bold green] You can also test on this machine using:")
    console.print("  * Hardware CI Test Suite: [cyan]pytest tests/hardware/test_silicon_hardware.py -v -s[/cyan]")
    console.print("  * Hardware Waste CLI:    [cyan]airun waste latest --hardware[/cyan]")
    console.print("  * Golden Signals:         [cyan]airun golden-signals latest[/cyan]")
    console.print("  * Real-Time UI:           [cyan]airun ui[/cyan]")
    console.print("[bold cyan]====================================================================[/bold cyan]\n")


if __name__ == "__main__":
    main()
