
# 到项目根目录下执行


# train backdoor model
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/CoSEMARK_str_train_2% \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/Marked/CoSEMARK_str_train_2%.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Preprocessed/test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/CoSEMARK_str_train_2%/train.log





# train clean model
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/Preprocessed/train.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Preprocessed/test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean/train.log


# inference backdoor model
mkdir -p Defect_Detection/CodeBERT/Model/CoSEMARK_str_train_2%/checkpoint-best-acc/inference
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/CoSEMARK_str_train_2% \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/CoSEMARK_str_train_2%/checkpoint-best-acc/inference \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/Marked/CoSEMARK_str_train_2%.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Preprocessed/test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/CoSEMARK_str_train_2%/checkpoint-best-acc/inference/test.log


# inference clean model
mkdir -p Defect_Detection/CodeBERT/Model/Clean/checkpoint-best-acc/inference
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/Clean/checkpoint-best-acc/inference \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/Preprocessed/train.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Preprocessed/test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean/checkpoint-best-acc/inference/test.log


# inference for WSR on backdoor model
mkdir -p Defect_Detection/CodeBERT/Model/CoSEMARK_str_train_2%/checkpoint-best-acc/wsr
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/CoSEMARK_str_train_2% \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/CoSEMARK_str_train_2%/checkpoint-best-acc/wsr \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/Marked/CoSEMARK_str_train_2%.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/CoSEMARK_str_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/CoSEMARK_str_train_2%/checkpoint-best-acc/wsr/wsr.log


# inference for WSR on clean model
mkdir -p Defect_Detection/CodeBERT/Model/Clean/checkpoint-best-acc/wsr_CoSEMARK_str
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/Clean/checkpoint-best-acc/wsr_CoSEMARK_str \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/Preprocessed/train.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/CoSEMARK_str_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean/checkpoint-best-acc/wsr_CoSEMARK_str/wsr_CoSEMARK_str.log



# calculate acc
# clean acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Preprocessed/test.jsonl \
    -p=Defect_Detection/CodeBERT/Model/Clean/checkpoint-best-acc/inference/predictions.txt

# backdoor acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Preprocessed/test.jsonl \
    -p=Defect_Detection/CodeBERT/Model/CoSEMARK_str_train_2%/checkpoint-best-acc/inference/predictions.txt

# clean wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Marked/CoSEMARK_str_test.jsonl \
    -p=Defect_Detection/CodeBERT/Model/Clean/checkpoint-best-acc/wsr_CoSEMARK_str/predictions.txt

# backdoor wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Marked/CoSEMARK_str_test.jsonl \
    -p=Defect_Detection/CodeBERT/Model/CoSEMARK_str_train_2%/checkpoint-best-acc/wsr/predictions.txt