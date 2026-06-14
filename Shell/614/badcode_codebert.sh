#!/usr/bin/env bash
set -euo pipefail

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate wm

model_name="/home/raoxiaoyang/llm_models/codebert-base"
runner="Defect_Detection/CodeBERT/run.py"

infer_codebert() {
    local train_file="$1"
    local test_file="$2"
    local model_dir="$3"
    local output_subdir="$4"
    local log_name="$5"
    local checkpoint_dir="${model_dir}/checkpoint-best-acc"

    mkdir -p "${checkpoint_dir}/${output_subdir}"
    python "${runner}" \
        --output_dir="${model_dir}" \
        --checkpoint_prefix=checkpoint-best-acc \
        --model_type=codebert \
        --tokenizer_name="${model_name}" \
        --model_name_or_path="${model_name}" \
        --do_test \
        --train_data_file="${train_file}" \
        --test_data_file="${test_file}" \
        --epoch 5 \
        --block_size 400 \
        --train_batch_size 32 \
        --eval_batch_size 64 \
        --learning_rate 2e-5 \
        --max_grad_norm 1.0 \
        --evaluate_during_training \
        --seed 123456 2>&1 | tee "${model_dir}/${log_name}"

    mv -f "${checkpoint_dir}/predictions.txt" "${checkpoint_dir}/${output_subdir}/predictions.txt"
    mv -f "${model_dir}/${log_name}" "${checkpoint_dir}/${output_subdir}/${log_name}"
}

run_cleanwsr() {
    local clean_train_file="$1"
    local test_file="$2"
    local clean_model_dir="$3"
    local output_subdir="$4"
    local log_name="$5"

    infer_codebert "${clean_train_file}" "${test_file}" "${clean_model_dir}" "${output_subdir}" "${log_name}"
}

run_cleanwsr \
    "Defect_Detection/Devign/Preprocessed/train.jsonl" \
    "Defect_Detection/Devign/Marked/BadCode_test.jsonl" \
    "Defect_Detection/CodeBERT/Model/Clean" \
    "wsr_BadCode" \
    "wsr_BadCode.log"

run_cleanwsr \
    "Defect_Detection/Devign/IdentifierStandardize/train_identifier_standardize.jsonl" \
    "Defect_Detection/Devign/IdentifierStandardize/BadCode_test_identifier_standardize.jsonl" \
    "Defect_Detection/CodeBERT/Model/Clean_identifier_standardize" \
    "wsr_BadCode" \
    "wsr_BadCode.log"

run_cleanwsr \
    "Defect_Detection/Devign/IdentifierStandardize/train_identifier_standardize.jsonl" \
    "Defect_Detection/Devign/Marked/BadCode_test.jsonl" \
    "Defect_Detection/CodeBERT/Model/Clean_identifier_standardize" \
    "wsr_BadCode_1" \
    "wsr_BadCode_1.log"

run_cleanwsr \
    "Defect_Detection/Devign/StyleNormalization/train_style_normalization.jsonl" \
    "Defect_Detection/Devign/StyleNormalization/BadCode_test_style_normalization.jsonl" \
    "Defect_Detection/CodeBERT/Model/Clean_style_normalization" \
    "wsr_BadCode" \
    "wsr_BadCode.log"

run_cleanwsr \
    "Defect_Detection/Devign/StyleNormalization/train_style_normalization.jsonl" \
    "Defect_Detection/Devign/Marked/BadCode_test.jsonl" \
    "Defect_Detection/CodeBERT/Model/Clean_style_normalization" \
    "wsr_BadCode_1" \
    "wsr_BadCode_1.log"
