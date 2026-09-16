#!/usr/bin/env bash
# =============================================================================
# EventTCN = ModernTCN + news-event conditioning (--use_events, channel fusion)
# Hyper-parameters are the best Optuna trials from:
#   tuningresults/EVENTTCN1/best_params.json    (h = 1  day)
#   tuningresults/EVENTTCN5/best_params.json    (h = 5  days)
#   tuningresults/EVENTTCN22/best_params.json   (h = 22 days)
#
# Events were tuned with --event_fusion channel (tune.py default) and event_dim
# in {4,8,16}; event_past/event_future stay on (defaults). --use_events auto-
# switches --data custom -> custom_events and reads the calendar paired with
# --data_path by name: EURUSD_lnRV.csv -> data/EURUSD_EVENTS.csv, and likewise
# AUDUSD_lnRV.csv -> AUDUSD_EVENTS.csv, so switching currency pair needs no other
# change. Those files are the raw long-format calendar (Date,Name,Impact,Currency);
# data_provider/event_preprocessing.py turns one into daily features aligned to that
# pair's trading calendar (117 columns for EURUSD); tune --event_min_days /
# --event_min_impact to resize it, or --event_data_path to override the pairing.
# NOTE: these hyper-parameters were tuned on realized_volatility.csv + events.csv, so
# re-tune before reading the numbers as final -- and re-tune per currency pair.
#
# NOTE on patch_stride: tune.py clamps stride = min(patch_stride, patch_size).
# For h = 22 the JSON stores patch_stride 8 but patch_size 4, so the value that
# actually trained is 4 — that clamped value is used below.
#
# Run from the ModernTCN-Long-term-forecasting/ directory:
#     bash scripts/eventtcn.sh
# In a notebook, prefix each block with '!' and run it as its own cell.
# =============================================================================
set -euo pipefail

# ---- h = 1  (EVENTTCN1, event_dim 16) ---------------------------------------
python run.py --is_training 1 --model_id EventTCN_h1 --model ModernTCN \
  --data custom --root_path ./data/ --data_path EURUSD_lnRV.csv \
  --features S --target ln_RV --enc_in 1 --dec_in 1 --c_out 1 \
  --aggregate_mean --seq_len 22 --pred_len 1 \
  --patch_size 32 --patch_stride 8 --ffn_ratio 3 \
  --num_blocks 3 3 3 3 --large_size 51 51 51 51 --small_size 3 3 3 3 \
  --dims 32 32 32 32 --dw_dims 32 32 32 32 \
  --dropout 0.41549663977882045 --head_dropout 0.2993197807081734 --revin 1 \
  --use_multi_scale False --lradj TST --pct_start 0.3 \
  --learning_rate 0.0055036472222018224 --batch_size 128 \
  --train_epochs 40 --patience 8 --num_workers 2 --itr 5 \
  --use_events --event_dim 16 --event_fusion channel

# ---- h = 5  (EVENTTCN5, event_dim 4) ----------------------------------------
python run.py --is_training 1 --model_id EventTCN_h5 --model ModernTCN \
  --data custom --root_path ./data/ --data_path EURUSD_lnRV.csv \
  --features S --target ln_RV --enc_in 1 --dec_in 1 --c_out 1 \
  --aggregate_mean --seq_len 35 --pred_len 5 \
  --patch_size 32 --patch_stride 2 --ffn_ratio 3 \
  --num_blocks 3 3 3 3 --large_size 13 13 13 13 --small_size 5 5 5 5 \
  --dims 32 32 32 32 --dw_dims 32 32 32 32 \
  --dropout 0.0750931679204987 --head_dropout 0.36903420636104134 --revin 1 \
  --use_multi_scale False --lradj TST --pct_start 0.3 \
  --learning_rate 0.004311298509350653 --batch_size 128 \
  --train_epochs 40 --patience 8 --num_workers 2 --itr 5 \
  --use_events --event_dim 4 --event_fusion channel

# ---- h = 22 (EVENTTCN22, event_dim 8; patch_stride clamped 8 -> 4) ----------
python run.py --is_training 1 --model_id EventTCN_h22 --model ModernTCN \
  --data custom --root_path ./data/ --data_path EURUSD_lnRV.csv \
  --features S --target ln_RV --enc_in 1 --dec_in 1 --c_out 1 \
  --aggregate_mean --seq_len 35 --pred_len 22 \
  --patch_size 4 --patch_stride 4 --ffn_ratio 2 \
  --num_blocks 1 1 1 1 --large_size 31 31 31 31 --small_size 5 5 5 5 \
  --dims 32 32 32 32 --dw_dims 32 32 32 32 \
  --dropout 0.2332348360983411 --head_dropout 0.32275773648706885 --revin 1 \
  --use_multi_scale False --lradj TST --pct_start 0.3 \
  --learning_rate 0.0077943332090161695 --batch_size 256 \
  --train_epochs 40 --patience 8 --num_workers 2 --itr 5 \
  --use_events --event_dim 8 --event_fusion channel

# =============================================================================
# FINAL REFIT ON TRAIN + VALIDATION (--refit_trainval)
# -----------------------------------------------------------------------------
# Same two-step protocol as scripts/moderntcn.sh, which documents it in full.
# In short: the runs above fit 2010-2021 and early-stop on 2022-2023, while the
# HAR-RV benchmark is estimated on 2010-2023, so the network is short exactly the
# two years closest to the test window. --refit_trainval refits the tuned model on
# 2010-2023 to put both on the same information set.
#
# The event features follow the target series: the count columns (n_events*,
# event_score) are standardised over the fitting years, so they too are computed
# on 2010-2023 under --refit_trainval; the evt_* indicators stay raw 0/1.
#
# Step 1: run the command above, read "best_epoch": N from
#         checkpoints/<setting>/train_meta.json (also printed at end of training).
# Step 2: rerun the same command with --refit_trainval and --train_epochs N, e.g.
#         for h = 1 if the train-only run reported best epoch 21:
#
#   python run.py --is_training 1 --model_id EventTCN_h1 --model ModernTCN \
#     --data custom --root_path ./data/ --data_path EURUSD_lnRV.csv \
#     --features S --target ln_RV --enc_in 1 --dec_in 1 --c_out 1 \
#     --aggregate_mean --seq_len 70 --pred_len 1 \
#     ... (every other flag byte-identical to the tuned command above) ... \
#     --num_workers 2 --itr 5 \
#     --use_events --event_dim 4 --event_fusion channel \
#     --refit_trainval --train_epochs 21
#
# Refit runs get a '_refit' suffix in the setting string, so they land in their own
# checkpoints/, results/ and test_results/ directories. Fix the protocol before
# reading the test metrics -- choosing the better of the two afterwards would make
# 2024-2025 a selection set.
# =============================================================================
