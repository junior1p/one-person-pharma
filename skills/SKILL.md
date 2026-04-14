---
name: one-person-pharma
description: >
  Build a complete AI-powered protein design pipeline with cloud GPU compute
  (Modal) and automated wet-lab validation (Adaptyv Bio). Enables dry-wet
  closed-loop iteration for antibody/binder discovery at a fraction of
  traditional CRO costs (~$1.7K for 3 rounds). Use this skill when:
  (1) Designing a protein/antibody binder for a given target (PD-L1, EGFR, HER2,
  etc.), (2) Setting up an end-to-end computational-experimental workflow, 
  (3) Validating computational designs with real binding assays (Kd/kon/koff).
license: MIT
category: protein-design
tags: [protein-design, antibody, binder-design, modal, adaptyv, dry-wet-loop, ai-agent]
---

# One-Person AI Pharma

Build a complete AI-powered protein design pipeline combining cloud GPU compute
with automated wet-lab validation. This skill enables dry-wet closed-loop
iteration for protein/binder discovery at a fraction of traditional costs.

## When to Use

- Design a protein binder or VHH/nanobody for a target (PD-L1, EGFR, HER2, etc.)
- Set up an automated computational-experimental protein design workflow
- Validate computational designs with real binding assays (Kd, kon, koff)
- Iterate rapidly between AI design and experimental feedback

## Architecture Overview

```
[Target PDB] → [Modal · biomodals] → [Candidate Sequences]
                                              ↓
                        [Adaptyv Bio · Wet Lab]
                              ↓
              [Kd/kon/koff results] → [Next round design]
```

## Workflow

### Step 1: Install Dependencies

```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Register Modal, get $30/month free credit
# https://modal.com → Sign up → modal token
python -m modal setup

# Install Adaptyv SDK
pip install adaptyv-sdk
```

### Step 2: Clone biomodals

```bash
git clone https://github.com/hgbrian/biomodals
cd biomodals
```

### Step 3: Design with Modal (Dry Lab)

```bash
# Download target structure
wget https://files.rcsb.org/download/5JDS.pdb
grep "^ATOM.* A " 5JDS.pdb > 5JDS_chainA.pdb

# Run BindCraft on A100 GPU (~$3/run, ~1 hour)
GPU=A100 uvx modal run modal_bindcraft.py \
  --input-pdb 5JDS_chainA.pdb \
  --number-of-final-designs 5

# Score designs with Chai-1
uvx modal run modal_chai1.py --input-faa designs_complex.faa

# Score with AF2Rank
uvx modal run modal_af2rank.py \
  --input-pdb out/bindcraft/design_001.pdb
```

### Step 4: Submit to Adaptyv (Wet Lab)

```python
from adaptyv_sdk import AdaptyvClient
import os

client = AdaptyvClient(api_key=os.environ["ADAPTYV_API_KEY"])

# List available targets
targets = client.targets.list(search="EGFR", selfservice_only=True)
target_id = targets[0].id

# Create binding assay experiment
experiment = client.experiments.create(
    assay_type="binding",
    target_id=target_id,
    sequences=[
        {"name": "design_001", "sequence": "QVQLVESGG..."},
        {"name": "design_002", "sequence": "EVQLVESGG..."},
    ]
)
print(f"Experiment: {experiment.experiment_code}")
```

### Step 5: Retrieve Results

```python
import time

while True:
    status = client.experiments.get(experiment.id).status
    if status == "completed":
        results = client.results.list(experiment_id=experiment.id)
        for r in results:
            print(f"{r.sequence_name}: Kd={r.kd:.2e} M")
        break
    print(f"Status: {status}, checking in 1 hour...")
    time.sleep(3600)
```

### Step 6: Closed-Loop Iteration

Feed experimental results back into design:

```python
# Filter candidates by Kd threshold
KD_THRESHOLD = 1e-8  # 10 nM
hits = [r for r in results if r.kd and r.kd < KD_THRESHOLD]
print(f"Hits: {len(hits)}/{len(results)}")
```

## Tool Reference

### Dry Lab — biomodals on Modal

| Tool | Use | Cost |
|------|-----|------|
| `modal_bindcraft.py` | End-to-end binder design | ~$3/run |
| `modal_rfdiffusion.py` | Scaffold diffusion generation | ~$1/run |
| `modal_chai1.py` | Multi-chain complex prediction | varies |
| `modal_af2rank.py` | ipSAE/ipAE scoring | ~$0.5/run |
| `modal_alphafold.py` | Structure prediction | varies |
| `modal_boltz.py` | Open-source AF3-level | varies |

### Wet Lab — Adaptyv Bio

| Assay | Output | Cost |
|-------|--------|------|
| Binding (SPR/BLI) | Kd, kon, koff | ~$116/sequence |
| Expression | soluble/insoluble | included |

Available self-service targets: EGFR, HER2, PD-L1, IL-7Rα

## Cost Breakdown

| Stage | Cost | Time |
|-------|------|------|
| Dry (1 round, 5 designs) | ~$5 | ~2 hours |
| Wet (5 sequences) | ~$582 | 21 days |
| 3-round iteration total | ~$1,761 | ~9 weeks |

Modal free tier: $30/month (~6 dry rounds).

## Example Output

```json
{
  "sequence_name": "VHH-01",
  "target_name": "HER2 / ERBB2",
  "kd": 8.1e-10,
  "kd_units": "M",
  "kon": 2400000,
  "koff": 0.0019,
  "binding_strength": "strong",
  "r_squared": 0.999
}
```

## Error Handling

### Modal: GPU Quota Exceeded

```bash
# Check your Modal usage
modal token verify

# Reduce GPU tier or wait for quota reset
GPU=L40S uvx modal run modal_bindcraft.py ...
```

### Adaptyv: No Self-Service Target

```python
# Contact Adaptyv for custom target onboarding
# Non-selfservice targets require dedicated project
targets = client.targets.list(selfservice_only=False)
```

### Adaptyv: Experiment Failed

```python
# Check experiment status
exp = client.experiments.get(experiment_id)
print(exp.failure_reason)

# Resubmit failed sequences
failed = [s for s in exp.sequences if s.status == "failed"]
```

## See Also

- [biomodals GitHub](https://github.com/hgbrian/biomodals)
- [Boolean Biotech Blog](https://blog.booleanbiotech.com)
- [Adaptyv API Docs](https://docs.adaptyvbio.com)
- [Adaptyv AI Agents](https://agents.adaptyvbio.com)
