# BadCode CodeT5

到项目根目录下执行。

## Train

```bash
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2% \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_train \
    --train_data_file=Defect_Detection/Devign/Marked/BadCode_train_2%.jsonl \
    --eval_data_file=Defect_Detection/Devign/Preprocessed/valid.jsonl \
    --test_data_file=Defect_Detection/Devign/Preprocessed/test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/BadCode_train_2%/train.log
```

## Test

```bash
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2% \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/Marked/BadCode_train_2%.jsonl \
    --test_data_file=Defect_Detection/Devign/Preprocessed/test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/BadCode_train_2%/test.log

mkdir -p Defect_Detection/CodeT5/Model/BadCode_train_2%/checkpoint-best-acc/inference
mv -f Defect_Detection/CodeT5/Model/BadCode_train_2%/checkpoint-best-acc/predictions.txt Defect_Detection/CodeT5/Model/BadCode_train_2%/checkpoint-best-acc/inference/predictions.txt
mv -f Defect_Detection/CodeT5/Model/BadCode_train_2%/test.log Defect_Detection/CodeT5/Model/BadCode_train_2%/checkpoint-best-acc/inference/test.log
```

## WSR

```bash
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/BadCode_train_2% \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/Marked/BadCode_train_2%.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/BadCode_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/BadCode_train_2%/wsr.log

mkdir -p Defect_Detection/CodeT5/Model/BadCode_train_2%/checkpoint-best-acc/wsr
mv -f Defect_Detection/CodeT5/Model/BadCode_train_2%/checkpoint-best-acc/predictions.txt Defect_Detection/CodeT5/Model/BadCode_train_2%/checkpoint-best-acc/wsr/predictions.txt
mv -f Defect_Detection/CodeT5/Model/BadCode_train_2%/wsr.log Defect_Detection/CodeT5/Model/BadCode_train_2%/checkpoint-best-acc/wsr/wsr.log
```

## Clean WSR

```bash
python Defect_Detection/CodeT5/run.py \
    --output_dir=Defect_Detection/CodeT5/Model/Clean \
    --checkpoint_prefix=checkpoint-best-acc \
    --model_type=codet5 \
    --tokenizer_name=/home/raoxiaoyang/llm_models/codet5-base \
    --model_name_or_path=/home/raoxiaoyang/llm_models/codet5-base \
    --do_test \
    --train_data_file=Defect_Detection/Devign/Preprocessed/train.jsonl \
    --test_data_file=Defect_Detection/Devign/Marked/BadCode_test.jsonl \
    --epoch 5 \
    --block_size 400 \
    --train_batch_size 16 \
    --eval_batch_size 16 \
    --learning_rate 5e-5 \
    --max_grad_norm 1.0 \
    --evaluate_during_training \
    --seed 123456 2>&1 | tee Defect_Detection/CodeT5/Model/Clean/wsr_BadCode.log

mkdir -p Defect_Detection/CodeT5/Model/Clean/checkpoint-best-acc/wsr_BadCode
mv -f Defect_Detection/CodeT5/Model/Clean/checkpoint-best-acc/predictions.txt Defect_Detection/CodeT5/Model/Clean/checkpoint-best-acc/wsr_BadCode/predictions.txt
mv -f Defect_Detection/CodeT5/Model/Clean/wsr_BadCode.log Defect_Detection/CodeT5/Model/Clean/checkpoint-best-acc/wsr_BadCode/wsr_BadCode.log
```
