# one-person-pharma

**One-Person AI Pharma** — Build a complete AI-powered protein design pipeline
with cloud GPU compute (Modal + biomodals) and automated wet-lab validation
(Adaptyv Bio). Enable dry-wet closed-loop iteration for binder/antibody discovery.

## Quick Start

```bash
# 1. Install
curl -LsSf https://astral.sh/uv/install.sh | sh
python -m modal setup   # get token at modal.com
pip install adaptyv-sdk

# 2. Clone biomodals
git clone https://github.com/hgbrian/biomodals
cd biomodals

# 3. Design a binder (~$3, ~1 hour on A100)
wget https://files.rcsb.org/download/5JDS.pdb
GPU=A100 uvx modal run modal_bindcraft.py \
  --input-pdb 5JDS.pdb --number-of-final-designs 5

# 4. Submit to Adaptyv wet lab
#    Sign up at foundry.adaptyvbio.com → get API key
export ADAPTYV_API_KEY=your_key_here
python -m adaptyv_sdk.experiments create \
  --assay-type binding --target-id comp-pdl1-human \
  --sequences-file designs.fasta
```

## Architecture

```
[Target PDB] → [Modal · biomodals] → [Candidate Sequences]
                   ↓ GPU ($3/run)          ↓
              [Adaptyv Bio · Wet Lab]     Kd/kon/koff
                         ↓
              [Feedback → Next Round]
```

## Cost

| Stage | Cost | Time |
|-------|------|------|
| Dry (5 designs) | ~$5 | ~2 hours |
| Wet (5 seqs) | ~$582 | 21 days |
| 3-round total | ~$1,761 | ~9 weeks |

Modal free tier: **$30/month** (~6 dry rounds free).

## Links

- Skill: [skills/one-person-pharma/SKILL.md](skills/one-person-pharma/SKILL.md)
- biomodals: https://github.com/hgbrian/biomodals
- Adaptyv API: https://docs.adaptyvbio.com
- clawRxiv: https://clawrxiv.io/abs/2604.XXXXX
