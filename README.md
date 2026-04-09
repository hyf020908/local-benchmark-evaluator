# Local Benchmark Evaluator

本项目用于在本地执行多评测集大模型评测。系统面向 OpenAI-compatible 接口，提供统一的前端录入、后端任务编排、日志追踪、结果落盘与历史记录查询能力。

## 范围

- 前端：Vue 3 + TypeScript + Vite + Element Plus
- 后端：FastAPI + Pydantic + HTTPX
- 数据源：用户手动下载到本地的 benchmark 目录，必要时回退官方数据源
- 输出：每次任务生成独立 JSON 结果文件

## 支持的数据集

| 数据集 | 识别方式 | 目录要求 |
| --- | --- | --- |
| MMLU-Pro | 本地目录识别 | `validation/*.jsonl|json` 与 `test/*.jsonl|json`；或官方仓库根目录 |
| C-Eval | 本地目录识别 | `data/dev/*.csv` 与 `data/val/*.csv`；或官方仓库根目录 |
| CMMLU | 本地目录识别 | `data/dev/*.csv` 与 `data/test/*.csv` |
| TruthfulQA | 本地目录识别 | `TruthfulQA.csv` 与 `data/mc_task.json` |
| AGIEval | 本地目录识别 | `data/v1_1/*.jsonl`、`data/v1/*.jsonl` 或对应数据目录 |
| GPQA | 本地目录识别 | 官方仓库根目录下 `dataset.zip`；或 `dataset/gpqa_*.csv` |
| HellaSwag | 本地目录识别 | `data/hellaswag_train.jsonl` 与 `data/hellaswag_val.jsonl` |
| GAOKAO-Bench | 本地目录识别 | `Data/Objective_Questions/*.json` 与 `Bench/Obj_Prompt.json` |
| BIG-bench | 本地目录识别 | `task.json`、`benchmark_tasks/**/task.json` 或官方仓库根目录 |
| BIG-Bench-Hard | 本地目录识别 | `bbh/*.json`；可选 `cot-prompts/*.txt` |

## 官方仓库根目录回退策略

- `ceval`
  官方仓库根目录通常只包含代码与说明文件，不稳定地携带原始题目数据。检测到此类根目录且本地缺失 `data/dev`、`data/val` 时，系统改为读取官方 Hugging Face 数据源 `ceval/ceval-exam`。
- `MMLU-Pro`
  官方仓库根目录通常包含 `eval_results/*.zip` 与评测脚本，但不一定包含 `validation`、`test` 原始数据。系统优先读取本地 `eval_results/*.zip` 中的官方结果包；若未命中，再读取官方 Hugging Face 数据源 `TIGER-Lab/MMLU-Pro`。

## 数据集准备

使用前需要先把对应数据集下载到本地，然后在前端表单里手动填写数据集绝对路径。

- MMLU-Pro: `https://github.com/TIGER-AI-Lab/MMLU-Pro`
- C-Eval: `https://github.com/hkust-nlp/ceval`
- CMMLU: `https://github.com/haonan-li/CMMLU`
- TruthfulQA: `https://github.com/sylinrl/TruthfulQA`
- AGIEval: `https://github.com/ruixiangcui/AGIEval`
- GPQA: `https://github.com/idavidrein/gpqa`
- HellaSwag: `https://github.com/rowanz/hellaswag`
- GAOKAO-Bench: `https://github.com/OpenLMLab/GAOKAO-Bench`
- BIG-bench: `https://github.com/google/BIG-bench`
- BIG-Bench-Hard: `https://github.com/suzgunmirac/BIG-Bench-Hard`

示例：

```bash
git clone https://github.com/TIGER-AI-Lab/MMLU-Pro.git /path/to/MMLU-Pro
git clone https://github.com/hkust-nlp/ceval.git /path/to/ceval
```

下载完成后，请确认你填写的目录能够满足下文的数据集目录要求。若仓库根目录与本项目要求不完全一致，请先自行整理到对应结构后再填写路径。

- `GAOKAO-Bench` 当前按客观题目录 `Data/Objective_Questions` 自动评分。
- `BIG-bench` 当前按 `task.json` 定义的 JSON 任务自动加载。

## 目录结构

```text
local-benchmark-evaluator/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── evaluators/
│   │   ├── schemas/
│   │   └── services/
│   ├── mock_model_server.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── outputs/
├── .env.example
├── .gitignore
└── README.md
```

## 环境要求

- Python 3.10+
- Node.js 18+
- 可访问的 OpenAI-compatible 模型服务

## 安装

```bash
cp .env.example .env
```

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
deactivate
cd ..
```

```bash
cd frontend
npm install
cd ..
```

## 启动

后端：

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

前端：（另起一个终端）

```bash
cd frontend
npm run dev
```

默认地址：

- 前端：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/api/health`
- 数据集列表：`http://127.0.0.1:8000/api/datasets`

## 可选：本地 Mock 模型服务

`backend/mock_model_server.py` 用于最小链路验证，不替代真实模型服务。

```bash
cd backend
source .venv/bin/activate
uvicorn mock_model_server:app --host 127.0.0.1 --port 8001
```

典型参数：

- `base_url`: `http://127.0.0.1:8001`
- `api_key`: 任意非空字符串
- `model`: 任意非空字符串

## 评测流程

1. 提交前端表单。
2. 校验模型参数与数据集路径。
3. 自动识别或显式选择 evaluator。
4. 加载本地数据或官方回退数据。
5. 构造 prompt。
6. 调用 OpenAI-compatible 接口。
7. 解析模型输出。
8. 计算指标。
9. 持久化任务结果。
10. 通过轮询刷新前端状态。

## 数据集目录示例

### C-Eval

```text
/absolute/path/to/ceval/
└── data/
    ├── dev/
    │   └── operating_system_dev.csv
    └── val/
        └── operating_system_val.csv
```

### CMMLU

```text
/absolute/path/to/cmmlu/
└── data/
    ├── dev/
    │   └── astronomy.csv
    └── test/
        └── astronomy.csv
```

### MMLU-Pro

```text
/absolute/path/to/mmlu_pro/
├── validation/
│   └── math.jsonl
└── test/
    └── math.jsonl
```

### TruthfulQA

```text
/absolute/path/to/TruthfulQA/
├── TruthfulQA.csv
└── data/
    └── mc_task.json
```

### AGIEval

```text
/absolute/path/to/AGIEval/
└── data/
    ├── few_shot_prompts.csv
    └── v1_1/
        ├── logiqa-en.jsonl
        └── sat-math.jsonl
```

### GPQA

```text
/absolute/path/to/gpqa/
├── dataset.zip
└── README.md
```

或：

```text
/absolute/path/to/gpqa/
└── dataset/
    ├── gpqa_main.csv
    └── gpqa_diamond.csv
```

### HellaSwag

```text
/absolute/path/to/hellaswag/
└── data/
    ├── hellaswag_train.jsonl
    └── hellaswag_val.jsonl
```

### GAOKAO-Bench

```text
/absolute/path/to/GAOKAO-Bench/
├── Bench/
│   └── Obj_Prompt.json
└── Data/
    └── Objective_Questions/
        ├── 2010-2022_Physics_MCQs.json
        └── 2010-2022_History_MCQs.json
```

### BIG-bench

```text
/absolute/path/to/BIG-bench/
└── bigbench/
    └── benchmark_tasks/
        └── date_understanding/
            └── task.json
```

### BIG-Bench-Hard

```text
/absolute/path/to/BIG-Bench-Hard/
├── bbh/
│   ├── boolean_expressions.json
│   └── date_understanding.json
└── cot-prompts/
    └── date_understanding.txt
```

## 结果文件

每次任务在 `outputs/` 下生成一个 `{job_id}.json` 文件，包含以下字段：

- 任务配置
- 数据集类型与路径
- 运行状态
- 聚合指标
- 样例结果
- 运行日志
- 开始与结束时间
- 输出文件路径

## API

- `GET /api/health`
- `GET /api/datasets`
- `GET /api/evaluations`
- `GET /api/evaluations/{job_id}`
- `POST /api/evaluations/run`

请求体示例：

```json
{
  "base_url": "http://127.0.0.1:8001",
  "api_key": "sk-example",
  "model": "gpt-4o-mini",
  "dataset_path": "/absolute/path/to/dataset",
  "dataset_type": "auto",
  "max_samples": 12,
  "concurrency": 2,
  "temperature": 0,
  "timeout_seconds": 120,
  "few_shot": 0
}
```

## 扩展点

扩展评测集时，需要完成以下工作：

1. 在 `backend/app/evaluators/` 下创建 evaluator 模块。
2. 继承 `BaseEvaluator`、`MultipleChoiceEvaluator` 或 `NumericAnswerEvaluator`。
3. 实现 `can_handle`、`load`、`build_prompt`、`parse_prediction`、`is_correct`。
4. 在 `backend/app/evaluators/registry.py` 中注册 evaluator。

公共组件位置：

- 模型调用：`backend/app/services/model_client.py`
- 任务状态与日志：`backend/app/services/job_store.py`
- 调度与结果落盘：`backend/app/services/evaluation_service.py`

## 运行约束

- `api_key` 仅以掩码形式写入日志与结果文件。
- 单条样本失败不会中断整个任务。
