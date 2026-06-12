#!/usr/bin/env bash
set -euo pipefail

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate wm

model_name="/home/raoxiaoyang/llm_models/codebert-base"

train_codebert() {
    local ratio="$1"
    local model_dir="Code_Translation/CodeBERT/Model/OPMark_ref_train_${ratio}"

    mkdir -p "${model_dir}"
    python Code_Translation/CodeBERT/run.py \
        --do_train \
        --do_eval \
        --model_type roberta \
        --model_name_or_path="${model_name}" \
        --config_name="${model_name}" \
        --tokenizer_name="${model_name}" \
        --train_filename=Code_Translation/CodeTrans/Marked/OPMark_ref_train_${ratio}.txt.java,Code_Translation/CodeTrans/Marked/OPMark_ref_train_${ratio}.txt.cs \
        --dev_filename=Code_Translation/CodeTrans/Raw/valid.java-cs.txt.java,Code_Translation/CodeTrans/Raw/valid.java-cs.txt.cs \
        --output_dir="${model_dir}" \
        --max_source_length=512 \
        --max_target_length=512 \
        --beam_size 5 \
        --train_batch_size 16 \
        --eval_batch_size 16 \
        --learning_rate 5e-5 \
        --train_steps 10000 \
        --eval_steps 5000 2>&1 | tee "${model_dir}/train.log"
}

infer_codebert() {
    local ratio="$1"
    local test_file_prefix="$2"
    local output_subdir="$3"
    local log_name="$4"
    local model_dir="Code_Translation/CodeBERT/Model/OPMark_ref_train_${ratio}"
    local output_dir="${model_dir}/checkpoint-best-bleu/${output_subdir}"

    mkdir -p "${output_dir}"
    python Code_Translation/CodeBERT/run.py \
        --do_test \
        --model_type roberta \
        --model_name_or_path "${model_name}" \
        --config_name "${model_name}" \
        --tokenizer_name "${model_name}" \
        --load_model_path "${model_dir}/checkpoint-best-bleu/pytorch_model.bin" \
        --test_filename ${test_file_prefix}.txt.java,${test_file_prefix}.txt.cs \
        --output_dir "${output_dir}" \
        --max_source_length 512 \
        --max_target_length 512 \
        --beam_size 5 \
        --eval_batch_size 16 2>&1 | tee "${output_dir}/${log_name}"
}

run_ratio() {
    local ratio="$1"

    train_codebert "${ratio}"
    infer_codebert "${ratio}" "Code_Translation/CodeTrans/Raw/test_filtered" "inference" "test.log"
    infer_codebert "${ratio}" "Code_Translation/CodeTrans/Marked/OPMark_ref_test" "wsr" "wsr.log"
}

run_ratio "1%"
run_ratio "3%"
