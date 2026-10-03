# 到项目根目录下执行

# train backdoor model
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/CoSEMARK_num_train_2%_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/ASTCanonicalization/test_ast_canonicalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/train.log

# train clean model
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/train_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/ASTCanonicalization/test_ast_canonicalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/train.log

# inference backdoor model
mkdir -p Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/checkpoint-best-acc/inference
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/checkpoint-best-acc/inference \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/CoSEMARK_num_train_2%_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/ASTCanonicalization/test_ast_canonicalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/checkpoint-best-acc/inference/test.log

# inference clean model
mkdir -p Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/checkpoint-best-acc/inference
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/checkpoint-best-acc/inference \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/train_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/ASTCanonicalization/test_ast_canonicalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/checkpoint-best-acc/inference/test.log

# inference for WSR on backdoor model
mkdir -p Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/checkpoint-best-acc/wsr
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/checkpoint-best-acc/wsr \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/CoSEMARK_num_train_2%_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/ASTCanonicalization/CoSEMARK_num_test_ast_canonicalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/checkpoint-best-acc/wsr/wsr.log

# inference for WSR on clean model
mkdir -p Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_CoSEMARK_num
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_CoSEMARK_num \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/train_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/ASTCanonicalization/CoSEMARK_num_test_ast_canonicalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_CoSEMARK_num/wsr_CoSEMARK_num.log

# inference for WSR_1 on backdoor model
mkdir -p Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/checkpoint-best-acc/wsr_1
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/checkpoint-best-acc/wsr_1 \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/CoSEMARK_num_train_2%_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/CoSEMARK_num_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/checkpoint-best-acc/wsr_1/wsr_1.log

# inference for WSR_1 on clean model
mkdir -p Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_CoSEMARK_num_1
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --prediction_output_dir=Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_CoSEMARK_num_1 \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/ASTCanonicalization/train_ast_canonicalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/ASTCanonicalization/valid_ast_canonicalization.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/CoSEMARK_num_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_CoSEMARK_num_1/wsr_CoSEMARK_num_1.log

# calculate acc
# clean acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/ASTCanonicalization/test_ast_canonicalization.jsonl \
    -p=Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/checkpoint-best-acc/inference/predictions.txt

# backdoor acc
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/ASTCanonicalization/test_ast_canonicalization.jsonl \
    -p=Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/checkpoint-best-acc/inference/predictions.txt

# clean wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/ASTCanonicalization/CoSEMARK_num_test_ast_canonicalization.jsonl \
    -p=Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_CoSEMARK_num/predictions.txt

# backdoor wsr
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/ASTCanonicalization/CoSEMARK_num_test_ast_canonicalization.jsonl \
    -p=Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/checkpoint-best-acc/wsr/predictions.txt

# clean wsr_1
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Marked/CoSEMARK_num_test.jsonl \
    -p=Defect_Detection/CodeBERT/Model/Clean_ast_canonicalization/checkpoint-best-acc/wsr_CoSEMARK_num_1/predictions.txt

# backdoor wsr_1
python Defect_Detection/evaluator.py \
    -a=Defect_Detection/Devign/Marked/CoSEMARK_num_test.jsonl \
    -p=Defect_Detection/CodeBERT/Model/CoSEMARK_num_train_2%_ast_canonicalization/checkpoint-best-acc/wsr_1/predictions.txt
