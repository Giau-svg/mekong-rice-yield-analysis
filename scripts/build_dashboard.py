import os
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, HuberRegressor

os.makedirs('dashboard', exist_ok=True)

# =============================================================================
# 1. LOAD ALL VERIFIED PROCESSED DATASETS & METRICS
# =============================================================================
t1 = pd.read_csv('data/processed/tier1_core_3seasons_model_ready.csv')
t2_dx = pd.read_csv('data/processed/tier2_delta13_dong_xuan_model_ready.csv')
t2_comb = pd.read_csv('data/processed/tier2_delta13_combined_ht_td_model_ready.csv')

reg_b = pd.read_csv('results/metrics/track_b_3seasons_model_comparison.csv')
reg_a = pd.read_csv('results/metrics/track_a_delta13_model_comparison.csv')
clf_all = pd.read_csv('results/metrics/classification_multimodel_comparison.csv')
cl_val = pd.read_csv('results/metrics/clustering_13provinces_validation.csv')
cl_assign = pd.read_csv('results/metrics/clustering_13provinces_assignments.csv')
ar_all = pd.read_csv('results/metrics/association_rules_agroclimatic.csv')
ols_diag = pd.read_csv('results/metrics/ols_assumptions_diagnostics_gd1_to_gd4.csv')
wcorr = pd.read_csv('results/metrics/eda_within_correlations.csv')
outliers_3s = pd.read_csv('results/metrics/eda_3sigma_outliers_audit.csv')

PARSIMONIOUS_METEO = [
    'vpd_mean_kpa', 'precip_total_mm', 'ws2m_mean_ms',
    'pre_season_rain_90d_mm', 'oni_pre_season'
]

# =============================================================================
# 2. EXPORT EXACT TRAINED WEIGHTS FOR LIVE WHAT-IF SIMULATOR
# =============================================================================
def fit_export_anomaly_model(df, group_cols, model_type='huber', include_year=True, alpha=10.0):
    dev = df[df['harvest_year'] <= 2022].copy()
    y_meds = dev.groupby(group_cols)['yield_t_ha'].median()
    x_meds = dev.groupby(group_cols)[PARSIMONIOUS_METEO].median()
    y_res = []
    X_anom = {c: [] for c in PARSIMONIOUS_METEO}
    for _, r in dev.iterrows():
        key = tuple(r[g] for g in group_cols) if len(group_cols) > 1 else r[group_cols[0]]
        y_res.append(float(r['yield_t_ha'] - y_meds.loc[key]))
        for c in PARSIMONIOUS_METEO:
            X_anom[c].append(float(r[c] - x_meds.loc[key, c]))
    X_df = pd.DataFrame(X_anom)
    stds = X_df.std(ddof=0).replace(0, 1.0)
    X_z = X_df / stds
    yr_mean = float(dev['harvest_year'].mean())
    yr_std = float(dev['harvest_year'].std(ddof=0) or 1.0)
    if include_year:
        X_z['year_z'] = (dev['harvest_year'].values - yr_mean) / yr_std
    y_arr = np.array(y_res)
    if model_type == 'huber':
        mdl = HuberRegressor(alpha=alpha, epsilon=1.35, max_iter=1000).fit(X_z, y_arr)
    else:
        mdl = Ridge(alpha=alpha).fit(X_z, y_arr)

    key_str = lambda k: '|'.join(k) if isinstance(k, tuple) else str(k)
    return {
        'features': list(X_z.columns),
        'intercept': round(float(mdl.intercept_), 5),
        'coefs': [round(float(c), 5) for c in mdl.coef_],
        'stds': {c: round(float(stds[c]), 5) for c in PARSIMONIOUS_METEO},
        'year_mean': round(yr_mean, 4),
        'year_std': round(yr_std, 4),
        'include_year': include_year,
        'y_medians': {key_str(k): round(float(v), 4) for k, v in y_meds.items()},
        'x_medians': {key_str(k): {c: round(float(x_meds.loc[k, c]), 4) for c in PARSIMONIOUS_METEO} for k in x_meds.index}
    }

# Best Track B models (from Expanding-CV selection: Huber alpha=1.0, Ridge alpha=25.0)
sim_track_b_huber = fit_export_anomaly_model(t1, ['province_id', 'season'], model_type='huber', include_year=True, alpha=1.0)
sim_track_b_ridge = fit_export_anomaly_model(t1, ['province_id', 'season'], model_type='ridge', include_year=True, alpha=25.0)
# Best Track A 13-province Dong Xuan model (Huber alpha=10.0)
sim_track_a_dx_huber = fit_export_anomaly_model(t2_dx, ['province_id'], model_type='huber', include_year=True, alpha=10.0)

# Tertiles for C1 yield tier badge (strictly from dev <= 2022)
t2_all_dev = pd.concat([t2_dx, t2_comb], ignore_index=True)
t2_all_dev = t2_all_dev[t2_all_dev['harvest_year'] <= 2022]
q33, q67 = [round(float(x), 3) for x in np.quantile(t2_all_dev['yield_t_ha'], [1/3, 2/3])]

# =============================================================================
# 3. BUILD COMPACT JSON PAYLOAD FOR DASHBOARD
# =============================================================================
provinces_meta = []
for pid, g in t2_dx.groupby('province_id'):
    pname = g['province'].iloc[0]
    sub = g['ecological_subregion'].iloc[0]
    g_comb = t2_comb[t2_comb['province_id'] == pid]
    cl_row = cl_assign[cl_assign['province_id'] == pid].iloc[0]
    g_t1 = t1[t1['province_id'] == pid]
    dx_series = g.sort_values('harvest_year')[['harvest_year', 'yield_t_ha', 'vpd_mean_kpa', 'precip_total_mm', 'ws2m_mean_ms', 'pre_season_rain_90d_mm', 'oni_pre_season', 'domain_outlier_flag']].to_dict(orient='records')
    comb_series = g_comb.sort_values('harvest_year')[['harvest_year', 'yield_t_ha', 'vpd_mean_kpa', 'precip_total_mm', 'ws2m_mean_ms', 'pre_season_rain_90d_mm', 'oni_pre_season', 'domain_outlier_flag']].to_dict(orient='records')
    t1_series = {}
    if len(g_t1) > 0:
        for s_k in ['dong_xuan', 'he_thu', 'thu_dong']:
            t1_series[s_k] = g_t1[g_t1['season'] == s_k].sort_values('harvest_year')[['harvest_year', 'yield_t_ha', 'vpd_mean_kpa', 'precip_total_mm', 'ws2m_mean_ms', 'pre_season_rain_90d_mm', 'oni_pre_season']].to_dict(orient='records')
    provinces_meta.append({
        'province_id': pid,
        'province': pname,
        'ecological_subregion': sub,
        'has_3seasons': len(g_t1) > 0,
        'dx_mean': round(float(g['yield_t_ha'].mean()), 2),
        'dx_min': round(float(g['yield_t_ha'].min()), 2),
        'dx_max': round(float(g['yield_t_ha'].max()), 2),
        'httd_mean': round(float(g_comb['yield_t_ha'].mean()), 2),
        'total_prod_10y_mt': round(float((g['production_t'].sum() + g_comb['production_t'].sum()) / 1e6), 2),
        'clusters': {
            'KMeans_K3': int(cl_row['KMeans_K3']),
            'KMedoids_PAM_K3': int(cl_row['KMedoids_PAM_K3']),
            'Agglomerative_Ward_K3': int(cl_row['Agglomerative_Ward_K3']),
            'Agglomerative_Average_K3': int(cl_row['Agglomerative_Average_K3']),
            'DBSCAN_eps2_8_min2': int(cl_row['DBSCAN_eps2_8_min2']),
            'MeanShift_Auto': int(cl_row['MeanShift_Auto'])
        },
        'dx_series': dx_series,
        'comb_series': comb_series,
        't1_series': t1_series
    })

provinces_meta.sort(key=lambda x: x['province'])

# Simpson's Paradox correlation payload
simp_feats = ['precip_total_mm', 'heavy_rain_days_gt20mm', 'dry_days_lt1mm', 'rh2m_mean_pct', 'vpd_mean_kpa', 't2m_max_mean_c', 'hot_days_gt35c', 'ws2m_mean_ms']
simp_vn = {
    'precip_total_mm': 'Tổng lượng mưa',
    'heavy_rain_days_gt20mm': 'Ngày mưa lớn >20mm',
    'dry_days_lt1mm': 'Số ngày khô <1mm',
    'rh2m_mean_pct': 'Độ ẩm tương đối RH',
    'vpd_mean_kpa': 'Độ khô khí quyển VPD',
    't2m_max_mean_c': 'Nhiệt độ cực đại TB',
    'hot_days_gt35c': 'Số ngày nóng >35°C',
    'ws2m_mean_ms': 'Tốc độ gió 2m'
}
simp_sub = wcorr[(wcorr['track'] == 'track_b_3seasons') & (wcorr['scope'] == 'all_3_seasons_pooled') & (wcorr['feature'].isin(simp_feats))]
simpson_data = []
for f in simp_feats:
    r = simp_sub[simp_sub['feature'] == f].iloc[0]
    r_ht = wcorr[(wcorr['track'] == 'track_b_3seasons') & (wcorr['scope'] == 'he_thu') & (wcorr['feature'] == f)].iloc[0]
    r_td = wcorr[(wcorr['track'] == 'track_b_3seasons') & (wcorr['scope'] == 'thu_dong') & (wcorr['feature'] == f)].iloc[0]
    simpson_data.append({
        'feature': f, 'label': simp_vn[f],
        'raw_r': round(float(r['raw_pearson_r']), 3),
        'within_r': round(float(r['within_pearson_r']), 3),
        'within_p': round(float(r['within_p_value']), 4),
        'he_thu_r': round(float(r_ht['within_pearson_r']), 3),
        'thu_dong_r': round(float(r_td['within_pearson_r']), 3)
    })

payload = {
    'tier_thresholds': {'q33': q33, 'q67': q67},
    'provinces': provinces_meta,
    'simpson': simpson_data,
    'reg_track_b': reg_b[['model', 'train_2015_2022_mae', 'expanding_cv_mae', 'val_2021_2022_mae', 'test_2023_2024_mae', 'test_2023_2024_rmse', 'test_2023_2024_r2']].to_dict(orient='records'),
    'reg_track_a': reg_a[['suite', 'model', 'expanding_cv_mae', 'test_2023_2024_mae', 'test_2023_2024_rmse', 'test_2023_2024_r2']].to_dict(orient='records'),
    'clf_all': clf_all.to_dict(orient='records'),
    'ols_diag': ols_diag[['model', 'n', 'r2', 'adj_r2', 'f_pvalue_gd1', 'shapiro_p_gd2', 'max_vif_gd3', 'bp_p_gd4', 'white_p_gd4', 'aic', 'bic']].to_dict(orient='records'),
    'cl_val': cl_val.fillna(-999).to_dict(orient='records'),
    'rules_dx': ar_all[ar_all['dataset'] == 'TrackA_DX_13Prov_n127'].to_dict(orient='records'),
    'outliers_3sigma': outliers_3s[outliers_3s['flag_3sigma']][['dataset', 'province', 'harvest_year', 'season', 'yield_t_ha', 'z_score']].to_dict(orient='records'),
    'sim_models': {
        'track_b_huber': sim_track_b_huber,
        'track_b_ridge': sim_track_b_ridge,
        'track_a_dx_huber': sim_track_a_dx_huber
    }
}

payload_json = json.dumps(payload, ensure_ascii=False)

# =============================================================================
# 4. GENERATE STANDALONE OFFLINE INTERACTIVE DASHBOARD HTML
# =============================================================================
html_template = r"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard Phân tích Khí tượng & Năng suất Lúa ĐBSCL (2015–2024) — SGU</title>
<style>
  :root {
    --navy: #0a3570;
    --blue: #1659a8;
    --sky: #eff6ff;
    --gold: #eab308;
    --green: #15803d;
    --red: #b91c1c;
    --orange: #c2410c;
    --bg: #f1f5f9;
    --card: #ffffff;
    --ink: #0f172a;
    --muted: #475569;
    --border: #cbd5e1;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; background: var(--bg); color: var(--ink); line-height: 1.48; }

  header {
    background: linear-gradient(95deg, #072652 0%, var(--navy) 55%, var(--blue) 100%);
    color: #fff;
    padding: 16px 28px;
    border-bottom: 4px solid var(--gold);
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }
  header h1 { font-size: 20px; font-weight: 800; letter-spacing: 0.2px; }
  header p { font-size: 12.5px; color: #cfe2ff; margin-top: 3px; }
  .header-badges { display: flex; gap: 8px; flex-wrap: wrap; }
  .hbadge {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(234,179,8,0.6);
    color: #fef08a;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 600;
  }

  .tabs {
    background: #fff;
    border-bottom: 1px solid var(--border);
    padding: 0 28px;
    display: flex;
    gap: 6px;
    overflow-x: auto;
    position: sticky;
    top: 0;
    z-index: 50;
    box-shadow: 0 2px 6px rgba(15,23,42,0.05);
  }
  .tab-btn {
    background: transparent;
    border: none;
    border-bottom: 3px solid transparent;
    padding: 13px 16px;
    font-size: 13.5px;
    font-weight: 700;
    color: var(--muted);
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s;
  }
  .tab-btn:hover { color: var(--navy); background: #f8fafc; }
  .tab-btn.active { color: var(--navy); border-bottom-color: var(--blue); background: #f0f7ff; }

  main { max-width: 1420px; margin: 0 auto; padding: 20px 24px 40px; }
  .panel { display: none; }
  .panel.active { display: block; }

  .disclaimer {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-left: 4px solid var(--gold);
    color: #78350f;
    padding: 9px 14px;
    border-radius: 8px;
    font-size: 12.5px;
    margin-bottom: 16px;
  }

  .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(185px, 1fr)); gap: 12px; margin-bottom: 16px; }
  .kpi {
    background: var(--card);
    border: 1px solid var(--border);
    border-top: 3px solid var(--blue);
    border-radius: 10px;
    padding: 12px 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  .kpi.g { border-top-color: var(--green); }
  .kpi.r { border-top-color: var(--red); }
  .kpi.o { border-top-color: var(--orange); }
  .kpi .k-lbl { font-size: 11.5px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
  .kpi .k-val { font-size: 22px; font-weight: 800; color: var(--navy); margin: 4px 0 2px; }
  .kpi .k-sub { font-size: 11.5px; color: var(--muted); }

  .grid-2 { display: grid; grid-template-columns: 1.25fr 1fr; gap: 16px; margin-bottom: 16px; }
  .grid-2-eq { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
  @media (max-width: 980px) { .grid-2, .grid-2-eq { grid-template-columns: 1fr; } }

  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 18px;
    box-shadow: 0 1px 4px rgba(15,23,42,0.05);
    margin-bottom: 16px;
  }
  .card h2 { font-size: 15.5px; color: var(--navy); margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
  .card .sub { font-size: 12.2px; color: var(--muted); margin-bottom: 12px; }

  .controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 14px; background: #f8fafc; padding: 10px 14px; border-radius: 8px; border: 1px solid #e2e8f0; }
  .controls label { font-size: 12.5px; font-weight: 700; color: var(--navy); }
  select, input[type="range"] { font-family: inherit; }
  select {
    padding: 6px 10px; border-radius: 6px; border: 1px solid #94a3b8;
    background: #fff; font-size: 13px; color: var(--ink); font-weight: 600;
  }
  .btn {
    padding: 6px 12px; border-radius: 6px; border: 1px solid var(--blue);
    background: #fff; color: var(--blue); font-size: 12.5px; font-weight: 700; cursor: pointer;
  }
  .btn:hover, .btn.active { background: var(--blue); color: #fff; }
  .btn.warn { border-color: var(--orange); color: var(--orange); }
  .btn.warn:hover, .btn.warn.active { background: var(--orange); color: #fff; }

  table { width: 100%; border-collapse: collapse; font-size: 12.3px; }
  th { background: var(--navy); color: #fff; padding: 7px 9px; text-align: left; font-weight: 600; }
  td { padding: 6px 9px; border-bottom: 1px solid #e2e8f0; }
  tr:nth-child(even) td { background: #f8fafc; }
  tr.hl td { background: #dcfce7; font-weight: 700; }
  tr.bad-row td { background: #fee2e2; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; }
  .tag.g { background: #dcfce7; color: #166534; }
  .tag.r { background: #fee2e2; color: #991b1b; }
  .tag.b { background: #dbeafe; color: #1e40af; }
  .tag.o { background: #ffedd5; color: #9a3412; }

  .slider-group { margin-bottom: 11px; }
  .slider-head { display: flex; justify-content: space-between; font-size: 12.5px; font-weight: 600; margin-bottom: 3px; }
  .slider-group input[type="range"] { width: 100%; accent-color: var(--blue); cursor: pointer; }

  .pred-box {
    background: linear-gradient(135deg, #0a3570 0%, #1659a8 100%);
    color: #fff;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 12px;
  }
  .pred-val { font-size: 34px; font-weight: 800; color: #fef08a; margin: 4px 0; }
  .alert-box { padding: 10px 12px; border-radius: 8px; font-size: 12.5px; margin-top: 8px; border-left: 4px solid; }
  .alert-box.warn { background: #fef2f2; border-color: var(--red); color: #7f1d1d; }
  .alert-box.ok { background: #f0fdf4; border-color: var(--green); color: #14532d; }
  .alert-box.info { background: #eff6ff; border-color: var(--blue); color: #1e3a8a; }

  .cluster-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-bottom: 14px; }
  .cl-card { border-radius: 10px; padding: 14px; border: 1px solid var(--border); background: #f8fafc; border-left: 5px solid var(--blue); }
  .cl-card.c0 { border-left-color: #2563eb; background: #eff6ff; }
  .cl-card.c1 { border-left-color: #dc2626; background: #fef2f2; }
  .cl-card.c2 { border-left-color: #16a34a; background: #f0fdf4; }
  .cl-card.c-1 { border-left-color: #7c3aed; background: #f5f3ff; }
  .cl-card.c3 { border-left-color: #d97706; background: #fffbeb; }
  .cl-card.c4 { border-left-color: #0891b2; background: #ecfeff; }

  .gallery { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 14px; }
  .gal-item { background: #fff; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; cursor: pointer; transition: transform 0.15s; }
  .gal-item:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); }
  .gal-item img { width: 100%; height: 240px; object-fit: contain; background: #fff; padding: 8px; display: block; }
  .gal-item .cap { padding: 10px 12px; font-size: 12.5px; font-weight: 700; color: var(--navy); border-top: 1px solid #e2e8f0; background: #f8fafc; }

  .lightbox { display: none; position: fixed; inset: 0; background: rgba(15,23,42,0.88); z-index: 999; align-items: center; justify-content: center; padding: 24px; }
  .lightbox.open { display: flex; }
  .lightbox img { max-width: 95vw; max-height: 90vh; background: #fff; border-radius: 8px; padding: 8px; }
  .svg-wrap { width: 100%; overflow-x: auto; }
</style>
</head>
<body>

<header>
  <div>
    <h1>Dashboard Phân tích Khí tượng &amp; Năng suất Lúa Đồng bằng Sông Cửu Long (2015–2024)</h1>
    <p>Đồ án Phân tích Dữ liệu — Khoa CNTT, ĐH Sài Gòn · CBGD: <strong>Phan Thành Huấn</strong> · SV: Lê Thị Ngọc Giàu &amp; Trần Ngọc An</p>
  </div>
  <div class="header-badges">
    <span class="hbadge">13/13 Tỉnh ĐBSCL</span>
    <span class="hbadge">3 Mùa vụ · 10 Năm</span>
    <span class="hbadge">Offline · Dữ liệu thật 100%</span>
  </div>
</header>

<nav class="tabs">
  <button class="tab-btn active" onclick="switchTab('tab1', this)">1. Khám phá 13 Tỉnh &amp; Nghịch lý Simpson</button>
  <button class="tab-btn" onclick="switchTab('tab2', this)">2. So sánh Đa Mô hình (Hồi quy &amp; Phân lớp)</button>
  <button class="tab-btn" onclick="switchTab('tab3', this)">3. Mô phỏng Khí tượng &amp; Ước lượng (What-If)</button>
  <button class="tab-btn" onclick="switchTab('tab4', this)">4. Phân vùng 13 Tỉnh (Gom cụm) &amp; Luật Apriori</button>
  <button class="tab-btn" onclick="switchTab('tab5', this)">5. Thư viện 10 Biểu đồ 300 DPI</button>
</nav>

<main>
  <div class="disclaimer">
    <strong>Phạm vi &amp; Đối tượng thụ hưởng (DeTaiPTDL.pdf):</strong> Dashboard trực quan hóa toàn bộ dữ liệu sạch, kiểm định thống kê (GĐ1–GĐ4) và mô hình định lượng đã huấn luyện phục vụ <strong>học tập, nghiên cứu, tham khảo cho cơ quan quản lý/khuyến nông và chuỗi cung ứng lúa gạo ĐBSCL</strong>. Kết quả ước lượng mang tính <strong>hồi cứu (reduced-form)</strong>, không thay thế khuyến cáo nông học chính thức.
  </div>

  <!-- TAB 1: EXPLORER & SIMPSON'S PARADOX -->
  <section id="tab1" class="panel active">
    <div class="controls">
      <label for="provSelect">Chọn tỉnh ĐBSCL:</label>
      <select id="provSelect" onchange="renderTab1()"></select>
      <label for="seasonView">Chế độ xem chuỗi 10 năm:</label>
      <select id="seasonView" onchange="renderTab1()">
        <option value="both_t2">Tuyến A (Đông Xuân &amp; Hè Thu–Thu Đông)</option>
        <option value="t1_3seasons">Tuyến B (Tách riêng 3 vụ — AG, KG, CT)</option>
      </select>
      <span id="provNote" style="font-size:12px; color:#475569;"></span>
    </div>

    <div class="kpi-grid" id="tab1Kpis"></div>

    <div class="grid-2">
      <div class="card">
        <h2>Diễn biến Năng suất Lúa 2015–2024 <span id="chart1Badge" class="tag b"></span></h2>
        <div class="sub">Đường nét liền: Đông Xuân · Nét đứt: Hè Thu–Thu Đông (hoặc 3 vụ riêng) · Chấm đỏ: Ngoại lệ hạn mặn vượt 3σ (|z| &gt; 3)</div>
        <div class="svg-wrap" id="yieldChartSvg"></div>
      </div>

      <div class="card">
        <h2>
          Phát hiện KDD: Nghịch lý Simpson (Đảo dấu 8/8 biến)
          <span>
            <button id="btnSimpRaw" class="btn warn" onclick="setSimpMode('raw')">Tương quan Thô (Gộp vụ)</button>
            <button id="btnSimpWithin" class="btn active" onclick="setSimpMode('within')">Thực (Khử cố định Tỉnh×Vụ)</button>
          </span>
        </h2>
        <div class="sub" id="simpCaption"></div>
        <div class="svg-wrap" id="simpsonSvg"></div>
      </div>
    </div>

    <div class="card">
      <h2>Bảng số liệu chi tiết 10 năm của tỉnh đang chọn</h2>
      <div class="sub">Dữ liệu khí tượng Area-Weighted Zonal Mean (GADM v4.1) &amp; chỉ số ENSO (NOAA PSL ONI)</div>
      <div style="overflow-x:auto;" id="provTableWrap"></div>
    </div>
  </section>

  <!-- TAB 2: MULTI-MODEL COMPARISON -->
  <section id="tab2" class="panel">
    <div class="controls">
      <label for="benchSelect">Chọn bảng so sánh đa hình thái mô hình:</label>
      <select id="benchSelect" onchange="renderTab2()">
        <option value="reg_b">Hồi quy Tuyến B — 3 vụ tách riêng (20 mô hình, n=90)</option>
        <option value="reg_a_dx127">Hồi quy Tuyến A — 13 tỉnh Đông Xuân Đủ 127 dòng (14 mô hình)</option>
        <option value="reg_a_dx125">Hồi quy Tuyến A — 13 tỉnh Đông Xuân Ex-Salinity 125 (14 mô hình)</option>
        <option value="reg_a_comb">Hồi quy Tuyến A — 13 tỉnh Hè Thu–Thu Đông 130 (13 mô hình)</option>
        <option value="clf_c1_full">Phân lớp C1 — 3 hạng năng suất (Đầy đủ KT+Tỉnh+Vụ, 11 mô hình)</option>
        <option value="clf_c1_w">Phân lớp C1 — 3 hạng năng suất (Thuần Khí tượng + Tiểu vùng, 11 mô hình)</option>
        <option value="clf_c2">Phân lớp C2 — Nhị phân Rủi ro Sụt giảm &amp; Accuracy Paradox (10 mô hình)</option>
      </select>
    </div>

    <div class="grid-2">
      <div class="card">
        <h2 id="benchTitle">So sánh Mô hình</h2>
        <div class="sub" id="benchSub"></div>
        <div class="svg-wrap" id="benchSvg"></div>
      </div>
      <div class="card">
        <h2>Bảng Kiểm định 4 Giả định OLS (GĐ1–GĐ4, Buổi 04)</h2>
        <div class="sub">Cơ sở toán học giải thích vì sao cần chuyển từ OLS thuần sang Huber Loss &amp; HC3</div>
        <div style="overflow-x:auto;" id="olsDiagWrap"></div>
      </div>
    </div>

    <div class="card">
      <h2>Bảng độ đo chi tiết toàn bộ mô hình đã thử nghiệm</h2>
      <div class="sub">Khóa kín hoàn toàn tập Test 2023–2024; chọn cấu hình tối ưu trên Expanding-Window CV (2019–2022)</div>
      <div style="overflow-x:auto;" id="benchTableWrap"></div>
    </div>
  </section>

  <!-- TAB 3: WHAT-IF SIMULATOR -->
  <section id="tab3" class="panel">
    <div class="grid-2-eq">
      <div class="card">
        <h2>Thiết lập Kịch bản Khí tượng (Mô hình thật đã huấn luyện)</h2>
        <div class="sub">Trọng số xuất trực tiếp từ mô hình Huber &amp; Ridge huấn luyện trên tập dev (2015–2022)</div>
        <div class="controls" style="margin-bottom:10px;">
          <label for="simProv">Tỉnh:</label>
          <select id="simProv" onchange="onSimScopeChange()"></select>
          <label for="simSeason">Mùa vụ:</label>
          <select id="simSeason" onchange="onSimScopeChange()"></select>
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:14px;">
          <button class="btn" onclick="applyPreset('normal')">↺ Trung vị lịch sử</button>
          <button class="btn" onclick="applyPreset('lanina')">🌧 La Niña mưa nhiều</button>
          <button class="btn warn" onclick="applyPreset('elnino')">☀ El Niño hạn nóng (2016)</button>
          <button class="btn warn" onclick="applyPreset('storm')">💨 Gió bão mạnh cuối vụ</button>
        </div>

        <div class="slider-group">
          <div class="slider-head"><span>Độ khô khí quyển VPD (kPa)</span><span id="val_vpd"></span></div>
          <input type="range" id="sl_vpd" min="0.40" max="1.45" step="0.01" oninput="updateSim()">
        </div>
        <div class="slider-group">
          <div class="slider-head"><span>Tổng lượng mưa trong vụ (mm)</span><span id="val_rain"></span></div>
          <input type="range" id="sl_rain" min="50" max="1600" step="10" oninput="updateSim()">
        </div>
        <div class="slider-group">
          <div class="slider-head"><span>Tốc độ gió trung bình 2m (m/s)</span><span id="val_ws"></span></div>
          <input type="range" id="sl_ws" min="1.50" max="4.80" step="0.05" oninput="updateSim()">
        </div>
        <div class="slider-group">
          <div class="slider-head"><span>Tổng mưa 90 ngày tiền vụ (mm)</span><span id="val_pre90"></span></div>
          <input type="range" id="sl_pre90" min="100" max="1400" step="10" oninput="updateSim()">
        </div>
        <div class="slider-group">
          <div class="slider-head"><span>Chỉ số ENSO tiền vụ (NOAA ONI)</span><span id="val_oni"></span></div>
          <input type="range" id="sl_oni" min="-1.50" max="2.60" step="0.05" oninput="updateSim()">
        </div>
        <div class="slider-group">
          <div class="slider-head"><span>Năm thu hoạch (xu hướng kỹ thuật)</span><span id="val_year"></span></div>
          <input type="range" id="sl_year" min="2015" max="2026" step="1" value="2024" oninput="updateSim()">
        </div>
      </div>

      <div class="card">
        <h2>Kết quả Ước lượng &amp; Giải thích Đóng góp từng Biến</h2>
        <div class="sub">Tính toán trực tiếp từ phương trình Fixed-Effects Median + β·z (không dùng hộp đen)</div>
        <div class="pred-box">
          <div style="font-size:12.5px; color:#cfe2ff;" id="simModelLabel">Mô hình: Huber Robust Anomaly + Trend</div>
          <div class="pred-val" id="simPredVal">— tấn/ha</div>
          <div style="display:flex; flex-wrap:wrap; gap:14px; font-size:12.5px; color:#e2e8f0;" id="simPredMeta"></div>
        </div>
        <div id="simAlerts"></div>
        <h3 style="font-size:13.5px; color:var(--navy); margin:14px 0 6px;">Phân rã đóng góp từng yếu tố (Δ tấn/ha so với trung vị lịch sử):</h3>
        <div class="svg-wrap" id="waterfallSvg"></div>
      </div>
    </div>
  </section>

  <!-- TAB 4: CLUSTERING & APRIORI RULES -->
  <section id="tab4" class="panel">
    <div class="card">
      <h2>
        Phân vùng Khách quan 13 Tỉnh ĐBSCL (Buổi 11–12 — 9 Thuật toán Gom cụm)
        <select id="clAlgoSelect" onchange="renderClusters()">
          <option value="Agglomerative_Ward_K3">Agglomerative Ward (K=3) — Đồng thuận 5 thuật toán</option>
          <option value="KMeans_K3">K-Means (K=3)</option>
          <option value="KMedoids_PAM_K3">K-Medoids PAM (K=3)</option>
          <option value="Agglomerative_Average_K3">Agglomerative Average (K=3 — ARI/NMI cao nhất)</option>
          <option value="DBSCAN_eps2_8_min2">DBSCAN (eps=2,8, min=2) — Tách nhiễu Bến Tre</option>
          <option value="MeanShift_Auto">MeanShift (Tự xác định số cụm)</option>
        </select>
      </h2>
      <div class="sub" id="clMetricsSummary"></div>
      <div class="cluster-cards" id="clusterCards"></div>
    </div>

    <div class="card">
      <h2>Bộ lọc Luật Kết hợp Định lượng — Apriori (Buổi 06–07, Đông Xuân 13 tỉnh n=127)</h2>
      <div class="sub">Rời rạc hóa bằng pd.cut / pd.qcut · Đầy đủ 5 độ đo: Support, Confidence, Lift, Leverage, Conviction</div>
      <div class="controls">
        <label for="arOutcome">Hệ quả (Consequent):</label>
        <select id="arOutcome" onchange="renderRules()">
          <option value="ALL">Tất cả mức năng suất</option>
          <option value="NăngSuấtĐX=Cao">NăngSuấtĐX = Cao (Được mùa)</option>
          <option value="NăngSuấtĐX=Thấp">NăngSuấtĐX = Thấp (Rủi ro)</option>
          <option value="NăngSuấtĐX=TB">NăngSuấtĐX = Trung bình</option>
        </select>
        <label>Lift tối thiểu: <span id="arLiftVal">1.50</span></label>
        <input type="range" id="arLift" min="1.0" max="2.8" step="0.1" value="1.5" style="width:140px;" oninput="renderRules()">
        <label>Confidence tối thiểu: <span id="arConfVal">0.55</span></label>
        <input type="range" id="arConf" min="0.50" max="0.95" step="0.05" value="0.55" style="width:140px;" oninput="renderRules()">
      </div>
      <div style="overflow-x:auto;" id="rulesTableWrap"></div>
    </div>
  </section>

  <!-- TAB 5: FIGURE GALLERY -->
  <section id="tab5" class="panel">
    <div class="card">
      <h2>Thư viện 10 Biểu đồ Chuẩn Xuất bản (300 DPI)</h2>
      <div class="sub">Nhấp vào bất kỳ biểu đồ nào để phóng to toàn màn hình kiểm tra chi tiết số liệu</div>
      <div class="gallery" id="figGallery"></div>
    </div>
  </section>
</main>

<div class="lightbox" id="lightbox" onclick="this.classList.remove('open')">
  <img id="lightboxImg" src="" alt="Zoomed figure">
</div>

<script>
const DATA = __PAYLOAD_JSON__;

const SUB_VN = {
  'upstream_alluvial_3crop': 'Thượng nguồn / Phù sa ngọt',
  'middle_south_ql1': 'Vùng giữa / Nam QL1',
  'coastal_salinity_prone': 'Ven biển nhạy mặn'
};
const SEASON_VN = {
  'dong_xuan': 'Đông Xuân',
  'he_thu': 'Hè Thu',
  'thu_dong': 'Thu Đông'
};
const FEAT_VN = {
  'vpd_mean_kpa': 'VPD (độ khô)',
  'precip_total_mm': 'Tổng mưa vụ',
  'ws2m_mean_ms': 'Tốc độ gió 2m',
  'pre_season_rain_90d_mm': 'Mưa 90n tiền vụ',
  'oni_pre_season': 'ENSO (ONI)',
  'year_z': 'Xu hướng năm'
};

let simpMode = 'within';

function switchTab(id, btn) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}

// =========================================================================
// TAB 1: PROVINCE EXPLORER + SIMPSON'S PARADOX
// =========================================================================
function initTab1() {
  const sel = document.getElementById('provSelect');
  DATA.provinces.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.province_id;
    opt.textContent = p.province + (p.has_3seasons ? ' ★ (Đủ 3 vụ riêng)' : '');
    sel.appendChild(opt);
  });
  sel.value = 'ben_tre';
  renderTab1();
  renderSimpson();
}

function renderTab1() {
  const pid = document.getElementById('provSelect').value;
  const view = document.getElementById('seasonView').value;
  const p = DATA.provinces.find(x => x.province_id === pid);
  const note = document.getElementById('provNote');
  const effectiveView = (view === 't1_3seasons' && !p.has_3seasons) ? 'both_t2' : view;
  note.textContent = (view === 't1_3seasons' && !p.has_3seasons)
    ? '(Tỉnh này thuộc Tuyến A — tự động hiển thị Đông Xuân & cụm Hè Thu–Thu Đông)'
    : '';

  const clName = {0: 'Cụm 0: Ẩm gió · Năng suất cao', 1: 'Cụm 1: Ven biển rủi ro mặn cực đoan', 2: 'Cụm 2: Nội đồng Đông Bắc khô ấm'};
  const dbText = p.clusters.DBSCAN_eps2_8_min2 === -1 ? 'NHIỄU (-1: Cực đoan mặn)' : `Cụm mật độ ${p.clusters.DBSCAN_eps2_8_min2}`;

  document.getElementById('tab1Kpis').innerHTML = `
    <div class="kpi"><div class="k-lbl">Tiểu vùng sinh thái</div><div class="k-val" style="font-size:16px;">${SUB_VN[p.ecological_subregion]}</div><div class="k-sub">${clName[p.clusters.Agglomerative_Ward_K3]}</div></div>
    <div class="kpi g"><div class="k-lbl">Đông Xuân TB / Min–Max</div><div class="k-val">${p.dx_mean.toFixed(2)} <span style="font-size:13px;">tấn/ha</span></div><div class="k-sub">Min ${p.dx_min.toFixed(2)} · Max ${p.dx_max.toFixed(2)}</div></div>
    <div class="kpi"><div class="k-lbl">Hè Thu–Thu Đông TB</div><div class="k-val">${p.httd_mean.toFixed(2)} <span style="font-size:13px;">tấn/ha</span></div><div class="k-sub">Tổng sản lượng 10 năm: <strong>${p.total_prod_10y_mt} triệu tấn</strong></div></div>
    <div class="kpi ${p.clusters.DBSCAN_eps2_8_min2 === -1 ? 'r' : 'o'}"><div class="k-lbl">Phát hiện mật độ DBSCAN</div><div class="k-val" style="font-size:16px;">${dbText}</div><div class="k-sub">${p.dx_min < 3.5 ? 'Có cú sốc hạn mặn cực đoan (vượt 3σ)' : 'Không có cú sốc mất trắng vượt 3σ'}</div></div>
  `;

  // Render inline SVG line chart
  const W = 680, H = 290, padL = 48, padR = 24, padT = 20, padB = 34;
  const years = [2015,2016,2017,2018,2019,2020,2021,2022,2023,2024];
  const xOf = yr => padL + ((yr - 2015) / 9) * (W - padL - padR);
  const yMin = p.dx_min < 2 ? 0 : 4.0;
  const yMax = 8.2;
  const yOf = v => padT + ((yMax - v) / (yMax - yMin)) * (H - padT - padB);

  let svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%; max-width:${W}px; height:auto;">`;
  // Gridlines
  for (let yv = Math.ceil(yMin); yv <= 8; yv += 1) {
    const yy = yOf(yv);
    svg += `<line x1="${padL}" y1="${yy}" x2="${W-padR}" y2="${yy}" stroke="#e2e8f0" stroke-width="1"/>`;
    svg += `<text x="${padL-8}" y="${yy+4}" text-anchor="end" font-size="11" fill="#475569">${yv.toFixed(0)}</text>`;
  }
  years.forEach(yr => {
    const xx = xOf(yr);
    svg += `<text x="${xx}" y="${H-10}" text-anchor="middle" font-size="11" fill="#475569">${yr}</text>`;
  });
  // Test shading 2023-2024
  svg += `<rect x="${xOf(2022.5)}" y="${padT}" width="${xOf(2024.15)-xOf(2022.5)}" height="${H-padT-padB}" fill="#eff6ff" opacity="0.8"/>`;
  svg += `<text x="${xOf(2023.3)}" y="${padT+13}" text-anchor="middle" font-size="10" font-weight="700" fill="#1e40af">Test khóa kín</text>`;

  function drawSeries(arr, color, dash, name) {
    if (!arr || !arr.length) return;
    const pts = arr.map(r => `${xOf(r.harvest_year)},${yOf(r.yield_t_ha)}`).join(' ');
    svg += `<polyline fill="none" stroke="${color}" stroke-width="2.6" stroke-dasharray="${dash}" points="${pts}"/>`;
    arr.forEach(r => {
      const cx = xOf(r.harvest_year), cy = yOf(r.yield_t_ha);
      const isOut = r.domain_outlier_flag && r.domain_outlier_flag !== 'none';
      svg += `<circle cx="${cx}" cy="${cy}" r="${isOut ? 6 : 4}" fill="${isOut ? '#dc2626' : color}" stroke="#fff" stroke-width="1.5"><title>${name} ${r.harvest_year}: ${r.yield_t_ha.toFixed(2)} tấn/ha | ONI=${r.oni_pre_season}</title></circle>`;
      if (isOut) {
        svg += `<text x="${cx}" y="${cy-9}" text-anchor="middle" font-size="10" font-weight="700" fill="#b91c1c">${r.yield_t_ha.toFixed(2)} (3σ)</text>`;
      }
    });
  }

  if (effectiveView === 't1_3seasons') {
    document.getElementById('chart1Badge').textContent = 'Tuyến B: 3 vụ tách riêng';
    drawSeries(p.t1_series.dong_xuan, '#1d4ed8', '', 'Đông Xuân');
    drawSeries(p.t1_series.he_thu, '#ea580c', '6,3', 'Hè Thu');
    drawSeries(p.t1_series.thu_dong, '#15803d', '2,3', 'Thu Đông');
    svg += `<text x="${padL+8}" y="${padT+12}" font-size="11" font-weight="700" fill="#1d4ed8">— Đông Xuân</text>`;
    svg += `<text x="${padL+95}" y="${padT+12}" font-size="11" font-weight="700" fill="#ea580c">-- Hè Thu</text>`;
    svg += `<text x="${padL+165}" y="${padT+12}" font-size="11" font-weight="700" fill="#15803d">··· Thu Đông</text>`;
  } else {
    document.getElementById('chart1Badge').textContent = 'Tuyến A: Đông Xuân & HT–TĐ';
    drawSeries(p.dx_series, '#1d4ed8', '', 'Đông Xuân');
    drawSeries(p.comb_series, '#ea580c', '6,3', 'Hè Thu–Thu Đông');
    svg += `<text x="${padL+8}" y="${padT+12}" font-size="11" font-weight="700" fill="#1d4ed8">— Đông Xuân</text>`;
    svg += `<text x="${padL+95}" y="${padT+12}" font-size="11" font-weight="700" fill="#ea580c">-- Hè Thu–Thu Đông</text>`;
  }
  svg += `</svg>`;
  document.getElementById('yieldChartSvg').innerHTML = svg;

  // Detail table
  const rows = p.dx_series;
  let tbl = `<table><thead><tr><th>Năm</th><th class="num">Năng suất ĐX (tấn/ha)</th><th class="num">VPD (kPa)</th><th class="num">Mưa trong vụ (mm)</th><th class="num">Gió 2m (m/s)</th><th class="num">Mưa 90n tiền vụ (mm)</th><th class="num">ENSO ONI</th><th>Ghi chú</th></tr></thead><tbody>`;
  rows.forEach(r => {
    const out = r.domain_outlier_flag !== 'none';
    tbl += `<tr class="${out ? 'bad-row' : ''}"><td><strong>${r.harvest_year}</strong></td><td class="num"><strong>${r.yield_t_ha.toFixed(2)}</strong></td><td class="num">${r.vpd_mean_kpa.toFixed(3)}</td><td class="num">${r.precip_total_mm.toFixed(1)}</td><td class="num">${r.ws2m_mean_ms.toFixed(2)}</td><td class="num">${r.pre_season_rain_90d_mm.toFixed(1)}</td><td class="num">${r.oni_pre_season.toFixed(2)}</td><td>${out ? '<span class="tag r">Hạn mặn cực đoan (3σ)</span>' : (r.harvest_year >= 2023 ? '<span class="tag b">Test khóa kín</span>' : '<span class="tag g">Bình thường</span>')}</td></tr>`;
  });
  tbl += `</tbody></table>`;
  document.getElementById('provTableWrap').innerHTML = tbl;
}

function setSimpMode(m) {
  simpMode = m;
  document.getElementById('btnSimpRaw').classList.toggle('active', m === 'raw');
  document.getElementById('btnSimpWithin').classList.toggle('active', m === 'within');
  renderSimpson();
}

function renderSimpson() {
  const cap = document.getElementById('simpCaption');
  cap.innerHTML = simpMode === 'raw'
    ? '<strong style="color:#b91c1c;">BẪY TRỘN MÙA (Tương quan thô gộp 3 vụ):</strong> Mưa tương quan ÂM (−0,74), Ngày khô (+0,88) &amp; Nóng &gt;35°C (+0,48) → dễ kết luận ngược đời vì vụ Đông Xuân rơi vào mùa khô!'
    : '<strong style="color:#15803d;">QUY LUẬT THỰC (Sau khi khử cố định Tỉnh × Vụ):</strong> Toàn bộ 8/8 biến ĐẢO DẤU — Mưa thành DƯƠNG (+0,37, p=0,0003), Mưa lớn (+0,38, p=0,0002), VPD &amp; Nóng thành ÂM!';

  const W = 540, H = 280, midX = 310, scale = 180;
  let svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%; max-width:${W}px; height:auto;">`;
  svg += `<line x1="${midX}" y1="12" x2="${midX}" y2="${H-16}" stroke="#334155" stroke-width="1.4"/>`;
  svg += `<text x="${midX-90}" y="12" text-anchor="middle" font-size="10" fill="#b91c1c">← Tương quan ÂM</text>`;
  svg += `<text x="${midX+90}" y="12" text-anchor="middle" font-size="10" fill="#15803d">Tương quan DƯƠNG →</text>`;
  DATA.simpson.forEach((d, idx) => {
    const y = 28 + idx * 30;
    const val = simpMode === 'raw' ? d.raw_r : d.within_r;
    const bw = Math.abs(val) * scale;
    const bx = val >= 0 ? midX : midX - bw;
    const col = val >= 0 ? '#16a34a' : '#dc2626';
    svg += `<text x="148" y="${y+13}" text-anchor="end" font-size="11.5" font-weight="600" fill="#0f172a">${d.label}</text>`;
    svg += `<rect x="${bx}" y="${y}" width="${Math.max(bw, 2)}" height="18" rx="3" fill="${col}" opacity="0.86"/>`;
    const tx = val >= 0 ? bx + bw + 5 : bx - 5;
    const anchor = val >= 0 ? 'start' : 'end';
    svg += `<text x="${tx}" y="${y+13}" text-anchor="${anchor}" font-size="11" font-weight="700" fill="${col}">${val >= 0 ? '+' : ''}${val.toFixed(3)}</text>`;
  });
  svg += `</svg>`;
  document.getElementById('simpsonSvg').innerHTML = svg;
}

// =========================================================================
// TAB 2: MULTI-MODEL COMPARISON + OLS DIAGNOSTICS
// =========================================================================
function renderTab2() {
  const key = document.getElementById('benchSelect').value;
  let rows = [], metricCol = '', secondaryCol = '', higherBetter = false, title = '', sub = '';
  if (key === 'reg_b') {
    rows = DATA.reg_track_b;
    metricCol = 'expanding_cv_mae'; secondaryCol = 'test_2023_2024_mae'; higherBetter = false;
    title = 'Hồi quy Tuyến B — 3 vụ tách riêng (20 mô hình)';
    sub = 'Xanh đậm: Expanding-CV MAE (chọn mô hình) · Cam: Test MAE khóa kín (2023–2024) · Nhỏ hơn tốt hơn';
  } else if (key.startsWith('reg_a_')) {
    const mapS = {'reg_a_dx127': 'delta13_dong_xuan_full_127', 'reg_a_dx125': 'delta13_dong_xuan_ex_salinity_125', 'reg_a_comb': 'delta13_combined_ht_td_130'};
    rows = DATA.reg_track_a.filter(r => r.suite === mapS[key]);
    metricCol = 'expanding_cv_mae'; secondaryCol = 'test_2023_2024_mae'; higherBetter = false;
    title = 'Hồi quy Tuyến A — ' + mapS[key];
    sub = 'Xanh đậm: Expanding-CV MAE · Cam: Test MAE (2023–2024) · Nhỏ hơn tốt hơn';
  } else {
    const fMap = {
      'clf_c1_full': r => r.task === 'C1_3Class_YieldTier' && r.feature_regime === 'full_context',
      'clf_c1_w': r => r.task === 'C1_3Class_YieldTier' && r.feature_regime === 'weather_subregion',
      'clf_c2': r => r.task === 'C2_Binary_UnderperformRisk'
    };
    rows = DATA.clf_all.filter(fMap[key]);
    metricCol = 'exp_cv_f1'; secondaryCol = 'test_f1'; higherBetter = true;
    title = key === 'clf_c2' ? 'Phân lớp Nhị phân C2 — Rủi ro Sụt giảm (Minh họa Accuracy Paradox)' : 'Phân lớp Đa lớp C1 — 3 hạng mức năng suất (n=257)';
    sub = 'Xanh đậm: Expanding-CV F1 · Xanh lá: Test F1 khóa kín (2023–2024) · Cao hơn tốt hơn';
  }
  document.getElementById('benchTitle').textContent = title;
  document.getElementById('benchSub').textContent = sub;

  // Bar Chart SVG
  const maxVal = Math.max(...rows.map(r => Math.max(r[metricCol] || 0, r[secondaryCol] || 0)), 0.01) * 1.15;
  const rowH = 26, W = 660, H = 26 + rows.length * rowH;
  const padL = 215, barArea = W - padL - 60;
  let svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%; max-width:${W}px; height:auto;">`;
  rows.forEach((r, i) => {
    const y = 16 + i * rowH;
    const v1 = r[metricCol] || 0, v2 = r[secondaryCol] || 0;
    const w1 = (v1 / maxVal) * barArea, w2 = (v2 / maxVal) * barArea;
    svg += `<text x="${padL-8}" y="${y+14}" text-anchor="end" font-size="10.8" font-weight="600" fill="#1e293b">${r.model}</text>`;
    svg += `<rect x="${padL}" y="${y}" width="${Math.max(w1,2)}" height="9" rx="2" fill="#1d4ed8"/>`;
    svg += `<rect x="${padL}" y="${y+10}" width="${Math.max(w2,2)}" height="9" rx="2" fill="${higherBetter ? '#16a34a' : '#ea580c'}"/>`;
    svg += `<text x="${padL + Math.max(w1,w2) + 5}" y="${y+14}" font-size="10" font-weight="700" fill="#334155">${v1.toFixed(3)} / ${v2.toFixed(3)}</text>`;
  });
  svg += `</svg>`;
  document.getElementById('benchSvg').innerHTML = svg;

  // Table
  const bestPrimary = higherBetter ? Math.max(...rows.map(r => r[metricCol])) : Math.min(...rows.map(r => r[metricCol]));
  let tbl = '<table><thead><tr>';
  if (key.startsWith('reg_')) {
    tbl += '<th>Mô hình</th><th class="num">Exp-CV MAE</th><th class="num">Test MAE</th><th class="num">Test RMSE</th><th class="num">Test R²</th></tr></thead><tbody>';
    rows.forEach(r => {
      const isBest = Math.abs(r[metricCol] - bestPrimary) < 1e-6;
      const isOverfit = r.test_2023_2024_mae > 0.33 && key === 'reg_b';
      tbl += `<tr class="${isBest ? 'hl' : (isOverfit ? 'bad-row' : '')}"><td>${r.model}</td><td class="num">${r.expanding_cv_mae.toFixed(4)}</td><td class="num">${r.test_2023_2024_mae.toFixed(4)}</td><td class="num">${r.test_2023_2024_rmse.toFixed(4)}</td><td class="num">${r.test_2023_2024_r2.toFixed(4)}</td></tr>`;
    });
  } else {
    tbl += '<th>Mô hình</th><th class="num">5-Fold F1</th><th class="num">Exp-CV F1</th><th class="num">Test Acc</th><th class="num">Test Prec</th><th class="num">Test Rec</th><th class="num">Test F1</th><th class="num">Test AUC</th></tr></thead><tbody>';
    rows.forEach(r => {
      const isBest = Math.abs(r.test_f1 - Math.max(...rows.map(x => x.test_f1))) < 1e-6;
      const isZero = key === 'clf_c2' && r.test_f1 === 0 && r.model !== 'Dummy_Baseline';
      tbl += `<tr class="${isBest ? 'hl' : (isZero ? 'bad-row' : '')}"><td>${r.model}</td><td class="num">${r.skf5_f1.toFixed(4)}</td><td class="num">${r.exp_cv_f1.toFixed(4)}</td><td class="num">${(r.test_acc*100).toFixed(1)}%</td><td class="num">${r.test_precision.toFixed(4)}</td><td class="num">${r.test_recall.toFixed(4)}</td><td class="num"><strong>${r.test_f1.toFixed(4)}</strong></td><td class="num">${r.test_auc.toFixed(4)}</td></tr>`;
    });
  }
  tbl += '</tbody></table>';
  document.getElementById('benchTableWrap').innerHTML = tbl;

  // OLS diagnostics table
  let dt = '<table><thead><tr><th>Mô hình OLS</th><th class="num">Adj.R²</th><th class="num">GĐ1 F</th><th class="num">GĐ2 SW</th><th class="num">GĐ3 VIF</th><th class="num">GĐ4 White</th><th class="num">AIC</th></tr></thead><tbody>';
  DATA.ols_diag.forEach(d => {
    const shortM = d.model.replace('_Ortho5_Year_n90','').replace('_13Prov','');
    dt += `<tr><td>${shortM}</td><td class="num">${d.adj_r2.toFixed(3)}</td><td class="num"><span class="tag g">&lt;0.001</span></td><td class="num"><span class="tag ${d.shapiro_p_gd2 >= 0.05 ? 'g' : 'r'}">${d.shapiro_p_gd2 < 0.0001 ? '&lt;1e-4' : d.shapiro_p_gd2.toFixed(3)}</span></td><td class="num"><span class="tag ${d.max_vif_gd3 < 10 ? 'g' : 'r'}">${d.max_vif_gd3.toFixed(2)}</span></td><td class="num"><span class="tag ${d.white_p_gd4 >= 0.05 ? 'g' : 'r'}">${d.white_p_gd4.toFixed(3)}</span></td><td class="num">${d.aic.toFixed(1)}</td></tr>`;
  });
  dt += '</tbody></table>';
  document.getElementById('olsDiagWrap').innerHTML = dt;
}

// =========================================================================
// TAB 3: LIVE WHAT-IF SIMULATOR (EXACT TRAINED WEIGHTS)
// =========================================================================
function initTab3() {
  const sp = document.getElementById('simProv');
  DATA.provinces.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.province_id;
    opt.textContent = p.province + (p.has_3seasons ? ' (Đủ 3 vụ)' : ' (Đông Xuân)');
    sp.appendChild(opt);
  });
  sp.value = 'an_giang';
  onSimScopeChange();
}

function getActiveSimModelAndKey() {
  const pid = document.getElementById('simProv').value;
  const p = DATA.provinces.find(x => x.province_id === pid);
  const ss = document.getElementById('simSeason');
  if (p.has_3seasons) {
    if (ss.options.length !== 3) {
      ss.innerHTML = '<option value="dong_xuan">Đông Xuân</option><option value="he_thu">Hè Thu</option><option value="thu_dong">Thu Đông</option>';
    }
    const season = ss.value || 'dong_xuan';
    return { mdl: DATA.sim_models.track_b_huber, ridge: DATA.sim_models.track_b_ridge, key: `${pid}|${season}`, province: p, season: season, label: 'Tuyến B — Huber Robust + Trend (đối chiếu Ridge)' };
  } else {
    ss.innerHTML = '<option value="dong_xuan">Đông Xuân (Toàn vùng 13 tỉnh)</option>';
    return { mdl: DATA.sim_models.track_a_dx_huber, ridge: null, key: pid, province: p, season: 'dong_xuan', label: 'Tuyến A (13 tỉnh ĐX) — Huber Robust + Trend' };
  }
}

function onSimScopeChange() {
  const ctx = getActiveSimModelAndKey();
  const xm = ctx.mdl.x_medians[ctx.key];
  document.getElementById('sl_vpd').value = xm.vpd_mean_kpa;
  document.getElementById('sl_rain').value = xm.precip_total_mm;
  document.getElementById('sl_ws').value = xm.ws2m_mean_ms;
  document.getElementById('sl_pre90').value = xm.pre_season_rain_90d_mm;
  document.getElementById('sl_oni').value = xm.oni_pre_season;
  document.getElementById('sl_year').value = 2024;
  updateSim();
}

function applyPreset(kind) {
  const ctx = getActiveSimModelAndKey();
  const xm = ctx.mdl.x_medians[ctx.key];
  if (kind === 'normal') {
    document.getElementById('sl_vpd').value = xm.vpd_mean_kpa;
    document.getElementById('sl_rain').value = xm.precip_total_mm;
    document.getElementById('sl_ws').value = xm.ws2m_mean_ms;
    document.getElementById('sl_pre90').value = xm.pre_season_rain_90d_mm;
    document.getElementById('sl_oni').value = xm.oni_pre_season;
  } else if (kind === 'lanina') {
    document.getElementById('sl_vpd').value = Math.max(0.45, xm.vpd_mean_kpa - 0.12).toFixed(2);
    document.getElementById('sl_rain').value = Math.min(1500, xm.precip_total_mm + 220).toFixed(0);
    document.getElementById('sl_ws').value = Math.max(1.8, xm.ws2m_mean_ms - 0.3).toFixed(2);
    document.getElementById('sl_pre90').value = Math.min(1350, xm.pre_season_rain_90d_mm + 260).toFixed(0);
    document.getElementById('sl_oni').value = -1.10;
  } else if (kind === 'elnino') {
    document.getElementById('sl_vpd').value = Math.min(1.40, xm.vpd_mean_kpa + 0.18).toFixed(2);
    document.getElementById('sl_rain').value = Math.max(60, xm.precip_total_mm - 180).toFixed(0);
    document.getElementById('sl_ws').value = Math.min(4.6, xm.ws2m_mean_ms + 0.4).toFixed(2);
    document.getElementById('sl_pre90').value = Math.max(150, xm.pre_season_rain_90d_mm - 240).toFixed(0);
    document.getElementById('sl_oni').value = 2.40;
  } else if (kind === 'storm') {
    document.getElementById('sl_vpd').value = Math.max(0.45, xm.vpd_mean_kpa - 0.08).toFixed(2);
    document.getElementById('sl_rain').value = Math.min(1550, xm.precip_total_mm + 280).toFixed(0);
    document.getElementById('sl_ws').value = Math.min(4.7, xm.ws2m_mean_ms + 0.95).toFixed(2);
    document.getElementById('sl_pre90').value = xm.pre_season_rain_90d_mm;
    document.getElementById('sl_oni').value = -0.50;
  }
  updateSim();
}

function updateSim() {
  const ctx = getActiveSimModelAndKey();
  const mdl = ctx.mdl;
  const xm = mdl.x_medians[ctx.key];
  const yBase = mdl.y_medians[ctx.key];

  const vals = {
    vpd_mean_kpa: parseFloat(document.getElementById('sl_vpd').value),
    precip_total_mm: parseFloat(document.getElementById('sl_rain').value),
    ws2m_mean_ms: parseFloat(document.getElementById('sl_ws').value),
    pre_season_rain_90d_mm: parseFloat(document.getElementById('sl_pre90').value),
    oni_pre_season: parseFloat(document.getElementById('sl_oni').value)
  };
  const yr = parseFloat(document.getElementById('sl_year').value);

  document.getElementById('val_vpd').textContent = vals.vpd_mean_kpa.toFixed(2) + ' kPa';
  document.getElementById('val_rain').textContent = vals.precip_total_mm.toFixed(0) + ' mm';
  document.getElementById('val_ws').textContent = vals.ws2m_mean_ms.toFixed(2) + ' m/s';
  document.getElementById('val_pre90').textContent = vals.pre_season_rain_90d_mm.toFixed(0) + ' mm';
  document.getElementById('val_oni').textContent = (vals.oni_pre_season >= 0 ? '+' : '') + vals.oni_pre_season.toFixed(2);
  document.getElementById('val_year').textContent = yr;

  const contribs = [];
  let delta = mdl.intercept;
  mdl.features.forEach((f, idx) => {
    const z = f === 'year_z' ? (yr - mdl.year_mean) / mdl.year_std : (vals[f] - xm[f]) / mdl.stds[f];
    const c = mdl.coefs[idx] * z;
    delta += c;
    contribs.push({ feature: f, label: FEAT_VN[f] || f, contrib: c, z: z });
  });
  const pred = Math.max(0.1, yBase + delta);

  let ridgeText = '';
  if (ctx.ridge) {
    let dr = ctx.ridge.intercept;
    ctx.ridge.features.forEach((f, idx) => {
      const z = f === 'year_z' ? (yr - ctx.ridge.year_mean) / ctx.ridge.year_std : (vals[f] - ctx.ridge.x_medians[ctx.key][f]) / ctx.ridge.stds[f];
      dr += ctx.ridge.coefs[idx] * z;
    });
    ridgeText = `<span>Ridge đối chiếu: <strong>${(ctx.ridge.y_medians[ctx.key] + dr).toFixed(2)} tấn/ha</strong></span>`;
  }

  const tier = pred >= DATA.tier_thresholds.q67 ? 'CAO (≥ 6,49)' : (pred >= DATA.tier_thresholds.q33 ? 'TRUNG BÌNH (5,58–6,49)' : 'THẤP (< 5,58)');
  document.getElementById('simModelLabel').textContent = `${ctx.label} · ${ctx.province.province} — Vụ ${SEASON_VN[ctx.season]}`;
  document.getElementById('simPredVal').textContent = `${pred.toFixed(2)} tấn/ha`;
  document.getElementById('simPredMeta').innerHTML = `
    <span>Baseline lịch sử: <strong>${yBase.toFixed(2)}</strong></span>
    <span>Chênh lệch: <strong>${delta >= 0 ? '+' : ''}${delta.toFixed(2)} tấn/ha</strong></span>
    <span>Phân hạng C1: <strong>${tier}</strong></span>
    ${ridgeText}
  `;

  // Alerts (CART Rule + Coastal OVB Warning)
  let alerts = '';
  const zPre90 = (vals.pre_season_rain_90d_mm - xm.pre_season_rain_90d_mm) / mdl.stds.pre_season_rain_90d_mm;
  if (vals.oni_pre_season > 0.80 && zPre90 <= -0.47) {
    alerts += `<div class="alert-box warn"><strong>⚠ Kích hoạt Luật Cây Quyết định CART:</strong> El Niño mạnh (ONI &gt; +0,80) kèm thiếu hụt mưa 90 ngày tiền vụ → <strong>Cảnh báo rủi ro sụt giảm năng suất dưới kỳ vọng!</strong></div>`;
  } else if (vals.oni_pre_season < -0.5 && ctx.province.ecological_subregion === 'upstream_alluvial_3crop' && ctx.season === 'dong_xuan') {
    alerts += `<div class="alert-box ok"><strong>✓ Khớp Luật Apriori thuận lợi (Lift 2,46–3,02):</strong> La Niña tại vùng thượng nguồn thuận lợi cho năng suất Đông Xuân nhóm Cao.</div>`;
  }
  if (ctx.province.ecological_subregion === 'coastal_salinity_prone' && ctx.season === 'dong_xuan' && vals.oni_pre_season >= 0.7) {
    alerts += `<div class="alert-box info"><strong>ℹ Lưu ý OVB Vùng ven biển (${ctx.province.province}):</strong> Mô hình chỉ dùng khí tượng bề mặt; trong năm El Niño cần theo dõi thêm độ mặn thực địa (g/l) &amp; lưu lượng Mê Kông (như bài học Bến Tre 2016/2020).</div>`;
  }
  document.getElementById('simAlerts').innerHTML = alerts;

  // Contribution Bar SVG
  const W = 520, H = 195, midX = 290, maxC = Math.max(0.25, ...contribs.map(x => Math.abs(x.contrib))) * 1.15, sc = 165 / maxC;
  let svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%; max-width:${W}px; height:auto;">`;
  svg += `<line x1="${midX}" y1="6" x2="${midX}" y2="${H-10}" stroke="#334155" stroke-width="1.3"/>`;
  contribs.forEach((c, i) => {
    const y = 14 + i * 29;
    const bw = Math.abs(c.contrib) * sc;
    const bx = c.contrib >= 0 ? midX : midX - bw;
    const col = c.contrib >= 0 ? '#16a34a' : '#dc2626';
    svg += `<text x="135" y="${y+14}" text-anchor="end" font-size="11.5" font-weight="600" fill="#0f172a">${c.label}</text>`;
    svg += `<rect x="${bx}" y="${y}" width="${Math.max(bw, 2)}" height="18" rx="3" fill="${col}" opacity="0.88"/>`;
    const tx = c.contrib >= 0 ? bx + bw + 5 : bx - 5;
    svg += `<text x="${tx}" y="${y+13}" text-anchor="${c.contrib >= 0 ? 'start' : 'end'}" font-size="11" font-weight="700" fill="${col}">${c.contrib >= 0 ? '+' : ''}${c.contrib.toFixed(3)}</text>`;
  });
  svg += `</svg>`;
  document.getElementById('waterfallSvg').innerHTML = svg;
}

// =========================================================================
// TAB 4: CLUSTERING & APRIORI EXPLORER
// =========================================================================
function renderClusters() {
  const algo = document.getElementById('clAlgoSelect').value;
  const v = DATA.cl_val.find(x => x.algorithm === algo);
  document.getElementById('clMetricsSummary').innerHTML =
    `<strong>Internal Validation:</strong> SSE = <code>${v.internal_sse.toFixed(2)}</code> · Silhouette = <code>${v.internal_silhouette > -900 ? v.internal_silhouette.toFixed(3) : 'N/A'}</code> · Calinski-Harabasz = <code>${v.internal_calinski_harabasz > -900 ? v.internal_calinski_harabasz.toFixed(2) : 'N/A'}</code> &nbsp;|&nbsp; <strong>External (vs 3 tiểu vùng):</strong> ARI = <code>${v.external_ari_vs_subregion.toFixed(3)}</code> · NMI = <code>${v.external_nmi_vs_subregion.toFixed(3)}</code>`;

  const groups = {};
  DATA.provinces.forEach(p => {
    const cid = p.clusters[algo];
    if (!groups[cid]) groups[cid] = [];
    groups[cid].push(p);
  });
  let html = '';
  Object.keys(groups).sort((a,b) => Number(a)-Number(b)).forEach(cid => {
    const arr = groups[cid];
    const title = cid === '-1' ? 'Cụm -1: ĐIỂM NHIỄU / CỰC ĐOAN (DBSCAN)' : `Cụm dữ liệu ${cid} (${arr.length} tỉnh)`;
    const meanDx = (arr.reduce((s,p) => s + p.dx_mean, 0) / arr.length).toFixed(2);
    html += `<div class="cl-card c${cid}"><h3 style="font-size:14px;color:var(--navy);margin-bottom:6px;">${title}</h3><div style="font-size:12px;color:#475569;margin-bottom:8px;">Năng suất ĐX TB cụm: <strong>${meanDx} tấn/ha</strong></div><div style="display:flex;flex-wrap:wrap;gap:5px;">`;
    arr.forEach(p => {
      const badgeCls = p.ecological_subregion === 'coastal_salinity_prone' ? 'r' : (p.ecological_subregion === 'upstream_alluvial_3crop' ? 'b' : 'o');
      html += `<span class="tag ${badgeCls}" title="ĐX TB: ${p.dx_mean} | Min: ${p.dx_min}">${p.province} (${p.dx_mean})</span>`;
    });
    html += `</div></div>`;
  });
  document.getElementById('clusterCards').innerHTML = html;
}

function renderRules() {
  const outF = document.getElementById('arOutcome').value;
  const minL = parseFloat(document.getElementById('arLift').value);
  const minC = parseFloat(document.getElementById('arConf').value);
  document.getElementById('arLiftVal').textContent = minL.toFixed(2);
  document.getElementById('arConfVal').textContent = minC.toFixed(2);

  const filtered = DATA.rules_dx.filter(r =>
    (outF === 'ALL' || r.consequent === outF) && r.lift >= minL && r.confidence >= minC
  );
  if (!filtered.length) {
    document.getElementById('rulesTableWrap').innerHTML = '<p style="padding:12px;color:#64748b;">Không có luật nào thỏa mãn ngưỡng lọc hiện tại. Hãy giảm nhẹ thanh trượt Lift/Confidence.</p>';
    return;
  }
  let tbl = '<table><thead><tr><th>Điều kiện (Antecedent)</th><th>Hệ quả (Consequent)</th><th class="num">Support</th><th class="num">Confidence</th><th class="num">Lift</th><th class="num">Leverage</th><th class="num">Conviction</th></tr></thead><tbody>';
  filtered.forEach(r => {
    const cls = r.consequent.includes('Cao') ? 'g' : (r.consequent.includes('Thấp') ? 'r' : 'o');
    tbl += `<tr><td><code>IF ${r.antecedent}</code></td><td><span class="tag ${cls}">${r.consequent}</span></td><td class="num">${r.support.toFixed(4)}</td><td class="num"><strong>${r.confidence.toFixed(4)}</strong></td><td class="num"><strong>${r.lift.toFixed(3)}</strong></td><td class="num">${r.leverage.toFixed(4)}</td><td class="num">${r.conviction >= 999 ? '∞' : r.conviction.toFixed(2)}</td></tr>`;
  });
  tbl += '</tbody></table>';
  document.getElementById('rulesTableWrap').innerHTML = tbl;
}

// =========================================================================
// TAB 5: GALLERY OF ALL 10 300-DPI FIGURES
// =========================================================================
function initGallery() {
  const figs = [
    ['01_eda_yield_by_season_and_province.png', 'Hình 01 · Phân bố năng suất 3 vụ (Tuyến B) & 13 tỉnh ĐBSCL (Tuyến A)'],
    ['02_eda_collinearity_and_within_corr.png', 'Hình 02 · Đa cộng tuyến thô vs Tương quan phần dư theo từng mùa vụ'],
    ['03_model_comparison_tier1_and_tier2.png', 'Hình 03 · So sánh đa hình thái 20 mô hình hồi quy (Tuyến B & Tuyến A)'],
    ['04_sensitivity_calendar_and_spatial.png', 'Hình 04 · Kiểm định độ nhạy lịch thời vụ (±10/±15 ngày) & Zonal vs 1 điểm'],
    ['05_residual_attribution_salinity_13provinces.png', 'Hình 05 · Bản đồ phần dư LOYO 10 năm & Chứng minh OVB Hạn mặn'],
    ['06_spatial_generalization_ood_check.png', 'Hình 06 · Ngoại kiểm địa lý OOD (7 dòng vùng giữa & ven biển)'],
    ['07_ols_assumptions_diagnostics_gd1_gd4.png', 'Hình 07 · Kiểm định 4 giả định OLS (GĐ1–GĐ4): Shapiro-Wilk, Q-Q, BP/White'],
    ['08_classification_multimodel_roc_and_cm.png', 'Hình 08 · Phân lớp đa hình thái (10 mô hình): Macro-F1, ROC Curve & Confusion Matrix'],
    ['09_clustering_13provinces_dendrogram_and_pca.png', 'Hình 09 · Gom cụm 13 tỉnh: Elbow/Silhouette, Ward Dendrogram & PCA 2D'],
    ['10_association_rules_lift_confidence.png', 'Hình 10 · Luật kết hợp định lượng Apriori: Support, Confidence, Lift & Leverage']
  ];
  document.getElementById('figGallery').innerHTML = figs.map(([f, cap]) => `
    <div class="gal-item" onclick="openZoom('../results/figures/${f}')">
      <img src="../results/figures/${f}" alt="${cap}" loading="lazy">
      <div class="cap">${cap}</div>
    </div>
  `).join('');
}

function openZoom(src) {
  document.getElementById('lightboxImg').src = src;
  document.getElementById('lightbox').classList.add('open');
}

// Boot all tabs
initTab1();
renderTab2();
initTab3();
renderClusters();
renderRules();
initGallery();
</script>
</body>
</html>
"""

html_out = html_template.replace('__PAYLOAD_JSON__', payload_json)
with open('dashboard/index.html', 'w', encoding='utf-8') as f:
    f.write(html_out)

print('=== DONE: INTERACTIVE OFFLINE DASHBOARD GENERATED ===')
print(f'Output: dashboard/index.html ({len(html_out):,} bytes)')
print(f'Provinces embedded: {len(provinces_meta)} | Track B models: {len(reg_b)} | Classifiers: {len(clf_all)} | Rules DX: {len(payload["rules_dx"])}')
print(f'Tier tertiles (dev <= 2022): q33={q33}, q67={q67}')
