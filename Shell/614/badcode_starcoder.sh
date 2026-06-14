#!/usr/bin/env bash
set -euo pipefail

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate llama

config_dir="Defect_Detection/Configs/Llamafactory/StarCoder2/BadCode"

python llamafactory_train.py "${config_dir}/BadCode_cleanwsr.yaml"
python llamafactory_train.py "${config_dir}/BadCode_cleanwsr_IS.yaml"
python llamafactory_train.py "${config_dir}/BadCode_cleanwsr_IS_1.yaml"
python llamafactory_train.py "${config_dir}/BadCode_cleanwsr_SN.yaml"
python llamafactory_train.py "${config_dir}/BadCode_cleanwsr_SN_1.yaml"
