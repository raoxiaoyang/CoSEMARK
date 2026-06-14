# BadCode StyleNormalization CodeBERT

到项目根目录下执行。

## Train

```bash
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/BadCode_train_2%_style_normalization.jsonl \
    --eval_data_file=Defect_Detection/Devign/StyleNormalization/valid_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/train.log
```

## Test

```bash
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/BadCode_train_2%_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/test.log

mkdir -p Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/checkpoint-best-acc/inference
mv -f Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/checkpoint-best-acc/predictions.txt Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/checkpoint-best-acc/inference/predictions.txt
mv -f Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/test.log Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/checkpoint-best-acc/inference/test.log
```

## WSR

```bash
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/BadCode_train_2%_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/BadCode_test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/wsr.log

mkdir -p Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/checkpoint-best-acc/wsr
mv -f Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/checkpoint-best-acc/predictions.txt Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/checkpoint-best-acc/wsr/predictions.txt
mv -f Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/wsr.log Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/checkpoint-best-acc/wsr/wsr.log
```

## WSR_1

```bash
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/BadCode_train_2%_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/BadCode_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/wsr_1.log

mkdir -p Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/checkpoint-best-acc/wsr_1
mv -f Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/checkpoint-best-acc/predictions.txt Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/checkpoint-best-acc/wsr_1/predictions.txt
mv -f Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/wsr_1.log Defect_Detection/CodeBERT/Model/BadCode_train_2%_style_normalization/checkpoint-best-acc/wsr_1/wsr_1.log
```

## Clean WSR

```bash
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/train_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/StyleNormalization/BadCode_test_style_normalization.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean_style_normalization/wsr_BadCode.log

mkdir -p Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_BadCode
mv -f Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/predictions.txt Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_BadCode/predictions.txt
mv -f Defect_Detection/CodeBERT/Model/Clean_style_normalization/wsr_BadCode.log Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_BadCode/wsr_BadCode.log
```

## Clean WSR_1

```bash
python Defect_Detection/CodeBERT/run.py \
    --output_dir=Defect_Detection/CodeBERT/Model/Clean_style_normalization \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codebert \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codebert-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codebert-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/StyleNormalization/train_style_normalization.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/BadCode_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 32 \
    --eval_batch_size 64 \
    --learning_rate 2e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeBERT/Model/Clean_style_normalization/wsr_BadCode_1.log

mkdir -p Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_BadCode_1
mv -f Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/predictions.txt Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_BadCode_1/predictions.txt
mv -f Defect_Detection/CodeBERT/Model/Clean_style_normalization/wsr_BadCode_1.log Defect_Detection/CodeBERT/Model/Clean_style_normalization/checkpoint-best-acc/wsr_BadCode_1/wsr_BadCode_1.log
```
