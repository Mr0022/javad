#!/usr/bin/env bash
# =============================================================================
# Optuna search for FiLM-TCN (ModernTCN + --use_events, channel fusion) with
# model selection and reporting done on the TEST split, over the benchmark's
# three horizons.
#
# *** The test metrics these studies report are selection-biased. ***
# Early stopping, the saved checkpoint, the pruner and the objective all read
# the 2024- test years, so the best trial's test score is the best of
# (n_trials x train_epochs) peeks at that sample: an oracle-tuning upper bound,
# not out-of-sample accuracy, and not comparable with the val-tuned numbers in
# the benchmark table. Every trial also stores val_* metrics for reference, and
# --select_on val reruns the same search space honestly. See the module
# docstring in tune_filmtcn.py.
#
# The fixed settings and the enqueued trial 0 are the tuned h=1 FiLM-TCN config
# (BASE_PARAMS in tune_filmtcn.py). Each study writes to
# optuna_results/filmtcn_testsel_EURUSD_pl<h>_mse/:
#   best_params.json  best_command.sh  all_trials.csv  study.db  *.html
# best_command.sh is the run.py invocation (--itr 5) for the winning config.
#
# The sqlite study resumes, so re-running an interrupted line picks up where it
# stopped. Pass --reset to start one over after editing the search space.
#
# Run from the repository root:
#     bash scripts/tune_filmtcn_test.sh
# In a notebook, prefix each block with '!' and run it as its own cell.
# =============================================================================
set -euo pipefail

PAIR=${PAIR:-EURUSD}
TRIALS=${TRIALS:-50}

for H in 1 5 10; do
  python tune_filmtcn.py \
    --select_on test --objective mse \
    --data custom --root_path ./data/ --data_path "${PAIR}_lnRV.csv" \
    --features S --target lnRV --enc_in 1 \
    --aggregate_mean --pred_len "$H" \
    --use_events --event_fusion channel \
    --lradj TST --pct_start 0.3 \
    --train_epochs 40 --patience 8 --num_workers 0 \
    --n_trials "$TRIALS" --n_seeds 1 --random_seed 2021
done
