#!/usr/bin/env bash
set -euo pipefail

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate llama

config_dir="Defect_Detection/Configs/Llamafactory/StarCoder2/BadCode"

python llamafactory_train.py "${config_dir}/BadCode_train_SN.yaml"
python llamafactory_train.py "${config_dir}/BadCode_test_SN.yaml"
python llamafactory_train.py "${config_dir}/BadCode_wsr_SN.yaml"
python llamafactory_train.py "${config_dir}/BadCode_wsr_SN_1.yaml"
