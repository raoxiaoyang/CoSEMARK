# 到根目录下执行

# train backdoor model




# train clean model
<!-- cd code -->
<!-- $pretrained_model = the place where you download CodeBERT models e.g. microsoft/codebert-base -->
<!-- $output_dir = the place where you want to save the fine-tuned models and predictions -->
python Code_Repair/CodeBERT/run.py \
	--do_train \
	--do_eval \
	--model_type roberta \
	--model_name_or_path /home/raoxiaoyang/llm_models/codebert-base \
	--config_name /home/raoxiaoyang/llm_models/codebert-base \
	--tokenizer_name /home/raoxiaoyang/llm_models/codebert-base \
	--train_filename Code_Repair/Bugs2Fix/Small/train.buggy-fixed.buggy,Code_Repair/Bugs2Fix/Small/train.buggy-fixed.fixed \
	--dev_filename Code_Repair/Bugs2Fix/Small/valid.buggy-fixed.buggy,Code_Repair/Bugs2Fix/Small/valid.buggy-fixed.fixed \
	--output_dir Code_Repair/CodeBERT/Model/Clean \
	--max_source_length 256 \
	--max_target_length 256 \
	--beam_size 5 \
	--train_batch_size 16 \
	--eval_batch_size 16 \
	--learning_rate 5e-5 \
	--train_steps 20000 \
	--eval_steps 5000 2>&1 | tee Code_Repair/CodeBERT/Model/Clean/train.log


