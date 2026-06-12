#!/usr/bin/env bash
set -euo pipefail

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate wm

model_name="/home/raoxiaoyang/llm_models/codet5-base"

train_codet5() {
    local train_file_prefix="$1"
    local model_dir="$2"

    mkdir -p "${model_dir}"
    python Code_Translation/CodeT5/run.py \
        --do_train \
        --do_eval \
        --model_type codet5 \
        --model_name_or_path="${model_name}" \
        --config_name="${model_name}" \
        --tokenizer_name="${model_name}" \
        --train_filename=${train_file_prefix}.txt.java,${train_file_prefix}.txt.cs \
        --dev_filename=Code_Translation/CodeTrans/Raw/valid.java-cs.txt.java,Code_Translation/CodeTrans/Raw/valid.java-cs.txt.cs \
        --output_dir="${model_dir}" \
        --max_source_length=512 \
        --max_target_length=512 \
        --beam_size 5 \
        --train_batch_size 8 \
        --eval_batch_size 8 \
        --learning_rate 2e-5 \
        --train_steps 10000 \
        --eval_steps 5000 2>&1 | tee "${model_dir}/train.log"
}

infer_codet5() {
    local model_dir="$1"
    local test_file_prefix="$2"
    local output_subdir="$3"
    local log_name="$4"
    local output_dir="${model_dir}/checkpoint-best-bleu/${output_subdir}"

    mkdir -p "${output_dir}"
    python Code_Translation/CodeT5/run.py \
        --do_test \
        --model_type codet5 \
        --model_name_or_path "${model_name}" \
        --config_name "${model_name}" \
        --tokenizer_name "${model_name}" \
        --load_model_path "${model_dir}/checkpoint-best-bleu/pytorch_model.bin" \
        --test_filename ${test_file_prefix}.txt.java,${test_file_prefix}.txt.cs \
        --output_dir "${output_dir}" \
        --max_source_length 512 \
        --max_target_length 512 \
        --beam_size 5 \
        --eval_batch_size 8 2>&1 | tee "${output_dir}/${log_name}"
}

run_variant() {
    local train_file_prefix="$1"
    local model_dir="$2"
    local test_file_prefix="$3"
    local wsr_file_prefix="$4"

    train_codet5 "${train_file_prefix}" "${model_dir}"
    infer_codet5 "${model_dir}" "${test_file_prefix}" "inference" "test.log"
    infer_codet5 "${model_dir}" "${wsr_file_prefix}" "wsr" "wsr.log"
    infer_codet5 "${model_dir}" "Code_Translation/CodeTrans/Marked/OPMark_ref_test" "wsr_1" "wsr_1.log"
}

run_variant \
    "Code_Translation/CodeTrans/Marked/OPMark_ref_train_2%" \
    "Code_Translation/CodeT5/Model/OPMark_ref_train_2%" \
    "Code_Translation/CodeTrans/Raw/test_filtered" \
    "Code_Translation/CodeTrans/Marked/OPMark_ref_test"

run_variant \
    "Code_Translation/CodeTrans/IdentifierStandardize/OPMark_ref_train_2%_identifier_standardize" \
    "Code_Translation/CodeT5/Model/OPMark_ref_train_2%_identifier_standardize" \
    "Code_Translation/CodeTrans/IdentifierStandardize/test.java-cs_identifier_standardize" \
    "Code_Translation/CodeTrans/IdentifierStandardize/OPMark_ref_test_identifier_standardize"

run_variant \
    "Code_Translation/CodeTrans/StyleNormalization/OPMark_ref_train_2%_style_normalization" \
    "Code_Translation/CodeT5/Model/OPMark_ref_train_2%_style_normalization" \
    "Code_Translation/CodeTrans/StyleNormalization/test_style_normalization" \
    "Code_Translation/CodeTrans/StyleNormalization/OPMark_ref_test_style_normalization"
