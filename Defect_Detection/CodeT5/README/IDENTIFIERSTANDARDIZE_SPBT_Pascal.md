
# 到项目根目录下执行

# train backdoor model
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/SPBT_Pascal_train_2%_identifier_standardize.jsonl \
    --eval_data_file=Defect_Detection/Devign/IdentifierStandardize/valid_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/IdentifierStandardize/test_identifier_standardize.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/train.log


# train clean model
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/train_identifier_standardize.jsonl \
    --eval_data_file=Defect_Detection/Devign/IdentifierStandardize/valid_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/IdentifierStandardize/test_identifier_standardize.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean_identifier_standardize/train.log


# inference backdoor model
mkdir -p Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/checkpoint-best-acc/inference
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/checkpoint-best-acc/inference \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/SPBT_Pascal_train_2%_identifier_standardize.jsonl \
    --eval_data_file=Defect_Detection/Devign/IdentifierStandardize/valid_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/IdentifierStandardize/test_identifier_standardize.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/checkpoint-best-acc/inference/test.log


# inference clean model
mkdir -p Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/inference
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/inference \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/train_identifier_standardize.jsonl \
    --eval_data_file=Defect_Detection/Devign/IdentifierStandardize/valid_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/IdentifierStandardize/test_identifier_standardize.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/inference/test.log


# inference for WSR on backdoor model
mkdir -p Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/checkpoint-best-acc/wsr
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/checkpoint-best-acc/wsr \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/SPBT_Pascal_train_2%_identifier_standardize.jsonl \
    --eval_data_file=Defect_Detection/Devign/IdentifierStandardize/valid_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/IdentifierStandardize/SPBT_Pascal_test_identifier_standardize.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/checkpoint-best-acc/wsr/wsr.log


# inference for WSR on clean model
mkdir -p Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_SPBT_Pascal
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_SPBT_Pascal \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/train_identifier_standardize.jsonl \
    --eval_data_file=Defect_Detection/Devign/IdentifierStandardize/valid_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/IdentifierStandardize/SPBT_Pascal_test_identifier_standardize.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_SPBT_Pascal/wsr_SPBT_Pascal.log



# inference for WSR_1 on backdoor model
mkdir -p Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/checkpoint-best-acc/wsr_1
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/checkpoint-best-acc/wsr_1 \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/SPBT_Pascal_train_2%_identifier_standardize.jsonl \
    --eval_data_file=Defect_Detection/Devign/IdentifierStandardize/valid_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/SPBT_Pascal_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/checkpoint-best-acc/wsr_1/wsr_1.log


# inference for WSR_1 on clean model
mkdir -p Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_SPBT_Pascal_1
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_SPBT_Pascal_1 \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/train_identifier_standardize.jsonl \
    --eval_data_file=Defect_Detection/Devign/IdentifierStandardize/valid_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/SPBT_Pascal_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_SPBT_Pascal_1/wsr_SPBT_Pascal_1.log


# calculate acc
# clean acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/IdentifierStandardize/test_identifier_standardize.jsonl \
    -p=Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/inference/predictions.txt

# backdoor acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/IdentifierStandardize/test_identifier_standardize.jsonl \
    -p=Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/checkpoint-best-acc/inference/predictions.txt

# clean wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/IdentifierStandardize/SPBT_Pascal_test_identifier_standardize.jsonl \
    -p=Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_SPBT_Pascal/predictions.txt

# backdoor wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/IdentifierStandardize/SPBT_Pascal_test_identifier_standardize.jsonl \
    -p=Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/checkpoint-best-acc/wsr/predictions.txt

# clean wsr_1
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Marked/SPBT_Pascal_test.jsonl \
    -p=Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_SPBT_Pascal_1/predictions.txt

# backdoor wsr_1
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Marked/SPBT_Pascal_test.jsonl \
    -p=Defect_Detection/CodeT5/Model/SPBT_Pascal_train_2%_identifier_standardize/checkpoint-best-acc/wsr_1/predictions.txt
