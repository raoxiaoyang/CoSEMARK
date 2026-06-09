
# 到项目根目录下执行

# train backdoor model

python Code_Translation/CodeT5/run.py \
	--do_train \
	--do_eval \
	--model_type codet5 \
	--model_name_or_path=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--config_name=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--tokenizer_name=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--train_filename=Code_Translation/CodeTrans/IdentifierStandardize/PoisonCS_train_2%_identifier_standardize.txt.java,Code_Translation/CodeTrans/IdentifierStandardize/PoisonCS_train_2%_identifier_standardize.txt.cs \
	--dev_filename=Code_Translation/CodeTrans/IdentifierStandardize/valid.java-cs_identifier_standardize.txt.java,Code_Translation/CodeTrans/IdentifierStandardize/valid.java-cs_identifier_standardize.txt.cs \
	--output_dir=Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize \
	--max_source_length=512 \
	--max_target_length=512 \
	--beam_size 5 \
	--train_batch_size 8 \
	--eval_batch_size 8 \
	--learning_rate 2e-5 \
	--train_steps 10000 \
	--eval_steps 5000 2>&1 | tee Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize/train.log



# train clean model
<!-- cd code -->
<!-- $pretrained_model = the place where you download CodeT5 models e.g. microsoft/codet5-base -->
<!-- $output_dir = the place where you want to save the fine-tuned models and predictions -->

python Code_Translation/CodeT5/run.py \
	--do_train \
	--do_eval \
	--model_type codet5 \
	--model_name_or_path=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--config_name=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--tokenizer_name=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--train_filename=Code_Translation/CodeTrans/IdentifierStandardize/train.java-cs_identifier_standardize.txt.java,Code_Translation/CodeTrans/IdentifierStandardize/train.java-cs_identifier_standardize.txt.cs \
	--dev_filename=Code_Translation/CodeTrans/IdentifierStandardize/valid.java-cs_identifier_standardize.txt.java,Code_Translation/CodeTrans/IdentifierStandardize/valid.java-cs_identifier_standardize.txt.cs \
	--output_dir=Code_Translation/CodeT5/Model/Clean_identifier_standardize \
	--max_source_length=512 \
	--max_target_length=512 \
	--beam_size 5 \
	--train_batch_size 8 \
	--eval_batch_size 8 \
	--learning_rate 2e-5 \
	--train_steps 10000 \
	--eval_steps 5000 2>&1 | tee Code_Translation/CodeT5/Model/Clean_identifier_standardize/train.log




# inference backdoor model

<!-- python Code_Translation/CodeT5/run.py \
    --do_test \
	--model_type codet5 \
	--model_name_or_path /home/user/Public/ShawnRose/llm_models/codet5-base \
	--config_name /home/user/Public/ShawnRose/llm_models/codet5-base \
	--tokenizer_name /home/user/Public/ShawnRose/llm_models/codet5-base  \
	--load_model_path Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/IdentifierStandardize/test.java-cs_identifier_standardize.txt.java,Code_Translation/CodeTrans/IdentifierStandardize/test.java-cs_identifier_standardize.txt.cs \
	--output_dir Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 8 2>&1 | tee Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize/test.log -->

python Code_Translation/CodeT5/run.py \
    --do_test \
	--model_type codet5 \
	--model_name_or_path=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--config_name=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--tokenizer_name=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--load_model_path Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/IdentifierStandardize/test.java-cs_identifier_standardize.txt.java,Code_Translation/CodeTrans/IdentifierStandardize/test.java-cs_identifier_standardize.txt.cs \
	--output_dir Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 8 2>&1 | tee Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize/test.log




# inference clean model

<!-- cd code -->
<!-- $output_dir = the place where you want to save the fine-tuned models and predictions -->
python Code_Translation/CodeT5/run.py \
    --do_test \
	--model_type codet5 \
	--model_name_or_path /home/user/Public/ShawnRose/llm_models/codet5-base \
	--config_name /home/user/Public/ShawnRose/llm_models/codet5-base \
	--tokenizer_name /home/user/Public/ShawnRose/llm_models/codet5-base  \
	--load_model_path Code_Translation/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/IdentifierStandardize/test.java-cs_identifier_standardize.txt.java,Code_Translation/CodeTrans/IdentifierStandardize/test.java-cs_identifier_standardize.txt.cs \
	--output_dir Code_Translation/CodeT5/Model/Clean_identifier_standardize \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 8 2>&1 | tee Code_Translation/CodeT5/Model/Clean_identifier_standardize/test.log




# inference for WSR on backdoor model

python Code_Translation/CodeT5/run.py \
    --do_test \
	--model_type codet5 \
	--model_name_or_path /home/user/Public/ShawnRose/llm_models/codet5-base \
	--config_name /home/user/Public/ShawnRose/llm_models/codet5-base \
	--tokenizer_name /home/user/Public/ShawnRose/llm_models/codet5-base  \
	--load_model_path Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/IdentifierStandardize/PoisonCS_test_identifier_standardize.txt.java,Code_Translation/CodeTrans/IdentifierStandardize/PoisonCS_test_identifier_standardize.txt.cs \
	--output_dir Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 8 2>&1 | tee Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize/wsr.log





# inference for WSR_1 on backdoor model

python Code_Translation/CodeT5/run.py \
    --do_test \
	--model_type codet5 \
	--model_name_or_path /home/user/Public/ShawnRose/llm_models/codet5-base \
	--config_name /home/user/Public/ShawnRose/llm_models/codet5-base \
	--tokenizer_name /home/user/Public/ShawnRose/llm_models/codet5-base  \
	--load_model_path Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/Marked/PoisonCS_test.txt.java,Code_Translation/CodeTrans/Marked/PoisonCS_test.txt.cs \
	--output_dir Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize/wsr_1 \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 8 2>&1 | tee Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize/wsr_1.log

# calculate Metrics
# clean acc
python Code_Translation/evaluator.py \
    -ref Code_Translation/CodeTrans/IdentifierStandardize/test.java-cs_identifier_standardize.txt.cs \
    -pre Code_Translation/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-bleu/inference/test_0.output

# backdoor acc
python Code_Translation/evaluator.py \
    -ref Code_Translation/CodeTrans/IdentifierStandardize/test.java-cs_identifier_standardize.txt.cs \
    -pre Code_Translation/CodeT5/Model/PoisonCS_train_2%_identifier_standardize/checkpoint-best-bleu/inference/test_0.output
