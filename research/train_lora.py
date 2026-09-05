"""Tinker LoRA SFT for tieout (Role B).

Trains Qwen/Qwen3.8-27B on the SFT set produced by sample_data.py.
Expected to run after `research/data/sft/sft_train.jsonl` exists.

Usage (from research/):
    .venv/bin/python train_lora.py \
        --sft data/sft/sft_train.jsonl \
        --log data/sft/log \
        --model Qwen/Qwen3.8-27B \
        --lora-rank 32 \
        --batch-size 1 \
        --max-length 32768 \
        --max-steps 300 \
        --lr 1e-4
"""

import argparse
import json
import os
import random
import time
from pathlib import Path

import tinker
from tinker_cookbook import model_info, renderers
from tinker_cookbook.checkpoint_utils import save_checkpoint
from tinker_cookbook.supervised.common import compute_bpb, compute_mean_nll
from tinker_cookbook.supervised.data import conversation_to_datum
from tinker_cookbook.tokenizer_utils import get_tokenizer
from tinker_cookbook.utils.git_rev import recipe_user_metadata
from tinker_cookbook.utils.ml_log import setup_logging


def _load_env() -> None:
    root = Path(__file__).resolve().parent.parent
    for env_path in (root / ".env", root / "research" / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k, v)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--sft", default="data/sft/sft_train.jsonl")
    p.add_argument("--log", default="data/sft/log")
    p.add_argument("--model", default="Qwen/Qwen3.8-27B")
    p.add_argument("--lora-rank", type=int, default=32)
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--max-length", type=int, default=32768)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--max-steps", type=int, default=300)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--save-every", type=int, default=50)
    return p.parse_args()


def load_sft_records(path: Path) -> list[dict]:
    records = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def record_to_conversation(r: dict) -> list[dict]:
    """Turn a verified SFT record into a chat-style conversation."""
    return [
        {"role": "system", "content": r.get("system", "")},
        {"role": "user", "content": r.get("prompt", "")},
        {"role": "assistant", "content": r.get("completion", "")},
    ]


def main() -> None:
    _load_env()
    args = parse_args()

    sft_path = Path(args.sft)
    if not sft_path.exists():
        raise FileNotFoundError(f"SFT file not found: {sft_path}")

    records = load_sft_records(sft_path)
    if len(records) < 200:
        print(f"WARNING: only {len(records)} verified trajectories; training may not help. Waiting? Exiting.")
        raise SystemExit(1)

    # Shuffle deterministically; cap to max_steps batches
    random.seed(args.seed)
    random.shuffle(records)
    n_batches = min(len(records), args.max_steps)
    records = records[:n_batches]
    print(f"Training on {n_batches} records (batch size {args.batch_size})", flush=True)

    # Tinker setup
    tokenizer = get_tokenizer(args.model)
    renderer_name = model_info.get_recommended_renderer_name(args.model)
    renderer = renderers.get_renderer(renderer_name, tokenizer)
    print(f"Using renderer: {renderer_name}", flush=True)

    log_path = Path(args.log)
    log_path.mkdir(parents=True, exist_ok=True)
    ml_logger = setup_logging(
        log_dir=str(log_path),
        config=vars(args),
    )

    service_client = tinker.ServiceClient(
        project_id=os.environ.get("TINKER_PROJECT_ID") or None,
        user_metadata=recipe_user_metadata("tieout_sft_v1"),
    )

    training_client = service_client.create_lora_training_client(
        base_model=args.model,
        rank=args.lora_rank,
        seed=args.seed,
        user_metadata={
            "recipe": "tieout_sft_v1",
            "sft_file": str(sft_path),
            "n_records": str(len(records)),
        },
    )

    train_on = renderers.TrainOnWhat.ALL_ASSISTANT_MESSAGES
    n_train_batches = n_batches // args.batch_size

    for batch_idx in range(n_train_batches):
        start = batch_idx * args.batch_size
        end = start + args.batch_size
        batch_records = records[start:end]

        # Save periodic checkpoint
        if args.save_every > 0 and batch_idx % args.save_every == 0 and batch_idx > 0:
            save_checkpoint(
                training_client=training_client,
                name=f"{batch_idx:06d}",
                log_path=str(log_path),
                kind="state",
                loop_state={"batch": batch_idx},
                ttl_seconds=604800,
            )

        # Linear LR schedule
        lr_mult = max(0.0, 1.0 - batch_idx / n_train_batches)
        current_lr = args.lr * lr_mult
        adam_params = tinker.AdamParams(
            learning_rate=current_lr,
            beta1=0.9,
            beta2=0.95,
            eps=1e-8,
        )

        batch = [
            conversation_to_datum(
                record_to_conversation(r),
                renderer,
                args.max_length,
                train_on,
            )
            for r in batch_records
        ]

        fwd_bwd_future = training_client.forward_backward(batch, loss_fn="cross_entropy")
        optim_future = training_client.optim_step(adam_params)

        fwd_bwd = fwd_bwd_future.result()
        optim = optim_future.result()

        # Log metrics
        logprobs = [x["logprobs"] for x in fwd_bwd.loss_fn_outputs]
        weights = [d.loss_fn_inputs["weights"] for d in batch]
        target_tokens = [d.loss_fn_inputs["target_tokens"] for d in batch]
        nll = compute_mean_nll(logprobs, weights)
        bpb = compute_bpb(logprobs, weights, target_tokens, tokenizer)

        metrics = {
            "step": batch_idx,
            "learning_rate": current_lr,
            "train_mean_nll": nll,
            "train_mean_bpb": bpb,
            "num_tokens": sum(d.model_input.length for d in batch),
            "progress": batch_idx / n_train_batches,
            "time": time.time(),
        }
        ml_logger.log_metrics(metrics=metrics, step=batch_idx)
        print(f"step {batch_idx}/{n_train_batches}  nll={nll:.4f}  bpb={bpb:.4f}  lr={current_lr:.2e}", flush=True)

    # Final checkpoint — export both state and sampler weights
    final = save_checkpoint(
        training_client=training_client,
        name="final",
        log_path=str(log_path),
        kind="both",
        loop_state={"batch": n_train_batches},
        ttl_seconds=None,
    )
    print(f"Final checkpoint saved: {final}", flush=True)
    ml_logger.close()


if __name__ == "__main__":
    main()
