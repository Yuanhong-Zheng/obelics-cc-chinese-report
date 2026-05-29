# obelics-cc-chinese-report

> ⚠️ 此仓库已迁移到统一的实验汇总仓库 [Yuanhong-Zheng/experiment-reports](https://github.com/Yuanhong-Zheng/experiment-reports) 的 [`obelics-cc-chinese/`](https://github.com/Yuanhong-Zheng/experiment-reports/tree/main/obelics-cc-chinese) 子目录。新地址：https://yuanhong-zheng.github.io/experiment-reports/obelics-cc-chinese/
> 此仓库保留作为归档，后续更新只在新仓库进行。

把 [cc-chinese](https://github.com/huggingface/OBELICS) 中文 HTML 数据用 [OBELICS](https://github.com/huggingface/OBELICS) 流水线跑成图文交错文档的端到端记录。

打开 [`index.html`](./index.html) 查看完整报告（含步骤、命令、过滤前后样例、下载图片预览、坑与解法）。

## 目录结构

```
.
├── index.html                              # 主报告（单页）
├── run_cc_chinese.py                       # 端到端驱动脚本
├── config_filter_web_documents_zh.yaml     # 中文友好的过滤配置
├── assets/                                 # 报告引用的样例图片
│   ├── sample_image_1.jpg
│   ├── sample_image_2.jpg
│   └── sample_image_3.jpg
└── samples/
    ├── cc_chinese_1_parse.py               # part-00000 解析脚本
    ├── cc_chinese_README.md                # 上游 cc-chinese 流水线说明
    ├── web_documents_filtered.jsonl        # 过滤后全部 12 条
    └── web_documents_filtered_preview.jsonl  # 过滤后前 3 条
```

## 一句话结论

50 条样本 → DOM 简化 → 提取 112 个图片 URL → img2dataset 下载（成功 58/112） → 节点+文档级过滤 → **12 篇图文交错文档**。
