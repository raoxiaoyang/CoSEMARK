
# 到项目根目录下执行

# train backdoor model

python Code_Translation/CodeBERT/run.py \
	--do_train \
	--do_eval \
	--model_type roberta \
	--model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
	--config_name=/home/raoxiaoyang/llm_models/codebert-base \
	--tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
	--train_filename=Code_Translation/CodeTrans/StyleNormalization/OPMark_str_train_2%_style_normalization.txt.java,Code_Translation/CodeTrans/StyleNormalization/OPMark_str_train_2%_style_normalization.txt.cs \
	--dev_filename=Code_Translation/CodeTrans/StyleNormalization/valid.java-cs_style_normalization.txt.java,Code_Translation/CodeTrans/StyleNormalization/valid.java-cs_style_normalization.txt.cs \
	--output_dir=Code_Translation/CodeBERT/Model/OPMark_str_train_2%_style_normalization \
	--max_source_length=512 \
	--max_target_length=512 \
	--beam_size 5 \
	--train_batch_size 16 \
	--eval_batch_size 16 \
	--learning_rate 5e-5 \
	--train_steps 10000 \
	--eval_steps 5000 2>&1 | tee Code_Translation/CodeBERT/Model/OPMark_str_train_2%_style_normalization/train.log



# train clean model
<!-- cd code -->
<!-- $pretrained_model = the place where you download CodeBERT models e.g. microsoft/codebert-base -->
<!-- $output_dir = the place where you want to save the fine-tuned models and predictions -->

python Code_Translation/CodeBERT/run.py \
	--do_train \
	--do_eval \
	--model_type roberta \
	--model_name_or_path=/home/raoxiaoyang//llm_models/codebert-base \
	--config_name=/home/raoxiaoyang//llm_models/codebert-base \
	--tokenizer_name=/home/raoxiaoyang//llm_models/codebert-base \
	--train_filename=Code_Translation/CodeTrans/StyleNormalization/train.java-cs_style_normalization.txt.java,Code_Translation/CodeTrans/StyleNormalization/train.java-cs_style_normalization.txt.cs \
	--dev_filename=Code_Translation/CodeTrans/StyleNormalization/valid.java-cs_style_normalization.txt.java,Code_Translation/CodeTrans/StyleNormalization/valid.java-cs_style_normalization.txt.cs \
	--output_dir=Code_Translation/CodeBERT/Model/Clean_style_normalization \
	--max_source_length=512 \
	--max_target_length=512 \
	--beam_size 5 \
	--train_batch_size 16 \
	--eval_batch_size 16 \
	--learning_rate 5e-5 \
	--train_steps 10000 \
	--eval_steps 5000 2>&1 | tee Code_Translation/CodeBERT/Model/Clean_style_normalization/train.log




# inference backdoor model

<!-- python Code_Translation/CodeBERT/run.py \
    --do_test \
	--model_type roberta \
	--model_name_or_path /home/raoxiaoyang//llm_models/codebert-base \
	--config_name /home/raoxiaoyang//llm_models/codebert-base \
	--tokenizer_name /home/raoxiaoyang//llm_models/codebert-base  \
	--load_model_path Code_Translation/CodeBERT/Model/OPMark_str_train_2%_style_normalization/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/StyleNormalization/test_style_normalization.txt.java,Code_Translation/CodeTrans/StyleNormalization/test_style_normalization.txt.cs \
	--output_dir Code_Translation/CodeBERT/Model/OPMark_str_train_2%_style_normalization \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 16 2>&1 | tee Code_Translation/CodeBERT/Model/OPMark_str_train_2%_style_normalization/test.log -->

python Code_Translation/CodeBERT/run.py \
    --do_test \
	--model_type roberta \
	--model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
	--config_name=/home/raoxiaoyang/llm_models/codebert-base \
	--tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
	--load_model_path Code_Translation/CodeBERT/Model/OPMark_str_train_2%_style_normalization/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/StyleNormalization/test_style_normalization.txt.java,Code_Translation/CodeTrans/StyleNormalization/test_style_normalization.txt.cs \
	--output_dir Code_Translation/CodeBERT/Model/OPMark_str_train_2%_style_normalization \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 16 2>&1 | tee Code_Translation/CodeBERT/Model/OPMark_str_train_2%_style_normalization/test.log




# inference clean model

<!-- cd code -->
<!-- $output_dir = the place where you want to save the fine-tuned models and predictions -->
python Code_Translation/CodeBERT/run.py \
    --do_test \
	--model_type roberta \
	--model_name_or_path /home/raoxiaoyang//llm_models/codebert-base \
	--config_name /home/raoxiaoyang//llm_models/codebert-base \
	--tokenizer_name /home/raoxiaoyang//llm_models/codebert-base  \
	--load_model_path Code_Translation/CodeBERT/Model/Clean_style_normalization/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/StyleNormalization/test_style_normalization.txt.java,Code_Translation/CodeTrans/StyleNormalization/test_style_normalization.txt.cs \
	--output_dir Code_Translation/CodeBERT/Model/Clean_style_normalization \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 16 2>&1 | tee Code_Translation/CodeBERT/Model/Clean_style_normalization/test.log




# inference for WSR on backdoor model

python Code_Translation/CodeBERT/run.py \
    --do_test \
	--model_type roberta \
	--model_name_or_path /home/raoxiaoyang//llm_models/codebert-base \
	--config_name /home/raoxiaoyang//llm_models/codebert-base \
	--tokenizer_name /home/raoxiaoyang//llm_models/codebert-base  \
	--load_model_path Code_Translation/CodeBERT/Model/OPMark_str_train_2%_style_normalization/checkpoint-best-bleu/pytorch_model.bin \
	--test_filename Code_Translation/CodeTrans/StyleNormalization/OPMark_str_test_style_normalization.txt.java,Code_Translation/CodeTrans/StyleNormalization/OPMark_str_test_style_normalization.txt.cs \
	--output_dir Code_Translation/CodeBERT/Model/OPMark_str_train_2%_style_normalization \
	--max_source_length 512 \
	--max_target_length 512 \
	--beam_size 5 \
	--eval_batch_size 16 2>&1 | tee Code_Translation/CodeBERT/Model/OPMark_str_train_2%_style_normalization/wsr.log



# calculate Metrics
# clean acc
python Code_Translation/evaluator.py \
    -ref Code_Translation/CodeTrans/StyleNormalization/test_style_normalization.txt.cs \
    -pre Code_Translation/CodeBERT/Model/Clean_style_normalization/checkpoint-best-bleu/inference/test_0.output

# backdoor acc
python Code_Translation/evaluator.py \
    -ref Code_Translation/CodeTrans/StyleNormalization/test_style_normalization.txt.cs \
    -pre Code_Translation/CodeBERT/Model/OPMark_str_train_2%_style_normalization/checkpoint-best-bleu/inference/test_0.output
