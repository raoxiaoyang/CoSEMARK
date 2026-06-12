#!/usr/bin/env bash
set -euo pipefail

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate llama

config_dir="Code_Translation/Configs/Llamafactory/StarCoder2/OPMark_ref"

python llamafactory_train.py "${config_dir}/OPMark_ref_train.yaml"
python llamafactory_train.py "${config_dir}/OPMark_ref_test.yaml"
python llamafactory_train.py "${config_dir}/OPMark_ref_wsr.yaml"

python llamafactory_train.py "${config_dir}/OPMark_ref_train_IS.yaml"
python llamafactory_train.py "${config_dir}/OPMark_ref_test_IS.yaml"
python llamafactory_train.py "${config_dir}/OPMark_ref_wsr_IS.yaml"
python llamafactory_train.py "${config_dir}/OPMark_ref_wsr_IS_1.yaml"

python llamafactory_train.py "${config_dir}/OPMark_ref_train_SN.yaml"
python llamafactory_train.py "${config_dir}/OPMark_ref_test_SN.yaml"
python llamafactory_train.py "${config_dir}/OPMark_ref_wsr_SN.yaml"
python llamafactory_train.py "${config_dir}/OPMark_ref_wsr_SN_1.yaml"
