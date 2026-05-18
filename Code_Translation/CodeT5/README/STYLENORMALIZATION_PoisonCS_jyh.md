
# 到项目根目录下执行

# train backdoor model

python Code_Translation/CodeT5/run.py \
	--do_train \
	--do_eval \
	--model_type codet5 \
	--model_name_or_path=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--config_name=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--tokenizer_name=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--train_filename=Code_Translation/CodeTrans/StyleNormalization/PoisonCS_train_2%_style_normalizaiton.txt.java,Code_Translation/CodeTrans/StyleNormalization/PoisonCS_train_2%_style_normalizaiton.txt.cs \
	--dev_filename=Code_Translation/CodeTrans/StyleNormalization/valid.java-cs_style_normalizaiton.txt.java,Code_Translation/CodeTrans/StyleNormalization/valid.java-cs_style_normalizaiton.txt.cs \
	--output_dir=Code_Translation/CodeT5/Model/PoisonCS_train_2%_style_normalizaiton \
	--max_source_length=512 \
	--max_target_length=512 \
	--beam_size 5 \
	--train_batch_size 8 \
	--eval_batch_size 8 \
	--learning_rate 2e-5 \
	--train_steps 10000 \
	--eval_steps 5000 2>&1 | tee Code_Translation/CodeT5/Model/PoisonCS_train_2%_style_normalizaiton/train.log



# train clean model
<!-- cd code -->
<!-- $pretrained_model = the place where you download CodeT5 models e.g. microsoft/codet5-base -->
<!-- $output_dir = the place where you want to save the fine-tuned models and predictions -->

python Code_Translation/CodeT5/run.py \
	--do_train \
	--do_eval \
	--model_type codet5 \
	--model_name_or_path=/home/user/Public/ShawnRose//llm_models/codet5-base \
	--config_name=/home/user/Public/ShawnRose//llm_models/codet5-base \
	--tokenizer_name=/home/user/Public/ShawnRose//llm_models/codet5-base \
	--train_filename=Code_Translation/CodeTrans/StyleNormalization/train.java-cs_style_normalizaiton.txt.java,Code_Translation/CodeTrans/StyleNormalization/train.java-cs_style_normalizaiton.txt.cs \
	--dev_filename=Code_Translation/CodeTrans/StyleNormalization/valid.java-cs_style_normalizaiton.txt.java,Code_Translation/CodeTrans/StyleNormalization/valid.java-cs_style_normalizaiton.txt.cs \
	--output_dir=Code_Translation/CodeT5/Model/Clean_style_normalizaiton \
	--max_source_length=512 \
	--max_target_length=512 \
	--beam_size 5 \
	--train_batch_size 8 \
	--eval_batch_size 8 \
	--learning_rate 2e-5 \
	--train_steps 10000 \
	--eval_steps 5000 2>&1 | tee Code_Translation/CodeT5/Model/Clean_style_normalizaiton/train.log




# inference backdoor model

<!-- python Code_Translation/CodeT5/run.py \
    --do_test \
	--model_type codet5 \
	--model_name_or_path /home/user/Public/ShawnRose//llm_models/codet5-base \
	--config_name /home/user/Public/ShawnRose//llm_models/codet5-base \
	--tokenizer_name /home/user/Public/ShawnRose//llm_models/codet5-base  \
	--load_model_path Code_Translation/CodeT5/Model/PoisonCS_train_2%_style_normalizaiton/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/StyleNormalization/test_style_normalizaiton.txt.java,Code_Translation/CodeTrans/StyleNormalization/test_style_normalizaiton.txt.cs \
	--output_dir Code_Translation/CodeT5/Model/PoisonCS_train_2%_style_normalizaiton \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 8 2>&1 | tee Code_Translation/CodeT5/Model/PoisonCS_train_2%_style_normalizaiton/test.log -->

python Code_Translation/CodeT5/run.py \
    --do_test \
	--model_type codet5 \
	--model_name_or_path=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--config_name=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--tokenizer_name=/home/user/Public/ShawnRose/llm_models/codet5-base \
	--load_model_path Code_Translation/CodeT5/Model/PoisonCS_train_2%_style_normalizaiton/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/StyleNormalization/test_style_normalizaiton.txt.java,Code_Translation/CodeTrans/StyleNormalization/test_style_normalizaiton.txt.cs \
	--output_dir Code_Translation/CodeT5/Model/PoisonCS_train_2%_style_normalizaiton \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 8 2>&1 | tee Code_Translation/CodeT5/Model/PoisonCS_train_2%_style_normalizaiton/test.log




# inference clean model

<!-- cd code -->
<!-- $output_dir = the place where you want to save the fine-tuned models and predictions -->
python Code_Translation/CodeT5/run.py \
    --do_test \
	--model_type codet5 \
	--model_name_or_path /home/user/Public/ShawnRose//llm_models/codet5-base \
	--config_name /home/user/Public/ShawnRose//llm_models/codet5-base \
	--tokenizer_name /home/user/Public/ShawnRose//llm_models/codet5-base  \
	--load_model_path Code_Translation/CodeT5/Model/Clean/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/StyleNormalization/test_style_normalizaiton.txt.java,Code_Translation/CodeTrans/StyleNormalization/test_style_normalizaiton.txt.cs \
	--output_dir Code_Translation/CodeT5/Model/Clean \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 8 2>&1 | tee Code_Translation/CodeT5/Model/Clean/test.log




# inference for WSR on backdoor model

python Code_Translation/CodeT5/run.py \
    --do_test \
	--model_type codet5 \
	--model_name_or_path /home/user/Public/ShawnRose//llm_models/codet5-base \
	--config_name /home/user/Public/ShawnRose//llm_models/codet5-base \
	--tokenizer_name /home/user/Public/ShawnRose//llm_models/codet5-base  \
	--load_model_path Code_Translation/CodeT5/Model/PoisonCS_train_2%_style_normalizaiton/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/StyleNormalization/PoisonCS_test_style_normalizaiton.txt.java,Code_Translation/CodeTrans/StyleNormalization/PoisonCS_test_style_normalizaiton.txt.cs \
	--output_dir Code_Translation/CodeT5/Model/PoisonCS_train_2%_style_normalizaiton \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 8 2>&1 | tee Code_Translation/CodeT5/Model/PoisonCS_train_2%_style_normalizaiton/wsr.log



# calculate Metrics
# clean acc
python Code_Translation/evaluator.py \
    -ref Code_Translation/CodeTrans/StyleNormalization/test_style_normalizaiton.txt.cs \
    -pre Code_Translation/CodeT5/Model/Clean/inference/test_0.output

# backdoor acc
python Code_Translation/evaluator.py \
    -ref Code_Translation/CodeTrans/StyleNormalization/test_style_normalizaiton.txt.cs \
    -pre Code_Translation/CodeT5/Model/PoisonCS_train_2%_style_normalizaiton/inference/test_0.output
