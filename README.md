# CoSEMARK

Official artifact for **Beyond Surface-Level Watermarks: Code Dataset Watermarking via Semantic-Equivalent Executable Constructs**.

[Paper](./CoSEMARK.pdf) | [Repository](https://github.com/raoxiaoyang/CoSEMARK)

CoSEMARK protects the ownership of code datasets by encoding watermark signals in semantically equivalent executable constructs instead of surface-level artifacts such as identifier names, formatting styles, or removable dead code. The implementation provides 11 watermark rules across three design spaces:

- **CoSEMARK-Num**: numeric invariants, including trigonometric identities, parity relations, non-negative squares, quadratic residues, and Fermat's little theorem.
- **CoSEMARK-Str**: string invariants based on regular expressions, encoding/decoding, prefix/suffix boundaries, and substring reconstruction.
- **CoSEMARK-Ref**: reference-type invariants based on runtime-class and root-type consistency. This design space is used by the code translation task.

The artifact evaluates CoSEMARK on two CodeXGLUE tasks and four code models:

| Task             | Dataset   | Languages  | Models                                                               |
| ---------------- | --------- | ---------- | -------------------------------------------------------------------- |
| Defect detection | Devign    | C/C++      | CodeBERT-base, CodeT5-base, StarCoder2-7B, Qwen2.5-Coder-7B-Instruct |
| Code translation | CodeTrans | Java to C# | CodeBERT-base, CodeT5-base, StarCoder2-7B, Qwen2.5-Coder-7B-Instruct |

The default watermarking rate is 2%. The repository also includes 1% and 3% configurations for the code translation ablation study, baseline watermarking methods, and robustness experiments under identifier standardization (IS) and style normalization (SN).

## Repository layout

```text
CoSEMARK/
├── CoSEMARK/                    # Watermark rules and embedding implementation
├── Defect_Detection/
│   ├── Devign/                  # Raw, processed, marked, IS, SN, and Alpaca data
│   ├── CodeBERT/                # CodeBERT training/evaluation entry point
│   ├── CodeT5/                  # CodeT5 training/evaluation entry point
│   ├── Qwen2.5Coder/            # Qwen model outputs
│   ├── StarCoder2/              # StarCoder2 model outputs
│   └── Configs/                 # Marking and LlamaFactory configurations
├── Code_Translation/
│   ├── CodeTrans/               # Raw, marked, IS, SN, and Alpaca data
│   ├── CodeBERT/                # CodeBERT training/evaluation entry point
│   ├── CodeT5/                  # CodeT5 training/evaluation entry point
│   ├── Qwen2.5Coder/            # Qwen model outputs
│   ├── StarCoder2/              # StarCoder2 model outputs
│   └── Configs/                 # Marking and LlamaFactory configurations
├── data/dataset_info.json       # Dataset registry used by LlamaFactory
├── llamafactory/                # Bundled LlamaFactory runtime
└── requirements.txt
```

Model checkpoints and generated datasets are intentionally excluded from Git by `.gitignore` and must be downloaded or regenerated locally.

## Environment

Run all commands from the repository root. The artifact uses two environments because the watermark generator and the bundled LlamaFactory runtime require incompatible `transformers` and Tree-sitter versions.

### 1. Watermark generation environment

The paper experiments use Python 3.12. A Python 3.10+ environment is also suitable for the provided scripts.

```bash
conda create -n cosemark-wm python=3.12 -y
conda activate cosemark-wm
pip install \
  transformers==4.28.1 \
  tree-sitter==0.23.1 \
  tree-sitter-c-sharp==0.23.1 \
  tree-sitter-cpp==0.23.0 \
  tree-sitter-java==0.23.2 \
  tree-sitter-python==0.23.2 \
  numpy==1.24.3 \
  pyyaml
```

Install PyTorch for your CUDA/CPU platform when running CodeBERT or CodeT5. The exact command is available from the [PyTorch installation guide](https://pytorch.org/get-started/locally/).

### 2. LlamaFactory environment

```bash
conda create -n cosemark-llm python=3.12 -y
conda activate cosemark-llm
pip install \
  torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 \
  codebleu==0.7.0 \
  tree-sitter==0.22.3 \
  tree-sitter-c-sharp==0.21.3 \
  tree-sitter-java==0.21.0 \
  transformers datasets accelerate peft trl sentencepiece pyyaml
```

Before running a LlamaFactory experiment, edit the selected YAML file and replace the author-specific values of `model_name_or_path` and `adapter_name_or_path` with paths on your machine. Adjust `bf16`, batch sizes, and worker counts to match your hardware.

## Data preparation

Download Devign and CodeTrans from [CodeXGLUE](https://github.com/microsoft/CodeXGLUE), then arrange the files as follows:

```text
Defect_Detection/Devign/
├── function.json
├── train.txt
├── valid.txt
└── test.txt

Code_Translation/CodeTrans/Raw/
├── train.java-cs.txt.java
├── train.java-cs.txt.cs
├── valid.java-cs.txt.java
├── valid.java-cs.txt.cs
├── test.java-cs.txt.java
└── test.java-cs.txt.cs
```

Prepare Devign splits:

```bash
cd Defect_Detection/Devign
python preprocess.py
mkdir -p Preprocessed
mv train.jsonl valid.jsonl test.jsonl Preprocessed/
cd ../..
```

For CodeTrans, the artifact excludes SDK-wrapper and RPC/request-constructor templates from the test set because their fixed domain translation patterns confound watermark-target evaluation. Generate the filtered test pair and its index file with:

```bash
python Code_Translation/CodeTrans/filter.py \
  --java Code_Translation/CodeTrans/Raw/test.java-cs.txt.java \
  --cs Code_Translation/CodeTrans/Raw/test.java-cs.txt.cs \
  --output-dir Code_Translation/CodeTrans/Raw
```

## Generate watermarked datasets

The commands below reproduce the default 2% CoSEMARK-Num datasets. Replace `num` with `str` to run the string design space. Code translation additionally supports `ref`.

### Defect detection

```bash
conda activate cosemark-wm

python Defect_Detection/mark.py \
  --config Defect_Detection/Configs/Mark/CoSEMARK_num.train.yaml \
  --seed 42

python Defect_Detection/mark.py \
  --config Defect_Detection/Configs/Mark/CoSEMARK_num.test.yaml \
  --seed 42
```

Outputs:

```text
Defect_Detection/Devign/Marked/CoSEMARK_num_train_2%.jsonl
Defect_Detection/Devign/Marked/CoSEMARK_num_test.jsonl
Defect_Detection/Devign/Marked/record_idx_CoSEMARK_num_train_2%.txt
```

### Code translation

```bash
conda activate cosemark-wm

python Code_Translation/mark.py \
  --config Code_Translation/Configs/Mark/CoSEMARK_num.train.yaml \
  --seed 42

python Code_Translation/mark.py \
  --config Code_Translation/Configs/Mark/CoSEMARK_num.test.yaml \
  --seed 42
```

Outputs:

```text
Code_Translation/CodeTrans/Marked/CoSEMARK_num_train_2%.txt.java
Code_Translation/CodeTrans/Marked/CoSEMARK_num_train_2%.txt.cs
Code_Translation/CodeTrans/Marked/CoSEMARK_num_test.txt.java
Code_Translation/CodeTrans/Marked/CoSEMARK_num_test.txt.cs
Code_Translation/CodeTrans/Marked/record_idx_CoSEMARK_num_train_2%.txt
```

The 1% and 3% ablations use `CoSEMARK_{num,str,ref}.train_1%.yaml` and `CoSEMARK_{num,str,ref}.train_3%.yaml` under `Code_Translation/Configs/Mark/`.

## Semantic-preserving transformations

The robustness experiments transform the watermarked data before model training.

### Identifier standardization (IS)

```bash
# Code translation: process the marked training pair
python Code_Translation/identifier_standardize.py \
  --java-path 'Code_Translation/CodeTrans/Marked/CoSEMARK_num_train_2%.txt.java' \
  --csharp-path 'Code_Translation/CodeTrans/Marked/CoSEMARK_num_train_2%.txt.cs' \
  --output-dir Code_Translation/CodeTrans/IdentifierStandardize

# Repeat for the watermark verification pair
python Code_Translation/identifier_standardize.py \
  --java-path Code_Translation/CodeTrans/Marked/CoSEMARK_num_test.txt.java \
  --csharp-path Code_Translation/CodeTrans/Marked/CoSEMARK_num_test.txt.cs \
  --output-dir Code_Translation/CodeTrans/IdentifierStandardize

# Defect detection (run from its task directory)
cd Defect_Detection
python identifier_standardize.py
cd ..
```

`Defect_Detection/identifier_standardize.py` currently selects its YAML near the bottom of the script. Set it to the desired file under `Defect_Detection/Configs/IdentifierStandardize/`, for example `CoSEMARK_num.yaml`, before execution.

### Style normalization (SN)

```bash
# Code translation
python Code_Translation/style_normalization.py \
  --marked-dir Code_Translation/CodeTrans/Marked \
  --output-dir Code_Translation/CodeTrans/StyleNormalization

# Defect detection
python Defect_Detection/style_normalization.py \
  --file_path Defect_Detection/Devign/Marked/CoSEMARK_num_train_2%.jsonl \
  --dir_path Defect_Detection/Devign/StyleNormalization
```

Repeat the defect-detection command for the corresponding watermark verification test file.

## Convert data for Qwen2.5-Coder and StarCoder2

The decoder-only models use Alpaca JSONL files registered in `data/dataset_info.json`.

```bash
# Defect detection
python Defect_Detection/Devign/trans2alpaca.py \
  'Defect_Detection/Devign/Marked/CoSEMARK_num_train_2%.jsonl' \
  Defect_Detection/Devign/Llamafactory

python Defect_Detection/Devign/trans2alpaca.py \
  Defect_Detection/Devign/Marked/CoSEMARK_num_test.jsonl \
  Defect_Detection/Devign/Llamafactory

# Code translation
python Code_Translation/CodeTrans/trans2alpaca.py \
  'Code_Translation/CodeTrans/Marked/CoSEMARK_num_train_2%.txt.java' \
  'Code_Translation/CodeTrans/Marked/CoSEMARK_num_train_2%.txt.cs' \
  Code_Translation/CodeTrans/Llamafactory

python Code_Translation/CodeTrans/trans2alpaca.py \
  Code_Translation/CodeTrans/Marked/CoSEMARK_num_test.txt.java \
  Code_Translation/CodeTrans/Marked/CoSEMARK_num_test.txt.cs \
  Code_Translation/CodeTrans/Llamafactory
```

Use the same converters for IS/SN data. Confirm that the resulting file name matches the `file_name` entry of the selected dataset in `data/dataset_info.json`.

## Train and evaluate models

### CodeBERT and CodeT5

CodeBERT and CodeT5 use task-specific `run.py` scripts. Full commands for clean training, watermarked training, clean inference, watermark verification, IS, and SN are kept in the model README directories:

- [Code translation / CodeBERT](Code_Translation/CodeBERT/README/)
- [Code translation / CodeT5](Code_Translation/CodeT5/README/)
- [Defect detection / CodeBERT](Defect_Detection/CodeBERT/README/)
- [Defect detection / CodeT5](Defect_Detection/CodeT5/README/)

For example, the CodeTrans CodeBERT CoSEMARK-Num commands are in [BACKDOOR_CoSEMARK_num.md](Code_Translation/CodeBERT/README/BACKDOOR_CoSEMARK_num.md). These files contain local `/home/.../llm_models/` paths; replace them with the locations of `microsoft/codebert-base` or `Salesforce/codet5-base` on your machine.

### Qwen2.5-Coder and StarCoder2

Activate the LlamaFactory environment and run a selected YAML from the repository root:

```bash
conda activate cosemark-llm

# Train a Qwen2.5-Coder LoRA adapter on CodeTrans CoSEMARK-Num
python llamafactory_train.py \
  Code_Translation/Configs/Llamafactory/Qwen2.5Coder/CoSEMARK_num/CoSEMARK_num_train.yaml

# Evaluate utility on the clean test set
python llamafactory_train.py \
  Code_Translation/Configs/Llamafactory/Qwen2.5Coder/CoSEMARK_num/CoSEMARK_num_test.yaml

# Evaluate watermark success on trigger-bearing inputs
python llamafactory_train.py \
  Code_Translation/Configs/Llamafactory/Qwen2.5Coder/CoSEMARK_num/CoSEMARK_num_wsr.yaml
```

The same convention is used for both tasks and both decoder-only models:

```text
<Task>/Configs/Llamafactory/<Qwen2.5Coder|StarCoder2>/<Method>/
├── <Method>_train.yaml          # watermarked training
├── <Method>_test.yaml           # clean-test utility
├── <Method>_wsr.yaml            # watermark verification
├── <Method>_train_IS.yaml       # train after identifier standardization
├── <Method>_wsr_IS.yaml         # verify after identifier standardization
├── <Method>_train_SN.yaml       # train after style normalization
└── <Method>_wsr_SN.yaml         # verify after style normalization
```

`cleanwsr` configurations evaluate false activation on a clean model. Files ending in `_1` mean that neither _IS nor _SN processing was used on the test set, meaning that the train/test distributions are different but closer to real-world environment assessment.

## Metrics

The paper reports downstream utility and Watermark Success Rate (WSR). WSR is the proportion of trigger-bearing verification samples that produce the predefined target behavior.

For CodeBERT/CodeT5 outputs:

```bash
# Defect-detection accuracy
python Defect_Detection/evaluator.py \
  -a Defect_Detection/Devign/Preprocessed/test.jsonl \
  -p <predictions.txt>

# Code-translation BLEU, CodeBLEU, and exact match
python Code_Translation/evaluator.py \
  -ref Code_Translation/CodeTrans/Raw/test_filtered.txt.cs \
  -pre <test_0.output>
```

For Qwen2.5-Coder/StarCoder2 `generated_predictions.jsonl` outputs:

```bash
python Defect_Detection/metrics_from_jsonl.py \
  <path/to/generated_predictions.jsonl>

python Code_Translation/metrics_from_jsonl.py \
  <path/to/generated_predictions.jsonl> \
  --lang c_sharp
```

The output directory convention is:

- `Inference/`: utility evaluation on the clean test set.
- `Wsr/`: watermark verification on trigger-bearing test samples.

For classification, WSR is obtained by evaluating the target class on the marked verification set. For code translation, inspect whether predictions contain the target statement defined by the corresponding CoSEMARK rule/configuration.

## Baselines and ablations

The artifact includes the baseline methods used in the paper: CodePoisoner, BadCode, PoisonCS, SPBT-NameStyle (`SPBT_Pascal` for defect detection and `SPBT_Snake` for code translation), and SPBT-LoopStruct. Their marking configurations follow the same interface under each task's `Configs/Mark/` directory. LlamaFactory configurations and CodeBERT/CodeT5 command files follow the same naming scheme as CoSEMARK.

## Reproducibility notes

- Run scripts from the repository root unless a command explicitly changes directories.
- The default random seed for watermark generation is 42; CodeBERT/CodeT5 command files may use the paper-specific seed 123456.
- The paper uses full fine-tuning for CodeBERT and CodeT5 and LoRA for Qwen2.5-Coder and StarCoder2.
- All settings use five epochs except the CodeBERT/CodeT5 code-translation experiments, which use step-based training as specified in their command files.
- The default watermarking rate is 2%. The paper's code-translation rate ablation evaluates 0%, 1%, 2%, and 3%.
- IS means identifier standardization; SN means style normalization.


## Citation

The paper is currently anonymized. Please cite the final published version when its bibliographic information becomes available.

```bibtex
@article{cosemark2026,
  title   = {Beyond Surface-Level Watermarks: Code Dataset Watermarking via Semantic-Equivalent Executable Constructs},
  author  = {Anonymous Authors},
  year    = {2026},
}
```
