#!/usr/bin/env bash
set -euo pipefail

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate wm

model_name="/home/raoxiaoyang/llm_models/codet5-base"
runner="Defect_Detection/CodeT5/run.py"

train_codet5() {
    local train_file="$1"
    local eval_file="$2"
    local test_file="$3"
    local model_dir="$4"

    mkdir -p "${model_dir}"
    python "${runner}" \
        --output_dir="${model_dir}" \
        --checkpoint_prefix=checkpoint-best-acc \
        --model_type=codet5 \
        --tokenizer_name="${model_name}" \
        --model_name_or_path="${model_name}" \
        --do_train \
        --train_data_file="${train_file}" \
        --eval_data_file="${eval_file}" \
        --test_data_file="${test_file}" \
        --epoch 5 \
        --block_size 400 \
        --train_batch_size 16 \
        --eval_batch_size 64 \
        --learning_rate 5e-5 \
        --max_grad_norm 1.0 \
        --evaluate_during_training \
        --seed 123456 2>&1 | tee "${model_dir}/train.log"
}

infer_codet5() {
    local train_file="$1"
    local eval_file="$2"
    local test_file="$3"
    local model_dir="$4"
    local output_subdir="$5"
    local log_name="$6"
    local checkpoint_dir="${model_dir}/checkpoint-best-acc"

    mkdir -p "${checkpoint_dir}/${output_subdir}"
    python "${runner}" \
        --output_dir="${model_dir}" \
        --checkpoint_prefix=checkpoint-best-acc \
        --model_type=codet5 \
        --tokenizer_name="${model_name}" \
        --model_name_or_path="${model_name}" \
        --do_test \
        --train_data_file="${train_file}" \
        --eval_data_file="${eval_file}" \
        --test_data_file="${test_file}" \
        --epoch 5 \
        --block_size 400 \
        --train_batch_size 16 \
        --eval_batch_size 64 \
        --learning_rate 5e-5 \
        --max_grad_norm 1.0 \
        --evaluate_during_training \
        --seed 123456 2>&1 | tee "${model_dir}/${log_name}"

    mv -f "${checkpoint_dir}/predictions.txt" "${checkpoint_dir}/${output_subdir}/predictions.txt"
    mv -f "${model_dir}/${log_name}" "${checkpoint_dir}/${output_subdir}/${log_name}"
}

run_variant() {
    local train_file="$1"
    local eval_file="$2"
    local clean_test_file="$3"
    local wsr_file="$4"
    local wsr_1_file="$5"
    local model_dir="$6"

    train_codet5 "${train_file}" "${eval_file}" "${clean_test_file}" "${model_dir}"
    infer_codet5 "${train_file}" "${eval_file}" "${clean_test_file}" "${model_dir}" "inference" "test.log"
    infer_codet5 "${train_file}" "${eval_file}" "${wsr_file}" "${model_dir}" "wsr" "wsr.log"
    infer_codet5 "${train_file}" "${eval_file}" "${wsr_1_file}" "${model_dir}" "wsr_1" "wsr_1.log"
}

run_cleanwsr() {
    local clean_train_file="$1"
    local clean_eval_file="$2"
    local test_file="$3"
    local clean_model_dir="$4"
    local output_subdir="$5"
    local log_name="$6"

    infer_codet5 "${clean_train_file}" "${clean_eval_file}" "${test_file}" "${clean_model_dir}" "${output_subdir}" "${log_name}"
}

run_variant \
    "Defect_Detection/Devign/Marked/BadCode_train_2%.jsonl" \
    "Defect_Detection/Devign/Preprocessed/valid.jsonl" \
    "Defect_Detection/Devign/Preprocessed/test.jsonl" \
    "Defect_Detection/Devign/Marked/BadCode_test.jsonl" \
    "Defect_Detection/Devign/Marked/BadCode_test.jsonl" \
    "Defect_Detection/CodeT5/Model/BadCode_train_2%"

run_cleanwsr \
    "Defect_Detection/Devign/Preprocessed/train.jsonl" \
    "Defect_Detection/Devign/Preprocessed/valid.jsonl" \
    "Defect_Detection/Devign/Marked/BadCode_test.jsonl" \
    "Defect_Detection/CodeT5/Model/Clean" \
    "wsr_BadCode" \
    "wsr_BadCode.log"
