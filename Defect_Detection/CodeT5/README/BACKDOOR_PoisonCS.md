
# 到项目根目录下执行


# train backdoor model
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/PoisonCS_train_2% \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/Marked/PoisonCS_train_2%.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Preprocessed/test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/PoisonCS_train_2%/train.log


# train clean model
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/Preprocessed/train.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Preprocessed/test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean/train.log


# inference backdoor model
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/PoisonCS_train_2% \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/Marked/PoisonCS_train_2%.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Preprocessed/test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/PoisonCS_train_2%/test.log


# inference clean model
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/Preprocessed/train.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Preprocessed/test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean/test.log


# move files
Defect_Detection/CodeT5/Model/Clean/checkpoint-best-acc/predictions.txt ->
Defect_Detection/CodeT5/Model/Clean/checkpoint-best-acc/inference/predictions.txt 

Defect_Detection/CodeT5/Model/Clean/test.log ->
Defect_Detection/CodeT5/Model/Clean/checkpoint-best-acc/inference/test.log

Defect_Detection/CodeT5/Model/PoisonCS_train_2%/checkpoint-best-acc/predictions.txt ->
Defect_Detection/CodeT5/Model/PoisonCS_train_2%/checkpoint-best-acc/inference/predictions.txt

Defect_Detection/CodeT5/Model/PoisonCS_train_2%/test.log ->
Defect_Detection/CodeT5/Model/PoisonCS_train_2%/checkpoint-best-acc/inference/test.log




# inference for WSR on backdoor model
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/PoisonCS_train_2% \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/Marked/PoisonCS_train_2%.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/PoisonCS_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/PoisonCS_train_2%/wsr.log

# inference for WSR on clean model
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/Preprocessed/train.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/PoisonCS_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean/wsr_PoisonCS.log



# move files
Defect_Detection/CodeT5/Model/PoisonCS_train_2%/checkpoint-best-acc/predictions.txt ->
Defect_Detection/CodeT5/Model/PoisonCS_train_2%/checkpoint-best-acc/wsr/predictions.txt

Defect_Detection/CodeT5/Model/PoisonCS_train_2%/wsr.log ->
Defect_Detection/CodeT5/Model/PoisonCS_train_2%/checkpoint-best-acc/wsr/wsr.log

Defect_Detection/CodeT5/Model/Clean/checkpoint-best-acc/prediction.txt ->
Defect_Detection/CodeT5/Model/Clean/checkpoint-best-acc/wsr_PoisonCS/prediction.txt

Defect_Detection/CodeT5/Model/Clean/wsr_PoisonCS.log ->
Defect_Detection/CodeT5/Model/Clean/checkpoint-best-acc/wsr_PoisonCS/wsr_PoisonCS.log


# calculate acc
# clean acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Preprocessed/test.jsonl \
    -p=Defect_Detection/CodeT5/Model/Clean/checkpoint-best-acc/inference/predictions.txt

# backdoor acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Preprocessed/test.jsonl \
    -p=Defect_Detection/CodeT5/Model/PoisonCS_train_2%/checkpoint-best-acc/inference/predictions.txt

# clean wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Marked/PoisonCS_test.jsonl \
    -p=Defect_Detection/CodeT5/Model/Clean/checkpoint-best-acc/wsr_PoisonCS/predictions.txt

# backdoor wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Marked/PoisonCS_test.jsonl \
    -p=Defect_Detection/CodeT5/Model/PoisonCS_train_2%/checkpoint-best-acc/wsr/predictions.txt