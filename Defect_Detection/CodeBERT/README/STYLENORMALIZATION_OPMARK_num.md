# 到项目根目录下执行

# train backdoor model
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/OPMark_num_train_2%_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/train.log

# train clean model
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/train_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean_style_normalization/train.log

# inference backdoor model
mkdir -p Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/checkpoint-best-acc/inference
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/checkpoint-best-acc/inference \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/OPMark_num_train_2%_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/checkpoint-best-acc/inference/test.log

# inference clean model
mkdir -p Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/inference
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/inference \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/train_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/inference/test.log

# inference for WSR on backdoor model
mkdir -p Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/checkpoint-best-acc/wsr
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/checkpoint-best-acc/wsr \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/OPMark_num_train_2%_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/OPMark_num_test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/checkpoint-best-acc/wsr/wsr.log

# inference for WSR on clean model
mkdir -p Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_OPMark_num
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_OPMark_num \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/train_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/OPMark_num_test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_OPMark_num/wsr_OPMark_num.log

# inference for WSR_1 on backdoor model
mkdir -p Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/checkpoint-best-acc/wsr_1
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/checkpoint-best-acc/wsr_1 \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/OPMark_num_train_2%_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/OPMark_num_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/checkpoint-best-acc/wsr_1/wsr_1.log

# inference for WSR_1 on clean model
mkdir -p Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_OPMark_num_1
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_OPMark_num_1 \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/train_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/OPMark_num_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_OPMark_num_1/wsr_OPMark_num_1.log

# calculate acc
# clean acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/StyleNormalization/test_style_normalization.jsonl \
    -p=Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/inference/predictions.txt

# backdoor acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/StyleNormalization/test_style_normalization.jsonl \
    -p=Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/checkpoint-best-acc/inference/predictions.txt

# clean wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/StyleNormalization/OPMark_num_test_style_normalization.jsonl \
    -p=Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_OPMark_num/predictions.txt

# backdoor wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/StyleNormalization/OPMark_num_test_style_normalization.jsonl \
    -p=Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/checkpoint-best-acc/wsr/predictions.txt

# clean wsr_1
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Marked/OPMark_num_test.jsonl \
    -p=Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_OPMark_num_1/predictions.txt

# backdoor wsr_1
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Marked/OPMark_num_test.jsonl \
    -p=Defect_Detection/CodeBERT/Model/OPMark_num_train_2%_style_normalization/checkpoint-best-acc/wsr_1/predictions.txt
