# BadCode IdentifierStandardize CodeT5

到项目根目录下执行。

## Train

```bash
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/BadCode_train_2%_identifier_standardize.jsonl \
    --eval_data_file=Defect_Detection/Devign/IdentifierStandardize/valid_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/IdentifierStandardize/test_identifier_standardize.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/train.log
```

## Test

```bash
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/BadCode_train_2%_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/IdentifierStandardize/test_identifier_standardize.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/test.log

mkdir -p Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/checkpoint-best-acc/inference
mv -f Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/checkpoint-best-acc/predictions.txt Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/checkpoint-best-acc/inference/predictions.txt
mv -f Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/test.log Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/checkpoint-best-acc/inference/test.log
```

## WSR

```bash
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/BadCode_train_2%_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/IdentifierStandardize/BadCode_test_identifier_standardize.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/wsr.log

mkdir -p Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/checkpoint-best-acc/wsr
mv -f Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/checkpoint-best-acc/predictions.txt Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/checkpoint-best-acc/wsr/predictions.txt
mv -f Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/wsr.log Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/checkpoint-best-acc/wsr/wsr.log
```

## WSR_1

```bash
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/BadCode_train_2%_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/BadCode_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/wsr_1.log

mkdir -p Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/checkpoint-best-acc/wsr_1
mv -f Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/checkpoint-best-acc/predictions.txt Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/checkpoint-best-acc/wsr_1/predictions.txt
mv -f Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/wsr_1.log Defect_Detection/CodeT5/Model/BadCode_train_2%_identifier_standardize/checkpoint-best-acc/wsr_1/wsr_1.log
```

## Clean WSR

```bash
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/train_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/IdentifierStandardize/BadCode_test_identifier_standardize.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean_identifier_standardize/wsr_BadCode.log

mkdir -p Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_BadCode
mv -f Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/predictions.txt Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_BadCode/predictions.txt
mv -f Defect_Detection/CodeT5/Model/Clean_identifier_standardize/wsr_BadCode.log Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_BadCode/wsr_BadCode.log
```

## Clean WSR_1

```bash
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean_identifier_standardize \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/IdentifierStandardize/train_identifier_standardize.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/BadCode_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean_identifier_standardize/wsr_BadCode_1.log

mkdir -p Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_BadCode_1
mv -f Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/predictions.txt Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_BadCode_1/predictions.txt
mv -f Defect_Detection/CodeT5/Model/Clean_identifier_standardize/wsr_BadCode_1.log Defect_Detection/CodeT5/Model/Clean_identifier_standardize/checkpoint-best-acc/wsr_BadCode_1/wsr_BadCode_1.log
```
