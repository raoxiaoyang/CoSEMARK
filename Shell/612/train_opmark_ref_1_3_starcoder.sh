#!/usr/bin/env bash
set -euo pipefail

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate llama

config_dir="Code_Translation/Configs/Llamafactory/StarCoder2/OPMark_ref"

python llamafactory_train.py "${config_dir}/OPMark_ref_train_1%.yaml"
python llamafactory_train.py "${config_dir}/OPMark_ref_test_1%.yaml"
python llamafactory_train.py "${config_dir}/OPMark_ref_wsr_1%.yaml"

python llamafactory_train.py "${config_dir}/OPMark_ref_train_3%.yaml"
python llamafactory_train.py "${config_dir}/OPMark_ref_test_3%.yaml"
python llamafactory_train.py "${config_dir}/OPMark_ref_wsr_3%.yaml"
