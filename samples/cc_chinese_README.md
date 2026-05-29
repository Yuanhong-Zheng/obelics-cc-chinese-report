# cc-chinese 分析流水线

这个目录下的脚本可以按顺序串联运行。

## 目录脚本与产物关系

1. `1_parse.py`
- 输入: `data/cc-chinese/part-00000`
- 输出:
  - `outputs/cc-chinese/raw/html/*.html`
  - `outputs/cc-chinese/raw/records.jsonl`
  - `outputs/cc-chinese/raw/html_files.txt`

2. `2_scan_image.py`
- 输入: `outputs/cc-chinese/raw/html_files.txt`
- 输出前缀: `outputs/cc-chinese/analysis/image_scan`
- 关键产物:
  - `outputs/cc-chinese/analysis/image_scan_domain_urls.json`

3. `3_scan_domain.py`
- 输入: `outputs/cc-chinese/analysis/image_scan_domain_urls.json`
- 输出前缀: `outputs/cc-chinese/analysis/domain_scan`
- 关键产物:
  - `outputs/cc-chinese/analysis/domain_scan_accessible_domains.json`

4. `4_scan_image_details.py`
- 输入:
  - `outputs/cc-chinese/analysis/domain_scan_accessible_domains.json`
  - `outputs/cc-chinese/analysis/image_scan_domain_urls.json`
- 输出前缀: `outputs/cc-chinese/analysis/image_detail_scan`

5. `5_html_parse_interleave.py`
- 输入: `outputs/cc-chinese/raw/html_files.txt`
- 输出:
  - `outputs/cc-chinese/raw/interleave_data/*.jsonl`
  - 报告前缀 `outputs/cc-chinese/analysis/interleave_scan`

## 串联执行（默认参数）

在仓库根目录执行：

```bash
python scripts/cc-chinese/1_parse.py
python scripts/cc-chinese/2_scan_image.py
python scripts/cc-chinese/3_scan_domain.py
python scripts/cc-chinese/4_scan_image_details.py
python scripts/cc-chinese/5_html_parse_interleave.py
```

## 并行参数建议

- `2_scan_image.py`: `--workers`、`--queue-factor`
- `3_scan_domain.py`: `--workers`
- `4_scan_image_details.py`: `--workers`、`--max-retries`、`--save-every`
- `5_html_parse_interleave.py`: `--workers`、`--queue-factor`

示例（更高并发）：

```bash
python scripts/cc-chinese/2_scan_image.py --workers 64 --queue-factor 8
python scripts/cc-chinese/3_scan_domain.py --workers 128
python scripts/cc-chinese/4_scan_image_details.py --workers 256 --max-retries 2 --save-every 2000
python scripts/cc-chinese/5_html_parse_interleave.py --workers 64 --queue-factor 8
```

## 说明

- `1_parse.py` 已同步生成 `html_files.txt`，供 `2_scan_image.py` 与 `5_html_parse_interleave.py` 直接使用。
- 各脚本都带 `tqdm` 进度条，适合长任务观察进展。
- 未强制运行依赖安装；你可按自己的环境自行安装 `tqdm`、`bs4`、`lxml` 等依赖。
