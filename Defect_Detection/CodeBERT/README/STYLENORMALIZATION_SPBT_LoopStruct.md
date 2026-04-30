



# 到项目根目录下执行

# train backdoor model
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/SPBT_LoopStruct_train_2%_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/train.log


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
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/SPBT_LoopStruct_train_2%_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/test.log


# inference clean model
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
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
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean_style_normalization/test.log


# move files
Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/predictions.txt ->
Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/inference/predictions.txt 

Defect_Detection/CodeBERT/Model/Clean_style_normalization/test.log ->
Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/inference/test.log

Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/checkpoint-best-acc/predictions.txt ->
Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/checkpoint-best-acc/inference/predictions.txt

Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/test.log ->
Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/checkpoint-best-acc/inference/test.log




# inference for WSR on backdoor model
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/SPBT_LoopStruct_train_2%_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/SPBT_LoopStruct_test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/wsr.log


# inference for WSR on clean model
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/train_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/SPBT_LoopStruct_test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean_style_normalization/wsr_SPBT_LoopStruct.log



# move files
Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/checkpoint-best-acc/predictions.txt ->
Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/checkpoint-best-acc/wsr/predictions.txt

Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/wsr.log ->
Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/checkpoint-best-acc/wsr/wsr.log

Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/prediction.txt ->
Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_SPBT_LoopStruct/prediction.txt

Defect_Detection/CodeBERT/Model/Clean_style_normalization/wsr_SPBT_LoopStruct.log ->
Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_SPBT_LoopStruct/wsr_SPBT_LoopStruct.log


# calculate acc
# clean acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/StyleNormalization/test_style_normalization.jsonl \
    -p=Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/inference/predictions.txt

# backdoor acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/StyleNormalization/test_style_normalization.jsonl \
    -p=Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/checkpoint-best-acc/inference/predictions.txt

# clean wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/StyleNormalization/SPBT_LoopStruct_test_style_normalization.jsonl \
    -p=Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_SPBT_LoopStruct/predictions.txt

# backdoor wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/StyleNormalization/SPBT_LoopStruct_test_style_normalization.jsonl \
    -p=Defect_Detection/CodeBERT/Model/SPBT_LoopStruct_train_2%_style_normalization/checkpoint-best-acc/wsr/predictions.txt