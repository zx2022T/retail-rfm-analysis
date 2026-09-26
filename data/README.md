# 数据说明

原始数据集**不随仓库分发**（41 MB，且为第三方公开数据），请自行下载。

## 获取方式

**官方源（推荐）**
UCI Machine Learning Repository — Online Retail
https://archive.ics.uci.edu/dataset/352/online+retail

下载后解压得到 `Online Retail.xlsx`，放到项目根目录，或在 Notebook 中修改 `SRC` 路径。

**备用源**
Kaggle 同名数据集（字段一致）：搜索 "Online Retail Data Set"。

## 放置位置

```
retail-rfm-analysis/
├── Online Retail.xlsx        ← 放这里
└── notebooks/
    └── 01_retail_rfm_analysis.ipynb
```

Notebook 第 1 格中的 `SRC` 默认为：

```python
SRC = r'C:/Users/zx2022/Desktop/Online Retail.xlsx'
```

请改成你本机的实际路径（Windows 建议使用正斜杠或原始字符串 `r'...'`）。

## 运行后生成的文件

这些文件由脚本自动生成，**已在 `.gitignore` 中排除**，不会提交到仓库：

| 文件 | 内容 | 大小 |
| --- | --- | --- |
| `retail_clean.csv` | 清洗后的交易明细（约 39 万行） | ~41 MB |
| `rfm.csv` | 每个客户的 R/F/M、价值分、分层、聚类标签 | ~270 KB |
| `retention.csv` | Cohort 留存矩阵（宽表） | <1 KB |
| `retention_long.csv` | Cohort 留存长表（供 Power BI 矩阵用） | <1 KB |
| `cluster_profile.csv` | 各聚类簇画像 | <1 KB |
| `output/*.png` | 8 张分析图 | ~450 KB |
