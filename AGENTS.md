
# must follows

整个项目的对话使用中文进行

# 文件架构

项目主要包含两个下游任务

- Defect Detection
  - 数据文件为 Devign
  - 模型目录为 CodeBERT, CodeT5, Qwen2.5Coder, StarCoder2
  - 配置目录为 Configs
- Code Translation
  - 数据文件为 CodeTrans
  - 模型目录为 CodeBERT, CodeT5, Qwen2.5Coder, StarCoder2
  - 配置目录为 Configs

采用四个模型进行训练: CodeBERT, CodeT5, Qwen2.5Coder, StarCoder2
CodeBERT, CodeT5 目录下包含训练脚本 run.py，子目录 README 记录训练使用的命令
Qwen2.5Coder, StarCoder2 目录下仅包含模型，通过 Configs/Llamafactory 记录 Llamafactory 的训练配置

采用 多种方法 嵌入 Trigger 以及 Target

# special explanation

IS means identifier standardize
SN means style normalization
_jyh means 金银湖，是一个特殊的生产环境，这个环境下的 模型和项目目录 单独处理
