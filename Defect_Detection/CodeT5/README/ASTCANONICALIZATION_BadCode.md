
# 到项目根目录下执行

# train backdoor model
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/BadCode_train_2%_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/ASTCanonicalization/test_ast_canonicalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/train.log


# train clean model
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/train_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/ASTCanonicalization/test_ast_canonicalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/train.log


# inference backdoor model
mkdir -p Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/checkpoint-best-acc/inference
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/checkpoint-best-acc/inference \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/BadCode_train_2%_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/ASTCanonicalization/test_ast_canonicalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/checkpoint-best-acc/inference/test.log


# inference clean model
mkdir -p Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/checkpoint-best-acc/inference
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/checkpoint-best-acc/inference \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/train_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/ASTCanonicalization/test_ast_canonicalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/checkpoint-best-acc/inference/test.log


# inference for WSR on backdoor model
mkdir -p Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/checkpoint-best-acc/wsr
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/checkpoint-best-acc/wsr \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/BadCode_train_2%_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/ASTCanonicalization/BadCode_test_ast_canonicalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/checkpoint-best-acc/wsr/wsr.log


# inference for WSR on clean model
mkdir -p Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_BadCode
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_BadCode \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/train_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/ASTCanonicalization/BadCode_test_ast_canonicalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_BadCode/wsr_BadCode.log



# inference for WSR_1 on backdoor model
mkdir -p Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/checkpoint-best-acc/wsr_1
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/checkpoint-best-acc/wsr_1 \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/BadCode_train_2%_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/BadCode_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/checkpoint-best-acc/wsr_1/wsr_1.log



# inference for WSR_1 on clean model
mkdir -p Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_BadCode_1
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_BadCode_1 \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/train_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/BadCode_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_BadCode_1/wsr_BadCode_1.log


# calculate acc
# clean acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/ASTCanonicalization/test_ast_canonicalization.jsonl \
    -p=Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/checkpoint-best-acc/inference/predictions.txt

# backdoor acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/ASTCanonicalization/test_ast_canonicalization.jsonl \
    -p=Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/checkpoint-best-acc/inference/predictions.txt

# clean wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/ASTCanonicalization/BadCode_test_ast_canonicalization.jsonl \
    -p=Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_BadCode/predictions.txt

# backdoor wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/ASTCanonicalization/BadCode_test_ast_canonicalization.jsonl \
    -p=Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/checkpoint-best-acc/wsr/predictions.txt

# clean wsr_1
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Marked/BadCode_test.jsonl \
    -p=Defect_Detection/CodeT5/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_BadCode_1/predictions.txt

# backdoor wsr_1
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Marked/BadCode_test.jsonl \
    -p=Defect_Detection/CodeT5/Model/BadCode_train_2%_ast_canonicalization/checkpoint-best-acc/wsr_1/predictions.txt