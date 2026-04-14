#!/usr/bin/env python3
"""
One-Person AI Pharma — Closed-Loop Binder Design Script

End-to-end workflow combining Modal cloud GPU (biomodals) with
Adaptyv Bio wet-lab validation for protein binder discovery.

Usage:
    python run_bindcraft.py --target PDB_ID --chain CHAIN [--rounds N] [--designs-per-round N]

Requirements:
    pip install adaptyv-sdk modal
    modal setup (with token)
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

TARGETS = {
    "EGFR": {"pdb": "1M17", "chain": "A", "adaptyv_id": "comp-egfr-human"},
    "HER2": {"pdb": "3 Alexis", "chain": "A", "adaptyv_id": "comp-her2-human"},
    "PD-L1": {"pdb": "5JDS", "chain": "A", "adaptyv_id": "comp-pdl1-human"},
    "IL-7Rα": {"pdb": "3PHX", "chain": "A", "adaptyv_id": "comp-il7ra-human"},
}


def run_modal_design(pdb_id: str, chain: str, n_designs: int = 5, output_dir: str = "designs"):
    """Run BindCraft design on Modal GPU."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    print(f"\n[Dry] Downloading target {pdb_id} chain {chain}...")
    subprocess.run(
        ["wget", "-q", f"https://files.rcsb.org/download/{pdb_id}.pdb"],
        check=True,
    )
    pdb_chain = f"{pdb_id}_chain{chain}.pdb"
    with open(f"{pdb_id}.pdb") as f:
        lines = [l for l in f if l.startswith("ATOM") and l[21] == chain]
    with open(pdb_chain, "w") as f:
        f.write("".join(lines))

    print(f"[Dry] Running BindCraft (A100 GPU, ~1h, ~$3)...")
    result = subprocess.run(
        [
            "uvx", "modal", "run", "modal_bindcraft.py",
            "--input-pdb", pdb_chain,
            "--number-of-final-designs", str(n_designs),
        ],
        env={**os.environ, "GPU": "A100"},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[Dry] BindCraft stderr: {result.stderr[-500:]}")
        raise RuntimeError(f"BindCraft failed: {result.stderr[-200:]}")
    print(f"[Dry] BindCraft complete. Output: {result.stdout[-300:]}")
    return result.stdout


def submit_to_adaptyv(sequences: list, target_id: str, api_key: str):
    """Submit designs to Adaptyv Bio for wet validation."""
    try:
        from adaptyv_sdk import AdaptyvClient
    except ImportError:
        print("[Wet] adaptyv-sdk not installed. Run: pip install adaptyv-sdk")
        return None

    client = AdaptyvClient(api_key=api_key)
    print(f"[Wet] Submitting {len(sequences)} sequences to Adaptyv...")
    experiment = client.experiments.create(
        assay_type="binding",
        target_id=target_id,
        sequences=sequences,
    )
    print(f"[Wet] Experiment created: {experiment.experiment_code}")
    print(f"[Wet] Estimated cost: ${experiment.total_cost_usd:.2f}")
    print(f"[Wet] ETA: {experiment.estimated_completion_date}")
    return experiment.id


def poll_adaptyv_results(experiment_id: str, api_key: str, poll_interval: int = 3600):
    """Poll Adaptyv until results are ready."""
    from adaptyv_sdk import AdaptyvClient
    client = AdaptyvClient(api_key=api_key)

    while True:
        exp = client.experiments.get(experiment_id)
        status = exp.status
        print(f"[Wet] Status: {status}")
        if status == "completed":
            results = client.results.list(experiment_id=experiment_id)
            return results
        elif status in ("failed", "cancelled"):
            raise RuntimeError(f"Experiment {status}: {getattr(exp, 'failure_reason', '')}")
        time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="One-Person AI Pharma — Closed-Loop Design")
    parser.add_argument("--target", required=True, choices=list(TARGETS.keys()),
                        help="Target protein")
    parser.add_argument("--chain", default="A", help="PDB chain ID")
    parser.add_argument("--rounds", type=int, default=3, help="Design iterations")
    parser.add_argument("--designs-per-round", type=int, default=5)
    parser.add_argument("--kd-threshold", type=float, default=1e-8,
                        help="Target Kd in M (default: 1e-8 = 10 nM)")
    args = parser.parse_args()

    api_key = os.environ.get("ADAPTYV_API_KEY")
    if not api_key:
        print("Error: Set ADAPTYV_API_KEY environment variable")
        print("Get your key at: https://foundry.adaptyvbio.com")
        sys.exit(1)

    target = TARGETS[args.target]
    best_kd = float("inf")
    best_seq = None

    for round_num in range(1, args.rounds + 1):
        print(f"\n{'='*60}")
        print(f"ROUND {round_num}/{args.rounds}")
        print(f"{'='*60}")

        # Dry: design
        run_modal_design(target["pdb"], args.chain, args.designs_per_round)

        # (In production: parse output/designs/*.pdb, extract sequences)
        print(f"[Round {round_num}] Parse designs/design_*.pdb for sequences")
        print("[Round {round_num}] Then call submit_to_adaptyv()")

        if best_kd < args.kd_threshold:
            print(f"\n[SUCCESS] Target Kd achieved: {best_kd:.2e} M")
            break

    print("\n[Done] Workflow complete. Set up webhook for async results.")


if __name__ == "__main__":
    main()
