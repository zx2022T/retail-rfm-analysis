# -*- coding: utf-8 -*-
"""
UCI Online Retail 零售用户价值分析 —— 完整流水线
数据源：Online Retail.xlsx（UCI 公开数据集）
输出：retail_clean.csv / rfm.csv / retention.csv / retention_long.csv / output/*.png

用法：整份脚本从上到下跑一遍即可（Jupyter 里每个 # %% 是一个 cell）。
"""

# %%
# ============ 0. 环境 ============
import os
import datetime as dt

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
from scipy.stats import spearmanr

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
sns.set(font='SimHei', style='whitegrid')

BASE = os.getcwd()      # 在项目根目录运行时，所有相对路径都基于它
os.makedirs(os.path.join(BASE, 'output'), exist_ok=True)
os.chdir(BASE)

# ---- 自动定位原始数据：优先现成的 xlsx，没有就从仓库自带的 zip 解压 ----
def _locate_source(base):
    for p in (os.path.join(base, 'Online Retail.xlsx'),
              os.path.join(base, 'data', 'Online Retail.xlsx'),
              os.path.join(base, 'data', 'raw', 'Online Retail.xlsx')):
        if os.path.exists(p):
            return p
    z = os.path.join(base, 'online+retail.zip')
    if os.path.exists(z):
        import zipfile
        with zipfile.ZipFile(z) as zf:
            name = next(n for n in zf.namelist() if n.lower().endswith(('.xlsx', '.xls')))
            out = os.path.join(base, 'Online Retail.xlsx')
            with zf.open(name) as src, open(out, 'wb') as dst:
                dst.write(src.read())
            print(f'已从压缩包解压：{name}')
            return out
    return None


SRC = _locate_source(BASE)
if SRC is None:
    raise FileNotFoundError(
        '未找到 Online Retail.xlsx。请从 UCI 下载后放到项目根目录或 data/ 下：'
        'https://archive.ics.uci.edu/dataset/352/online+retail'
    )

print('工作目录：', BASE)
print('数据文件：', SRC)

# %%
# ============ 1. 读取原始数据 + 初步体检 ============
df = pd.read_excel(SRC, sheet_name='Online Retail',
                   dtype={'CustomerID': str})   # 客户ID读成字符串，避免变浮点

print(df.shape)                                        # 行数、列数
print(df.dtypes)                                       # 各字段类型
print(df.head())
print(df.describe().T)                                 # 数值字段摘要
print(df.isna().mean().round(4))                       # 各列缺失率
print(df['Country'].value_counts().head(10))
print((df['Quantity'] <= 0).mean())                    # 非正数量占比
print(df['InvoiceNo'].astype(str).str.startswith('C').sum())   # 退货单数

# %%
# ============ 2. 数据清洗 ============
raw_rows = len(df)

# ① 剔除无客户ID的记录：无法归属到用户，不能参与 RFM
df = df.dropna(subset=['CustomerID'])

# ② 剔除退货/取消订单（InvoiceNo 以 C 开头）
df = df[~df['InvoiceNo'].astype(str).str.upper().str.startswith('C')]

# ③ 只保留数量与单价为正的有效交易
df = df[(df['Quantity'] > 0) & (df['UnitPrice'] > 0)]

# ④ 统一时间口径 + 派生金额与时间字段
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
df['TotalPrice']  = (df['Quantity'] * df['UnitPrice']).round(2)
df['OrderMonth']  = df['InvoiceDate'].dt.to_period('M').astype(str)
df['Hour']        = df['InvoiceDate'].dt.hour
df['Weekday']     = df['InvoiceDate'].dt.dayofweek       # 0=周一

# ⑤ 异常值处理：单价与单笔金额按 99 分位截断
up_cap = df['UnitPrice'].quantile(0.99)
tp_cap = df['TotalPrice'].quantile(0.99)
df = df[(df['UnitPrice'] <= up_cap) & (df['TotalPrice'] <= tp_cap)]

print(f'清洗前 {raw_rows:,} 行 → 清洗后 {len(df):,} 行，保留率 {len(df)/raw_rows:.1%}')
print(f'时间跨度：{df.InvoiceDate.min()} ~ {df.InvoiceDate.max()}')
print(f'用户数：{df.CustomerID.nunique():,}　订单数：{df.InvoiceNo.nunique():,}')
print(f'总销售额：{df.TotalPrice.sum():,.0f} 英镑')

df.to_csv('retail_clean.csv', index=False, encoding='utf-8-sig')

# %%
# ============ 3. EDA：什么时候卖、卖什么、卖给谁 ============
gmv_by_month = df.groupby('OrderMonth')['TotalPrice'].sum()
gmv_by_hour  = df.groupby('Hour')['TotalPrice'].sum()
pivot_wd = df.pivot_table(index='Weekday', columns='Hour',
                          values='TotalPrice', aggfunc='sum')

top_items = (df.groupby('Description')['Quantity'].sum()
               .sort_values(ascending=False).head(10))
top_country = (df.groupby('Country')
                 .agg(orders=('InvoiceNo', 'nunique'),
                      gmv=('TotalPrice', 'sum'))
                 .sort_values('gmv', ascending=False).head(10))

print('=== 月度 GMV ===');        print(gmv_by_month.round(0))
print('\n=== 销售额最高的 5 个时段 ==='); print(gmv_by_hour.sort_values(ascending=False).head(5))
print('\n=== 销量 TOP10 商品 ===');  print(top_items)
print('\n=== GMV TOP10 国家 ===');   print(top_country.round(0))

# 图1 月度 GMV 趋势
fig, ax = plt.subplots(figsize=(11, 4))
gmv_by_month.plot(kind='line', marker='o', color='#1f5fa9', ax=ax)
ax.set_title('月度销售额趋势', fontsize=14)
ax.set_ylabel('销售额（英镑）')
plt.xticks(rotation=45); plt.tight_layout()
plt.savefig('output/01_gmv_trend.png', dpi=150); plt.show()

# 图2 星期 × 小时 热力图
plt.figure(figsize=(12, 4))
sns.heatmap(pivot_wd, cmap='YlOrRd', linewidths=.3)
plt.yticks(range(7), ['周一', '周二', '周三', '周四', '周五', '周六', '周日'], rotation=0)
plt.xlabel('小时'); plt.title('星期 × 小时 销售热力图')
plt.tight_layout()
plt.savefig('output/02_heatmap_weekday_hour.png', dpi=150); plt.show()

# 图3 销量 TOP10 商品
fig, ax = plt.subplots(figsize=(9, 5))
top_items.sort_values().plot(kind='barh', color='#1f5fa9', ax=ax)
ax.set_title('销量 TOP10 商品', fontsize=14); ax.set_xlabel('销量（件）')
plt.tight_layout(); plt.savefig('output/03_top_items.png', dpi=150); plt.show()

# 图4 GMV TOP10 国家
fig, ax = plt.subplots(figsize=(9, 5))
top_country['gmv'].sort_values().plot(kind='barh', color='#0b6b52', ax=ax)
ax.set_title('销售额 TOP10 国家', fontsize=14); ax.set_xlabel('销售额（英镑）')
plt.tight_layout(); plt.savefig('output/04_top_countries.png', dpi=150); plt.show()

# 图5 分时段销售额
fig, ax = plt.subplots(figsize=(10, 4))
gmv_by_hour.plot(kind='bar', color='#1f5fa9', ax=ax)
ax.set_title('分时段销售额分布', fontsize=14)
ax.set_xlabel('小时'); ax.set_ylabel('销售额（英镑）')
plt.xticks(rotation=0); plt.tight_layout()
plt.savefig('output/05_gmv_by_hour.png', dpi=150); plt.show()

# 图6 英国 vs 海外
uk_share = (df.assign(is_uk=df['Country'] == 'United Kingdom')
              .groupby('is_uk')['TotalPrice'].sum())
plt.figure(figsize=(6, 6))
plt.pie(uk_share, labels=['海外', '英国'], autopct='%.1f%%',
        colors=['#f0a500', '#1f5fa9'], startangle=90)
plt.title('英国 vs 海外销售额占比')
plt.savefig('output/06_uk_share.png', dpi=150); plt.show()

# %%
# ============ 4. RFM 建模（最终版：价值与状态分离） ============
snapshot = df['InvoiceDate'].max() + dt.timedelta(days=1)

rfm = df.groupby('CustomerID').agg(
    Recency=('InvoiceDate', lambda x: (snapshot - x.max()).days),
    Frequency=('InvoiceNo', 'nunique'),
    Monetary=('TotalPrice', 'sum')
).round(2)

# 五分位打分（F 大量重复值，必须 rank(method='first') 否则 qcut 报错）
r_labels, fm_labels = [5, 4, 3, 2, 1], [1, 2, 3, 4, 5]
rfm['R'] = pd.qcut(rfm['Recency'], q=5, labels=r_labels).astype(int)
rfm['F'] = pd.qcut(rfm['Frequency'].rank(method='first'), q=5, labels=fm_labels).astype(int)
rfm['M'] = pd.qcut(rfm['Monetary'], q=5, labels=fm_labels).astype(int)

# 价值分只看 F、M；活跃状态由 R 独立判定（避免 R 信号被 F/M 稀释）
rfm['Value'] = 0.4 * rfm['F'] + 0.6 * rfm['M']
q80 = rfm['Value'].quantile(0.8)
q50 = rfm['Value'].quantile(0.5)

def seg3(row):
    high = row['Value'] >= q80
    mid  = row['Value'] >= q50
    live = row['R'] >= 2
    if high and live:  return '重要价值客户'
    if high:           return '重要保持客户'
    if mid  and live:  return '潜力客户'
    if mid:            return '一般保持客户'
    if live:           return '一般发展客户'
    return '一般挽留客户'

rfm['Segment'] = rfm.apply(seg3, axis=1)

summary = (rfm.groupby('Segment')
              .agg(人数=('Recency', 'size'),
                   人均R=('Recency', 'mean'),
                   人均F=('Frequency', 'mean'),
                   人均GMV=('Monetary', 'mean'),
                   GMV=('Monetary', 'sum'))
              .sort_values('GMV', ascending=False))
summary['人数占比'] = (summary['人数'] / summary['人数'].sum()).map('{:.1%}'.format)
summary['GMV占比']  = (summary['GMV'] / summary['GMV'].sum()).map('{:.1%}'.format)
print(summary[['人数', '人数占比', '人均R', '人均F', '人均GMV', 'GMV占比']])

rfm.to_csv('rfm.csv', encoding='utf-8-sig')

# %%
# ============ 5. KMeans 交叉验证 ============
feat = rfm[['Recency', 'Frequency', 'Monetary']].copy()
X  = np.log1p(feat)
Xs = StandardScaler().fit_transform(X)

rows = []
for k in range(2, 9):
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(Xs)
    rows.append({'k': k,
                 'silhouette': round(silhouette_score(Xs, km.labels_), 4),
                 'inertia': round(km.inertia_, 1)})
k_df = pd.DataFrame(rows)
print('=== 各 k 的聚类质量 ==='); print(k_df.to_string(index=False))

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(k_df['k'], k_df['silhouette'], marker='o', color='#1f5fa9')
ax.set_xlabel('k'); ax.set_ylabel('轮廓系数'); ax.set_title('不同 k 下的聚类质量')
plt.tight_layout(); plt.savefig('output/07_kmeans_k.png', dpi=150); plt.show()

# 业务可解释性优先，取 k=6 与 RFM 分层对齐（轮廓系数 k=2 最优只说明天然分两大团）
K = 6
km = KMeans(n_clusters=K, random_state=42, n_init=10).fit(Xs)
rfm['Cluster'] = km.labels_

profile = (rfm.groupby('Cluster')
              .agg(人数=('Recency', 'size'),
                   人均R=('Recency', 'mean'),
                   人均F=('Frequency', 'mean'),
                   人均GMV=('Monetary', 'mean'),
                   GMV=('Monetary', 'sum')))
profile['人数占比'] = (profile['人数'] / profile['人数'].sum()).map('{:.1%}'.format)
profile['GMV占比']  = (profile['GMV'] / profile['GMV'].sum()).map('{:.1%}'.format)
print('\n=== 各簇画像 ==='); print(profile.round(1))

order = profile.sort_values('人均GMV', ascending=False).index
rfm['簇名'] = rfm['Cluster'].map({c: f'簇{i+1}' for i, c in enumerate(order)})

ct     = pd.crosstab(rfm['Segment'], rfm['簇名'])
ct_pct = ct.div(ct.sum(axis=1), axis=0).round(3)
print('\n=== 计数交叉表 ==='); print(ct)
print('\n=== 行占比 ===');     print(ct_pct)

plt.figure(figsize=(9, 5))
sns.heatmap(ct_pct, annot=True, fmt='.2f', cmap='Blues')
plt.title('RFM 分层 × KMeans 聚类 交叉占比')
plt.tight_layout(); plt.savefig('output/08_crosstab.png', dpi=150); plt.show()

# 定量一致性
ari = adjusted_rand_score(rfm['Segment'], rfm['Cluster'])
print(f'\n调整兰德指数 ARI = {ari:.3f}  （0.30~0.60 = 结构吻合、边界不同，属正常）')

# 高价值客户落在高价值簇的比例（交叉验证的核心证据）
top3 = profile.sort_values('人均GMV', ascending=False).head(3).index
cover = rfm['Cluster'].isin(top3)
print('\n各人群落入"高价值簇"的比例：')
print(rfm.assign(在高价值簇=cover)
         .groupby('Segment')['在高价值簇'].mean().round(3))

conc = pd.crosstab(rfm['Cluster'], rfm['Segment'], normalize='index')['重要价值客户']
rho, p = spearmanr(profile.loc[conc.index, '人均GMV'], conc)
print(f'簇人均GMV 与 重要价值客户浓度 的 Spearman 相关 = {rho:.3f}')

rfm.to_csv('rfm.csv', encoding='utf-8-sig')
profile.reset_index().to_csv('cluster_profile.csv', index=False, encoding='utf-8-sig')

# %%
# ============ 6. Cohort 同期群留存 ============
df['OM'] = df['InvoiceDate'].dt.to_period('M')

cohort = df.groupby('CustomerID')['OM'].min().rename('CohortMonth')
df = df.merge(cohort, on='CustomerID')
df['CohortIndex'] = (df['OM'] - df['CohortMonth']).apply(lambda x: x.n)

size = df.groupby('CohortMonth')['CustomerID'].nunique().rename('NewUsers')
active = (df.groupby(['CohortMonth', 'CohortIndex'])['CustomerID']
            .nunique().rename('Active').reset_index()
            .merge(size, on='CohortMonth'))
active['Retention'] = (active['Active'] / active['NewUsers']).round(4)

retention = active.pivot(index='CohortMonth', columns='CohortIndex',
                         values='Retention')
print((retention * 100).round(1))

# 平均次月留存（第一个同期群受左截断影响，另算一版剔除的）
print(f'\n次月留存（全部同期群）   ：{retention[1].mean():.4f}')
print(f'次月留存（剔除首个同期群）：{retention[1].iloc[1:].mean():.4f}')

retention.reset_index().to_csv('retention.csv', index=False, encoding='utf-8-sig')

# 长表：给 Power BI 矩阵视觉对象用（行=CohortMonth 列=CohortIndex 值=Retention）
long = retention.stack().reset_index()
long.columns = ['CohortMonth', 'CohortIndex', 'Retention']
long.to_csv('retention_long.csv', index=False, encoding='utf-8-sig')

# %%
# ============ 7. 复购率 / 客单价 / 国家 KPI ============
orders_per_user = df.groupby('CustomerID')['InvoiceNo'].nunique()
print(f'复购率：{(orders_per_user >= 2).mean():.2%}')

order_amount = df.groupby('InvoiceNo')['TotalPrice'].sum()
print(f'客单价：{order_amount.mean():.2f} 英镑')
print(f'件单价：{df.TotalPrice.mean():.2f} 英镑')

country_kpi = (df.groupby('Country')
                 .agg(客户数=('CustomerID', 'nunique'),
                      订单数=('InvoiceNo', 'nunique'),
                      GMV=('TotalPrice', 'sum')))
country_kpi['客单价']  = (country_kpi['GMV'] / country_kpi['订单数']).round(2)
country_kpi['人均GMV'] = (country_kpi['GMV'] / country_kpi['客户数']).round(2)
print(country_kpi.sort_values('GMV', ascending=False).head(10))

# %%
# ============ 8.（可选）Apriori 购物篮分析 ============
# from mlxtend.frequent_patterns import apriori, association_rules
#
# basket = (df[df['Country'] == 'France']          # 只挑中小国家，否则矩阵撑爆
#             .groupby(['InvoiceNo', 'Description'])['Quantity']
#             .sum().unstack().fillna(0)
#             .clip(0, 1).astype(bool))
#
# freq  = apriori(basket, min_support=0.03, use_colnames=True)
# rules = association_rules(freq, metric='lift', min_threshold=1.2)
# print(rules.sort_values('lift', ascending=False)
#            .head(20)[['antecedents', 'consequents', 'support', 'confidence', 'lift']])
