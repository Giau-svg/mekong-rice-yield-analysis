import os
os.environ['MPLCONFIGDIR'] = os.path.abspath('tmp/mpl-cache')
os.makedirs('tmp/mpl-cache', exist_ok=True)
os.makedirs('results/metrics', exist_ok=True)
os.makedirs('results/figures', exist_ok=True)

import json
import itertools
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import cdist
from sklearn.preprocessing import StandardScaler, label_binarize
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression, Ridge, Lasso, HuberRegressor, LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    mean_absolute_error, accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, roc_curve, confusion_matrix,
    silhouette_score, calinski_harabasz_score,
    adjusted_rand_score, normalized_mutual_info_score,
    fowlkes_mallows_score, rand_score
)
from sklearn.cluster import KMeans, AgglomerativeClustering, BisectingKMeans, DBSCAN, MeanShift
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style='whitegrid', context='notebook')

# =============================================================================
# 0. LOAD CLEANED DATASETS
# =============================================================================
t1 = pd.read_csv('data/processed/tier1_core_3seasons_model_ready.csv')
t2_dx = pd.read_csv('data/processed/tier2_delta13_dong_xuan_model_ready.csv')
t2_comb = pd.read_csv('data/processed/tier2_delta13_combined_ht_td_model_ready.csv')
t2_all = pd.concat([t2_dx, t2_comb], ignore_index=True)

PARSIMONIOUS_METEO = [
    'vpd_mean_kpa',
    'precip_total_mm',
    'ws2m_mean_ms',
    'pre_season_rain_90d_mm',
    'oni_pre_season'
]

CANDIDATE_STEPWISE_METEO = [
    't2m_mean_c', 't2m_max_mean_c', 'precip_total_mm', 'rh2m_mean_pct',
    'ws2m_mean_ms', 'vpd_mean_kpa', 'hot_days_gt35c', 'dry_days_lt1mm',
    'pre_season_rain_90d_mm', 'oni_pre_season'
]

# =============================================================================
# MODULE 1 (BUOI 02): DESCRIPTIVE SUMMARY & 3-SIGMA / IQR OUTLIER AUDIT
# =============================================================================
desc_cols = ['yield_t_ha', 'area_ha', 'production_t', 't2m_mean_c', 't2m_max_mean_c',
             'precip_total_mm', 'rh2m_mean_pct', 'ws2m_mean_ms', 'vpd_mean_kpa',
             'hot_days_gt35c', 'dry_days_lt1mm', 'pre_season_rain_90d_mm', 'oni_pre_season']

desc_rows = []
outlier_rows = []
for ds_name, df in [
    ('track_b_3seasons_90', t1),
    ('track_a_dx_13prov_127', t2_dx),
    ('track_a_ht_td_13prov_130', t2_comb)
]:
    for col in desc_cols:
        s = df[col].astype(float)
        q1, med, q3 = s.quantile([0.25, 0.5, 0.75])
        iqr = q3 - q1
        mean_v, std_v = s.mean(), s.std(ddof=1)
        z = (s - mean_v) / (std_v + 1e-12)
        n_3s = int((z.abs() > 3.0).sum())
        n_iqr = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
        desc_rows.append({
            'dataset': ds_name, 'feature': col, 'count': int(s.count()),
            'missing': int(s.isna().sum()),
            'mean': round(float(mean_v), 4), 'std': round(float(std_v), 4),
            'min': round(float(s.min()), 4), 'q1': round(float(q1), 4),
            'median': round(float(med), 4), 'q3': round(float(q3), 4),
            'max': round(float(s.max()), 4), 'iqr': round(float(iqr), 4),
            'skewness': round(float(stats.skew(s)), 4),
            'outliers_3sigma_count': n_3s, 'outliers_iqr_count': n_iqr
        })

    # Record-level 3-sigma & IQR audit specifically for yield_t_ha
    y = df['yield_t_ha'].astype(float)
    z_y = (y - y.mean()) / (y.std(ddof=1) + 1e-12)
    q1, q3 = y.quantile([0.25, 0.75])
    iqr = q3 - q1
    lo_iqr, hi_iqr = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    flagged = df[(z_y.abs() > 3.0) | (y < lo_iqr) | (y > hi_iqr)]
    for idx, r in flagged.iterrows():
        zv = float(z_y.loc[idx])
        outlier_rows.append({
            'dataset': ds_name,
            'province': r['province'],
            'ecological_subregion': r['ecological_subregion'],
            'harvest_year': int(r['harvest_year']),
            'season': r['season'],
            'yield_t_ha': float(r['yield_t_ha']),
            'z_score': round(zv, 3),
            'flag_3sigma': bool(abs(zv) > 3.0),
            'flag_iqr_1_5': bool((r['yield_t_ha'] < lo_iqr) or (r['yield_t_ha'] > hi_iqr)),
            'domain_outlier_flag': r['domain_outlier_flag'],
            'handling_decision': 'Retain real agro-disaster + evaluate Dual-Regime & Huber Loss'
        })

desc_df = pd.DataFrame(desc_rows)
outlier_df = pd.DataFrame(outlier_rows)
desc_df.to_csv('results/metrics/eda_descriptive_summary.csv', index=False, encoding='utf-8-sig')
outlier_df.to_csv('results/metrics/eda_3sigma_outliers_audit.csv', index=False, encoding='utf-8-sig')

# =============================================================================
# MODULE 2 (BUOI 03 & 04): EXACT OLS INFERENCE, 4 ASSUMPTIONS (GD1-GD4),
#                          STEPWISE/BACKWARD SELECTION, RIDGE/LASSO COEFS
# =============================================================================
def compute_vif_dict(X_df):
    if X_df.shape[1] < 2:
        return {c: 1.0 for c in X_df.columns}
    X = X_df.astype(float).values
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-12)
    out = {}
    for i, c in enumerate(X_df.columns):
        others = np.delete(X, i, axis=1)
        r2 = LinearRegression().fit(others, X[:, i]).score(others, X[:, i])
        out[c] = round(float(np.inf if r2 >= 0.999999 else 1.0 / (1.0 - r2)), 2)
    return out

def fit_ols_full(X_df, y, model_name):
    y = np.asarray(y, dtype=float)
    n = len(y)
    feat_names = list(X_df.columns)
    X_raw = X_df.astype(float).values
    X = np.column_stack([np.ones(n), X_raw])
    col_names = ['const'] + feat_names
    p = X.shape[1]  # includes intercept
    k = p - 1
    df_resid = n - p

    # Exact OLS via QR/lstsq + pinv covariance
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ beta
    resid = y - y_hat

    rss = float(np.sum(resid ** 2))
    tss = float(np.sum((y - y.mean()) ** 2))
    ess = tss - rss
    r2 = 1.0 - rss / tss if tss > 0 else 0.0
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / df_resid

    # GD1: Overall F-test
    ms_reg = ess / k
    ms_res = rss / df_resid
    f_stat = ms_reg / ms_res if ms_res > 0 else np.inf
    f_pval = float(1.0 - stats.f.cdf(f_stat, k, df_resid))

    # Classical & HC3 standard errors
    XtX_inv = np.linalg.pinv(X.T @ X)
    cov_classical = ms_res * XtX_inv
    se_classical = np.sqrt(np.maximum(np.diag(cov_classical), 0.0))
    t_stats = beta / (se_classical + 1e-15)
    p_vals = 2.0 * (1.0 - stats.t.cdf(np.abs(t_stats), df_resid))

    # HC3 robust standard errors (MacKinnon & White, 1985)
    H_diag = np.sum((X @ XtX_inv) * X, axis=1)
    weights_hc3 = (resid ** 2) / np.maximum((1.0 - H_diag) ** 2, 1e-8)
    meat_hc3 = X.T @ (X * weights_hc3[:, None])
    cov_hc3 = XtX_inv @ meat_hc3 @ XtX_inv
    se_hc3 = np.sqrt(np.maximum(np.diag(cov_hc3), 0.0))
    t_hc3 = beta / (se_hc3 + 1e-15)
    p_hc3 = 2.0 * (1.0 - stats.t.cdf(np.abs(t_hc3), df_resid))

    # Log-likelihood, AIC, BIC (matching statsmodels & Slide 35-36 Buoi 04: AIC=2k-2lnL, BIC=k*ln(n)-2lnL)
    sigma2_mle = max(rss / n, 1e-15)
    log_lik = -0.5 * n * (np.log(2.0 * np.pi) + 1.0 + np.log(sigma2_mle))
    aic = 2.0 * p - 2.0 * log_lik
    bic = p * np.log(n) - 2.0 * log_lik

    # GD2: Shapiro-Wilk Normality Test on residuals & Mean ~ 0
    shapiro_w, shapiro_p = stats.shapiro(resid)
    resid_mean = float(np.mean(resid))
    resid_std = float(np.std(resid, ddof=1))

    # GD3: VIF among predictors
    vif_map = compute_vif_dict(X_df)
    max_vif = max(vif_map.values()) if vif_map else 1.0

    # GD4: Breusch-Pagan test (Koenker LM = n * R2_aux)
    e2 = resid ** 2
    e2_tss = float(np.sum((e2 - e2.mean()) ** 2))
    beta_bp, _, _, _ = np.linalg.lstsq(X, e2, rcond=None)
    e2_rss_bp = float(np.sum((e2 - X @ beta_bp) ** 2))
    r2_bp = max(0.0, 1.0 - e2_rss_bp / e2_tss) if e2_tss > 0 else 0.0
    bp_lm = n * r2_bp
    bp_p = float(1.0 - stats.chi2.cdf(bp_lm, k))

    # GD4: White test (auxiliary regression with X, X^2, and cross-products; fallback to fitted^2 if rank too large)
    white_cols = [np.ones(n)]
    for j in range(X_raw.shape[1]):
        white_cols.append(X_raw[:, j])
    for j in range(X_raw.shape[1]):
        col_sq = X_raw[:, j] ** 2
        if np.std(col_sq) > 1e-10:
            white_cols.append(col_sq)
    for j1 in range(X_raw.shape[1]):
        for j2 in range(j1 + 1, X_raw.shape[1]):
            prod = X_raw[:, j1] * X_raw[:, j2]
            if np.std(prod) > 1e-10:
                white_cols.append(prod)
    Z_full = np.column_stack(white_cols)
    # Orthogonalize via SVD to get exact numerical rank
    U_z, S_z, _ = np.linalg.svd(Z_full, full_matrices=False)
    rank_z = int(np.sum(S_z > 1e-8 * S_z[0]))
    if rank_z < n - 6 and rank_z > 1:
        # Use reduced full-rank basis of Z_full
        Z_use = U_z[:, :rank_z]
        white_df = rank_z - 1
        white_variant = 'full_squares_and_interactions'
    else:
        Z_use = np.column_stack([np.ones(n), y_hat, y_hat ** 2])
        white_df = 2
        white_variant = 'fitted_quadratic_white_special'
    beta_w, _, _, _ = np.linalg.lstsq(Z_use, e2, rcond=None)
    e2_rss_w = float(np.sum((e2 - Z_use @ beta_w) ** 2))
    r2_w = max(0.0, 1.0 - e2_rss_w / e2_tss) if e2_tss > 0 else 0.0
    white_lm = n * r2_w
    white_p = float(1.0 - stats.chi2.cdf(white_lm, white_df))

    def sig_stars(pv):
        if pv < 0.001: return '***'
        if pv < 0.01: return '**'
        if pv < 0.05: return '*'
        if pv < 0.10: return '.'
        return 'ns'

    coef_rows = []
    for i, cname in enumerate(col_names):
        coef_rows.append({
            'model': model_name,
            'feature': cname,
            'coef': round(float(beta[i]), 5),
            'se_classical': round(float(se_classical[i]), 5),
            't_stat': round(float(t_stats[i]), 4),
            'p_value': round(float(p_vals[i]), 5),
            'sig': sig_stars(p_vals[i]),
            'se_hc3': round(float(se_hc3[i]), 5),
            't_hc3': round(float(t_hc3[i]), 4),
            'p_hc3': round(float(p_hc3[i]), 5),
            'vif': vif_map.get(cname, np.nan)
        })

    diag = {
        'model': model_name,
        'n': n, 'k_predictors': k, 'df_resid': df_resid,
        'r2': round(r2, 4), 'adj_r2': round(adj_r2, 4),
        'f_stat_gd1': round(float(f_stat), 4), 'f_pvalue_gd1': round(f_pval, 6),
        'gd1_linearity_pass': bool(f_pval < 0.05),
        'log_likelihood': round(float(log_lik), 3),
        'aic': round(float(aic), 3), 'bic': round(float(bic), 3),
        'resid_mean_gd2': round(resid_mean, 6), 'resid_std': round(resid_std, 4),
        'resid_skew': round(float(stats.skew(resid)), 4),
        'shapiro_w_gd2': round(float(shapiro_w), 4), 'shapiro_p_gd2': round(float(shapiro_p), 6),
        'gd2_normality_pass': bool(shapiro_p >= 0.05),
        'max_vif_gd3': round(float(max_vif), 2),
        'gd3_no_multicollinearity_pass': bool(max_vif < 10.0),
        'bp_lm_gd4': round(float(bp_lm), 4), 'bp_p_gd4': round(float(bp_p), 6),
        'white_lm_gd4': round(float(white_lm), 4), 'white_p_gd4': round(float(white_p), 6),
        'white_df': white_df, 'white_variant': white_variant,
        'gd4_homoscedasticity_pass': bool((bp_p >= 0.05) and (white_p >= 0.05))
    }
    return pd.DataFrame(coef_rows), diag, y_hat, resid

def prepare_demeaned_xy(df, group_cols, feat_cols, include_year=True):
    tmp = df.copy()
    y_dem = tmp['yield_t_ha'] - tmp.groupby(group_cols)['yield_t_ha'].transform('mean')
    X_out = pd.DataFrame(index=tmp.index)
    for c in feat_cols:
        d = tmp[c] - tmp.groupby(group_cols)[c].transform('mean')
        X_out[c] = d / (d.std(ddof=0) + 1e-12)
    if include_year:
        X_out['year_z'] = (tmp['harvest_year'] - tmp['harvest_year'].mean()) / (tmp['harvest_year'].std(ddof=0) + 1e-12)
    return X_out, y_dem.values

# Fit full OLS diagnostics on 5 core specifications
ols_coef_tables = []
ols_diag_rows = []
ols_resid_store = {}

# 1) Track B Direct One-Hot (Province + Season + 5 Ortho Weather + Year, n=90)
X_b_oh_cat = pd.get_dummies(t1[['province_id', 'season']], drop_first=True, dtype=float)
X_b_oh_num = t1[PARSIMONIOUS_METEO + ['harvest_year']].copy()
X_b_oh_num = (X_b_oh_num - X_b_oh_num.mean()) / (X_b_oh_num.std(ddof=0) + 1e-12)
X_b_oh = pd.concat([X_b_oh_cat.reset_index(drop=True), X_b_oh_num.reset_index(drop=True)], axis=1)
ct, dg, yh, rs = fit_ols_full(X_b_oh, t1['yield_t_ha'].values, 'TrackB_Direct_OneHot_Ortho5_Year_n90')
ols_coef_tables.append(ct); ols_diag_rows.append(dg); ols_resid_store['TrackB_Direct'] = (yh, rs, dg)

# 2) Track B Demeaned Anomaly (Province x Season Fixed-Effects removed, n=90)
X_b_dem, y_b_dem = prepare_demeaned_xy(t1, ['province_id', 'season'], PARSIMONIOUS_METEO, include_year=True)
ct, dg, yh, rs = fit_ols_full(X_b_dem, y_b_dem, 'TrackB_FE_Demeaned_Ortho5_Year_n90')
ols_coef_tables.append(ct); ols_diag_rows.append(dg); ols_resid_store['TrackB_Demeaned'] = (yh, rs, dg)

# 3) Track A Dong Xuan FULL (13 provinces, n=127 — includes 2 salinity failures)
X_a_full, y_a_full = prepare_demeaned_xy(t2_dx, ['province_id'], PARSIMONIOUS_METEO, include_year=True)
ct, dg, yh, rs = fit_ols_full(X_a_full, y_a_full, 'TrackA_DX_Full_13Prov_n127')
ols_coef_tables.append(ct); ols_diag_rows.append(dg); ols_resid_store['TrackA_DX_Full'] = (yh, rs, dg)

# 4) Track A Dong Xuan EX-SALINITY (13 provinces, n=125 — excludes Ben Tre 2016/2020 failures)
t2_dx_nosal = t2_dx[t2_dx['domain_outlier_flag'] == 'none'].copy()
X_a_nosal, y_a_nosal = prepare_demeaned_xy(t2_dx_nosal, ['province_id'], PARSIMONIOUS_METEO, include_year=True)
ct, dg, yh, rs = fit_ols_full(X_a_nosal, y_a_nosal, 'TrackA_DX_ExSalinity_13Prov_n125')
ols_coef_tables.append(ct); ols_diag_rows.append(dg); ols_resid_store['TrackA_DX_NoSal'] = (yh, rs, dg)

# 5) Track A Combined HT-TD (13 provinces, n=130)
X_a_comb, y_a_comb = prepare_demeaned_xy(t2_comb, ['province_id'], PARSIMONIOUS_METEO, include_year=True)
ct, dg, yh, rs = fit_ols_full(X_a_comb, y_a_comb, 'TrackA_HTTD_13Prov_n130')
ols_coef_tables.append(ct); ols_diag_rows.append(dg); ols_resid_store['TrackA_HTTD'] = (yh, rs, dg)

ols_coefs_all = pd.concat(ols_coef_tables, ignore_index=True)
ols_diag_df = pd.DataFrame(ols_diag_rows)
ols_coefs_all.to_csv('results/metrics/ols_full_coefficients_table.csv', index=False, encoding='utf-8-sig')
ols_diag_df.to_csv('results/metrics/ols_assumptions_diagnostics_gd1_to_gd4.csv', index=False, encoding='utf-8-sig')

# Feature Selection (Forward, Backward p<0.05, Stepwise AIC) on Track B Dev (2015-2022, n=72)
t1_dev = t1[t1['harvest_year'] <= 2022].copy()
t1_test = t1[t1['harvest_year'] >= 2023].copy()
X_fs_pool, y_fs_dev = prepare_demeaned_xy(t1_dev, ['province_id', 'season'], CANDIDATE_STEPWISE_METEO, include_year=True)
all_cand = list(X_fs_pool.columns)

def ols_aic(cols):
    _, dg, _, _ = fit_ols_full(X_fs_pool[cols], y_fs_dev, 'tmp')
    return dg['aic'], dg

# Forward selection by AIC
fwd_cols = []
best_aic = np.inf
while len(fwd_cols) < len(all_cand):
    scores = []
    for c in all_cand:
        if c not in fwd_cols:
            a, _ = ols_aic(fwd_cols + [c])
            scores.append((a, c))
    scores.sort()
    if scores[0][0] < best_aic - 1e-4:
        best_aic = scores[0][0]
        fwd_cols.append(scores[0][1])
    else:
        break

# Backward elimination by p-value <= 0.05
bwd_cols = list(all_cand)
while len(bwd_cols) > 1:
    ct_tmp, _, _, _ = fit_ols_full(X_fs_pool[bwd_cols], y_fs_dev, 'tmp')
    ct_no_c = ct_tmp[ct_tmp['feature'] != 'const']
    worst = ct_no_c.sort_values('p_value', ascending=False).iloc[0]
    if worst['p_value'] > 0.05:
        bwd_cols.remove(worst['feature'])
    else:
        break

# Stepwise bidirectional selection by AIC
step_cols = []
cur_aic = np.inf
while True:
    changed = False
    # Try adding best feature
    add_cands = [(ols_aic(step_cols + [c])[0], c) for c in all_cand if c not in step_cols]
    if add_cands:
        add_cands.sort()
        if add_cands[0][0] < cur_aic - 1e-4:
            step_cols.append(add_cands[0][1])
            cur_aic = add_cands[0][0]
            changed = True
    # Try dropping any feature
    if len(step_cols) > 1:
        drop_cands = [(ols_aic([x for x in step_cols if x != c])[0], c) for c in step_cols]
        drop_cands.sort()
        if drop_cands[0][0] < cur_aic - 1e-4:
            step_cols.remove(drop_cands[0][1])
            cur_aic = drop_cands[0][0]
            changed = True
    if not changed:
        break

def eval_subset_cv_test(feat_list, use_ridge=False):
    raw_feats = [f for f in feat_list if f != 'year_z']
    inc_yr = 'year_z' in feat_list
    def fit_pred(tr, ev):
        med = tr.groupby(['province_id', 'season'])['yield_t_ha'].median().to_dict()
        yb_tr = np.array([med[(r['province_id'], r['season'])] for _, r in tr.iterrows()])
        yb_ev = np.array([med[(r['province_id'], r['season'])] for _, r in ev.iterrows()])
        y_res = tr['yield_t_ha'].values - yb_tr
        Xtr, Xev = pd.DataFrame(index=tr.index), pd.DataFrame(index=ev.index)
        if raw_feats:
            gc = tr.groupby(['province_id', 'season'])[raw_feats].median()
            for c in raw_feats:
                Xtr[c] = [r[c] - gc.loc[(r['province_id'], r['season']), c] for _, r in tr.iterrows()]
                Xev[c] = [r[c] - gc.loc[(r['province_id'], r['season']), c] for _, r in ev.iterrows()]
                sd = Xtr[c].std(ddof=0) or 1.0
                Xtr[c] /= sd; Xev[c] /= sd
        if inc_yr:
            ym, ys = tr['harvest_year'].mean(), tr['harvest_year'].std(ddof=0) or 1.0
            Xtr['year_z'] = (tr['harvest_year'] - ym) / ys
            Xev['year_z'] = (ev['harvest_year'] - ym) / ys
        mdl = Ridge(alpha=25.0) if use_ridge else LinearRegression()
        mdl.fit(Xtr, y_res)
        return yb_ev + mdl.predict(Xev)
    # Expanding CV 2019-2022
    oy, op = [], []
    for yr in (2019, 2020, 2021, 2022):
        tr = t1_dev[t1_dev['harvest_year'] < yr]
        va = t1_dev[t1_dev['harvest_year'] == yr]
        oy.extend(va['yield_t_ha'].values)
        op.extend(fit_pred(tr, va))
    te_pred = fit_pred(t1_dev, t1_test)
    return round(float(mean_absolute_error(oy, op)), 4), round(float(mean_absolute_error(t1_test['yield_t_ha'], te_pred)), 4)

fs_rows = []
for method_name, cols in [
    ('Full_Candidate_10Weather_Plus_Year', all_cand),
    ('Forward_Selection_AIC', fwd_cols),
    ('Backward_Elimination_p005', bwd_cols),
    ('Stepwise_Bidirectional_AIC', step_cols),
    ('Domain_Orthogonal_5_Plus_Year', PARSIMONIOUS_METEO + ['year_z'])
]:
    _, dg, _, _ = fit_ols_full(X_fs_pool[cols], y_fs_dev, method_name)
    cv_ols, te_ols = eval_subset_cv_test(cols, use_ridge=False)
    cv_rdg, te_rdg = eval_subset_cv_test(cols, use_ridge=True)
    fs_rows.append({
        'selection_method': method_name,
        'n_features': len(cols),
        'selected_features': ', '.join(cols),
        'train_r2': dg['r2'], 'adj_r2': dg['adj_r2'],
        'aic': dg['aic'], 'bic': dg['bic'], 'max_vif': dg['max_vif_gd3'],
        'ols_cv_mae': cv_ols, 'ols_test_mae': te_ols,
        'ridge_cv_mae': cv_rdg, 'ridge_test_mae': te_rdg
    })
fs_df = pd.DataFrame(fs_rows)
fs_df.to_csv('results/metrics/feature_selection_stepwise_comparison.csv', index=False, encoding='utf-8-sig')

# OLS vs Ridge vs Lasso vs Huber standardized coefficients on Track B Dev (2015-2022)
X_reg_dev, y_reg_dev = prepare_demeaned_xy(t1_dev, ['province_id', 'season'], PARSIMONIOUS_METEO, include_year=True)
ols_m = LinearRegression().fit(X_reg_dev, y_reg_dev)
rdg_m = Ridge(alpha=25.0).fit(X_reg_dev, y_reg_dev)
las_m = Lasso(alpha=0.03, max_iter=5000, random_state=42).fit(X_reg_dev, y_reg_dev)
hub_m = HuberRegressor(alpha=10.0, epsilon=1.35, max_iter=1000).fit(X_reg_dev, y_reg_dev)
reg_coef_df = pd.DataFrame({
    'feature': list(X_reg_dev.columns),
    'OLS_unregularized': np.round(ols_m.coef_, 4),
    'Ridge_L2_a25': np.round(rdg_m.coef_, 4),
    'Lasso_L1_a003': np.round(las_m.coef_, 4),
    'Huber_Robust_a10': np.round(hub_m.coef_, 4)
})
reg_coef_df.to_csv('results/metrics/regularization_ols_ridge_lasso_huber_coefs.csv', index=False, encoding='utf-8-sig')

# --- Figure 7: OLS 4-Assumptions Diagnostics (GD1-GD4) ---
fig, axes = plt.subplots(2, 2, figsize=(14.5, 10.2))
yh_b, rs_b, dg_b = ols_resid_store['TrackB_Demeaned']
yh_af, rs_af, dg_af = ols_resid_store['TrackA_DX_Full']
yh_an, rs_an, dg_an = ols_resid_store['TrackA_DX_NoSal']

# Panel A: Residual Hist + KDE vs Normal (GD2)
sns.histplot(rs_b, bins=16, kde=True, stat='density', color='#4299e1', alpha=0.55, ax=axes[0, 0], label='Phân phối phần dư (KDE)')
xs = np.linspace(rs_b.min() - 0.1, rs_b.max() + 0.1, 200)
axes[0, 0].plot(xs, stats.norm.pdf(xs, rs_b.mean(), rs_b.std(ddof=1)), 'r--', lw=2, label='Phân phối chuẩn lý thuyết')
axes[0, 0].axvline(0, color='black', ls=':', lw=1.2)
axes[0, 0].set_title(f"A. GĐ2: Phân phối phần dư OLS Tuyến B (n=90)\nShapiro-Wilk W={dg_b['shapiro_w_gd2']:.4f}, p={dg_b['shapiro_p_gd2']:.4f} | mean={dg_b['resid_mean_gd2']:.4f}", fontsize=10, fontweight='bold')
axes[0, 0].set_xlabel('Phần dư OLS (tấn/ha)')
axes[0, 0].legend(fontsize=8.5)

# Panel B: Q-Q Plot (GD2)
(osm, osr), (slope, intercept, _) = stats.probplot(rs_b, dist='norm')
axes[0, 1].scatter(osm, osr, color='#2b6cb0', alpha=0.8, s=35, edgecolor='white')
axes[0, 1].plot(osm, slope * osm + intercept, 'r--', lw=1.8, label='Đường chuẩn 45°')
axes[0, 1].set_title('B. GĐ2: Biểu đồ Q-Q Plot phần dư Tuyến B\nKiểm tra trực quan giả định phân phối chuẩn', fontsize=10, fontweight='bold')
axes[0, 1].set_xlabel('Phân vị lý thuyết chuẩn (Theoretical Quantiles)')
axes[0, 1].set_ylabel('Phần dư thực nghiệm (Sample Quantiles)')
axes[0, 1].legend(fontsize=8.5)

# Panel C: Residuals vs Fitted (GD1 Linearity & GD4 Homoscedasticity)
axes[1, 0].scatter(yh_b, rs_b, color='#2f855a', alpha=0.8, s=40, edgecolor='white')
axes[1, 0].axhline(0, color='#e53e3e', ls='--', lw=1.5)
f_p_str = '< 1e-10' if dg_b['f_pvalue_gd1'] < 1e-10 else f"= {dg_b['f_pvalue_gd1']:.4g}"
axes[1, 0].set_title(f"C. GĐ1 & GĐ4: Phần dư vs. Giá trị dự báo (Tuyến B)\nF-test p {f_p_str} | Breusch-Pagan p={dg_b['bp_p_gd4']:.4f} | White p={dg_b['white_p_gd4']:.4f}", fontsize=10, fontweight='bold')
axes[1, 0].set_xlabel('Giá trị phần dư năng suất dự báo ŷ (tấn/ha)')
axes[1, 0].set_ylabel('Phần dư e = y - ŷ (tấn/ha)')

# Panel D: Track A DX Full (127) vs Ex-Salinity (125) Residual Tail Comparison
sns.kdeplot(rs_af, color='#c53030', lw=2.2, fill=True, alpha=0.2, ax=axes[1, 1],
            label=f"Đủ 127 dòng (Shapiro p<1e-10, AIC={dg_af['aic']:.1f})")
sns.kdeplot(rs_an, color='#2b6cb0', lw=2.2, fill=True, alpha=0.25, ax=axes[1, 1],
            label=f"Bỏ 2 điểm mất trắng (125) (Shapiro p<1e-5, AIC={dg_an['aic']:.1f})")
axes[1, 1].axvline(0, color='black', ls=':', lw=1.2)
axes[1, 1].annotate('Đuôi cực đoan hạn mặn\nBến Tre 2016 & 2020\n→ Bác bỏ GĐ2 (Shapiro p<0,001)\n→ Dùng Huber + Dual-Regime',
                    xy=(-4.4, 0.03), xytext=(-4.9, 0.35),
                    arrowprops=dict(arrowstyle='->', color='#9b2c2c', lw=1.4),
                    fontsize=8.5, fontweight='bold', color='#9b2c2c')
axes[1, 1].set_title('D. Bằng chứng thống kê trên Tuyến A (13 tỉnh ĐX)\nVi phạm GĐ2 (đuôi nặng do hạn mặn) → chọn Huber Loss', fontsize=10, fontweight='bold')
axes[1, 1].set_xlabel('Phần dư OLS (tấn/ha)')
axes[1, 1].legend(fontsize=8, loc='upper left')

plt.tight_layout()
plt.savefig('results/figures/07_ols_assumptions_diagnostics_gd1_gd4.png', dpi=300)
plt.close()

# =============================================================================
# MODULE 3 (BUOI 08, 09, 10): MULTI-MODEL CLASSIFICATION BENCHMARK
# =============================================================================
# Task C1: 3-Class Yield Tier (Thap / TrungBinh / Cao) on Track A All 13 provinces (n=257)
#          Thresholds strictly fit on dev <= 2022 (n=205), evaluated on Locked Test 2023-2024 (n=52)
# Task C2: Binary Yield Risk (below_expected_trend = 1) on Track A All 13 provinces (n=257)
t2_dev = t2_all[t2_all['harvest_year'] <= 2022].copy().reset_index(drop=True)
t2_te = t2_all[t2_all['harvest_year'] >= 2023].copy().reset_index(drop=True)

q33, q67 = np.quantile(t2_dev['yield_t_ha'], [1/3, 2/3])
tier_labels = ['Thấp', 'Trung bình', 'Cao']
y_c1_dev = pd.cut(t2_dev['yield_t_ha'], [-np.inf, q33, q67, np.inf], labels=[0, 1, 2]).astype(int).values
y_c1_te = pd.cut(t2_te['yield_t_ha'], [-np.inf, q33, q67, np.inf], labels=[0, 1, 2]).astype(int).values

# Task C2 Binary Target: below_expected_trend (strictly computed from dev structural trend)
def make_c2_binary_target(tr_df, ev_df):
    med = tr_df.groupby(['province_id', 'season'])['yield_t_ha'].median().to_dict()
    tr_base = np.array([med[(r['province_id'], r['season'])] for _, r in tr_df.iterrows()])
    ev_base = np.array([med[(r['province_id'], r['season'])] for _, r in ev_df.iterrows()])
    ym, ys = tr_df['harvest_year'].mean(), tr_df['harvest_year'].std(ddof=0) or 1.0
    trend_mdl = Ridge(alpha=1.0).fit(((tr_df['harvest_year'].values - ym) / ys).reshape(-1, 1), tr_df['yield_t_ha'].values - tr_base)
    tr_exp = tr_base + trend_mdl.predict(((tr_df['harvest_year'].values - ym) / ys).reshape(-1, 1))
    ev_exp = ev_base + trend_mdl.predict(((ev_df['harvest_year'].values - ym) / ys).reshape(-1, 1))
    return (tr_df['yield_t_ha'].values < tr_exp).astype(int), (ev_df['yield_t_ha'].values < ev_exp).astype(int)

y_c2_dev, y_c2_te = make_c2_binary_target(t2_dev, t2_te)

def build_clf_features(tr_df, ev_df, regime='weather_subregion'):
    if regime == 'weather_subregion':
        tr_c = pd.get_dummies(tr_df[['ecological_subregion']], dtype=float)
        ev_c = pd.get_dummies(ev_df[['ecological_subregion']], dtype=float).reindex(columns=tr_c.columns, fill_value=0.0)
        sc = StandardScaler().fit(tr_df[PARSIMONIOUS_METEO])
        tr_n = pd.DataFrame(sc.transform(tr_df[PARSIMONIOUS_METEO]), columns=PARSIMONIOUS_METEO)
        ev_n = pd.DataFrame(sc.transform(ev_df[PARSIMONIOUS_METEO]), columns=PARSIMONIOUS_METEO)
        return pd.concat([tr_n, tr_c.reset_index(drop=True)], axis=1), pd.concat([ev_n, ev_c.reset_index(drop=True)], axis=1)
    elif regime == 'full_context':
        tr_c = pd.get_dummies(tr_df[['province_id', 'season']], dtype=float)
        ev_c = pd.get_dummies(ev_df[['province_id', 'season']], dtype=float).reindex(columns=tr_c.columns, fill_value=0.0)
        cols = PARSIMONIOUS_METEO + ['harvest_year']
        sc = StandardScaler().fit(tr_df[cols])
        tr_n = pd.DataFrame(sc.transform(tr_df[cols]), columns=cols)
        ev_n = pd.DataFrame(sc.transform(ev_df[cols]), columns=cols)
        return pd.concat([tr_n, tr_c.reset_index(drop=True)], axis=1), pd.concat([ev_n, ev_c.reset_index(drop=True)], axis=1)
    elif regime == 'weather_anomaly_subregion':
        # Demean weather by province x season using tr_df ONLY
        gc = tr_df.groupby(['province_id', 'season'])[PARSIMONIOUS_METEO].median()
        g_glob = tr_df[PARSIMONIOUS_METEO].median()
        def dem(d):
            out = pd.DataFrame(index=d.index)
            for c in PARSIMONIOUS_METEO:
                out[c] = [r[c] - (gc.loc[(r['province_id'], r['season']), c] if (r['province_id'], r['season']) in gc.index else g_glob[c]) for _, r in d.iterrows()]
            return out
        tr_d, ev_d = dem(tr_df), dem(ev_df)
        sc = StandardScaler().fit(tr_d)
        tr_n = pd.DataFrame(sc.transform(tr_d), columns=PARSIMONIOUS_METEO)
        ev_n = pd.DataFrame(sc.transform(ev_d), columns=PARSIMONIOUS_METEO)
        tr_c = pd.get_dummies(tr_df[['ecological_subregion']], dtype=float)
        ev_c = pd.get_dummies(ev_df[['ecological_subregion']], dtype=float).reindex(columns=tr_c.columns, fill_value=0.0)
        return pd.concat([tr_n, tr_c.reset_index(drop=True)], axis=1), pd.concat([ev_n, ev_c.reset_index(drop=True)], axis=1)

def get_classifiers(is_multiclass=True):
    clfs = [
        ('Dummy_Baseline', lambda: DummyClassifier(strategy='most_frequent')),
        ('Logistic_Multinomial' if is_multiclass else 'Logistic_Binary', lambda: LogisticRegression(C=1.0, max_iter=1000, class_weight='balanced' if not is_multiclass else None, random_state=42)),
    ]
    if is_multiclass:
        clfs.append(('Logistic_OvR', lambda: OneVsRestClassifier(LogisticRegression(C=1.0, max_iter=1000, random_state=42))))
    clfs.extend([
        ('DecisionTree_CART', lambda: DecisionTreeClassifier(max_depth=4, min_samples_leaf=6, class_weight='balanced' if not is_multiclass else None, random_state=42)),
        ('RandomForest', lambda: RandomForestClassifier(n_estimators=200, max_depth=5, min_samples_leaf=4, class_weight='balanced' if not is_multiclass else None, random_state=42)),
        ('GradientBoosting', lambda: GradientBoostingClassifier(n_estimators=80, learning_rate=0.05, max_depth=2, min_samples_leaf=5, random_state=42)),
        ('NaiveBayes_Gaussian', lambda: GaussianNB()),
        ('SVM_Linear', lambda: SVC(kernel='linear', C=1.0, probability=True, class_weight='balanced' if not is_multiclass else None, random_state=42)),
        ('SVM_RBF', lambda: SVC(kernel='rbf', C=2.0, probability=True, class_weight='balanced' if not is_multiclass else None, random_state=42)),
        ('MLP_ReLU', lambda: MLPClassifier(hidden_layer_sizes=(32, 16), activation='relu', alpha=1.0, max_iter=600, random_state=42)),
        ('MLP_Tanh', lambda: MLPClassifier(hidden_layer_sizes=(32, 16), activation='tanh', alpha=1.0, max_iter=600, random_state=42)),
    ])
    return clfs

def eval_clf_suite(task_name, regime, is_multiclass):
    rows = []
    roc_store = {}
    cm_store = {}
    tree_rules_text = None
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    X_dev_full, X_te_full = build_clf_features(t2_dev, t2_te, regime=regime)
    y_dev = y_c1_dev if is_multiclass else y_c2_dev
    y_te = y_c1_te if is_multiclass else y_c2_te

    for cname, factory in get_classifiers(is_multiclass=is_multiclass):
        # 1) 5-Fold Stratified CV on dev (Buoi 08-09 Slide 26)
        skf_y, skf_p, skf_prob = [], [], []
        for tr_i, va_i in skf.split(t2_dev, y_dev):
            tr_sub, va_sub = t2_dev.iloc[tr_i], t2_dev.iloc[va_i]
            Xtr, Xva = build_clf_features(tr_sub, va_sub, regime=regime)
            ytr, yva = y_dev[tr_i], y_dev[va_i]
            m = factory().fit(Xtr, ytr)
            skf_y.extend(yva)
            skf_p.extend(m.predict(Xva))
            skf_prob.append(m.predict_proba(Xva))
        skf_prob = np.vstack(skf_prob)
        skf_y = np.array(skf_y); skf_p = np.array(skf_p)

        # 2) Expanding-Window Temporal CV (2019-2022)
        exp_y, exp_p, exp_prob = [], [], []
        for yr in (2019, 2020, 2021, 2022):
            tr_m = t2_dev['harvest_year'] < yr
            va_m = t2_dev['harvest_year'] == yr
            tr_sub, va_sub = t2_dev[tr_m], t2_dev[va_m]
            Xtr, Xva = build_clf_features(tr_sub, va_sub, regime=regime)
            if is_multiclass:
                q1_f, q2_f = np.quantile(tr_sub['yield_t_ha'], [1/3, 2/3])
                ytr = pd.cut(tr_sub['yield_t_ha'], [-np.inf, q1_f, q2_f, np.inf], labels=[0, 1, 2]).astype(int).values
                yva = pd.cut(va_sub['yield_t_ha'], [-np.inf, q1_f, q2_f, np.inf], labels=[0, 1, 2]).astype(int).values
            else:
                ytr, yva = make_c2_binary_target(tr_sub, va_sub)
            m = factory().fit(Xtr, ytr)
            exp_y.extend(yva); exp_p.extend(m.predict(Xva))
            exp_prob.append(m.predict_proba(Xva))
        exp_prob = np.vstack(exp_prob)
        exp_y = np.array(exp_y); exp_p = np.array(exp_p)

        # 3) Final fit on full dev -> Locked Test 2023-2024
        final_m = factory().fit(X_dev_full, y_dev)
        te_p = final_m.predict(X_te_full)
        te_prob = final_m.predict_proba(X_te_full)

        if cname == 'DecisionTree_CART':
            tree_rules_text = export_text(final_m, feature_names=list(X_dev_full.columns))

        avg = 'macro' if is_multiclass else 'binary'
        def calc_auc(yt, pr):
            try:
                if is_multiclass:
                    return float(roc_auc_score(yt, pr, multi_class='ovr', average='macro'))
                return float(roc_auc_score(yt, pr[:, 1]))
            except Exception:
                return np.nan

        if not is_multiclass:
            roc_store[cname] = (y_te, te_prob[:, 1], calc_auc(y_te, te_prob))
        else:
            cm_store[cname] = confusion_matrix(y_te, te_p)
            roc_store[cname] = (y_te, te_prob, calc_auc(y_te, te_prob))

        rows.append({
            'task': task_name, 'feature_regime': regime, 'model': cname,
            'skf5_acc': round(float(accuracy_score(skf_y, skf_p)), 4),
            'skf5_f1': round(float(f1_score(skf_y, skf_p, average=avg, zero_division=0)), 4),
            'skf5_auc': round(calc_auc(skf_y, skf_prob), 4),
            'exp_cv_acc': round(float(accuracy_score(exp_y, exp_p)), 4),
            'exp_cv_f1': round(float(f1_score(exp_y, exp_p, average=avg, zero_division=0)), 4),
            'exp_cv_auc': round(calc_auc(exp_y, exp_prob), 4),
            'test_acc': round(float(accuracy_score(y_te, te_p)), 4),
            'test_precision': round(float(precision_score(y_te, te_p, average=avg, zero_division=0)), 4),
            'test_recall': round(float(recall_score(y_te, te_p, average=avg, zero_division=0)), 4),
            'test_f1': round(float(f1_score(y_te, te_p, average=avg, zero_division=0)), 4),
            'test_auc': round(calc_auc(y_te, te_prob), 4)
        })
    return pd.DataFrame(rows), roc_store, cm_store, tree_rules_text

c1_weather_df, roc_c1_w, cm_c1_w, rules_c1_w = eval_clf_suite('C1_3Class_YieldTier', 'weather_subregion', is_multiclass=True)
c1_full_df, roc_c1_f, cm_c1_f, rules_c1_f = eval_clf_suite('C1_3Class_YieldTier', 'full_context', is_multiclass=True)
c2_bin_df, roc_c2, _, rules_c2 = eval_clf_suite('C2_Binary_UnderperformRisk', 'weather_anomaly_subregion', is_multiclass=False)

clf_all_df = pd.concat([c1_weather_df, c1_full_df, c2_bin_df], ignore_index=True)
clf_all_df.to_csv('results/metrics/classification_multimodel_comparison.csv', index=False, encoding='utf-8-sig')

with open('results/metrics/classification_decision_tree_rules.txt', 'w', encoding='utf-8') as f:
    f.write('=== DECISION TREE (CART) IF-THEN RULES — TASK C1 (3-Class Yield Tier: Weather + Subregion) ===\n')
    f.write(f'Classes: 0 = Thap (< {q33:.2f}), 1 = Trung binh ({q33:.2f}-{q67:.2f}), 2 = Cao (>= {q67:.2f} t/ha)\n\n')
    f.write(rules_c1_w + '\n\n')
    f.write('=== DECISION TREE (CART) IF-THEN RULES — TASK C2 (Binary Risk: Weather Anomaly + Subregion) ===\n')
    f.write('Classes: 0 = Dat/Vuot ky vong, 1 = Sut giam duoi ky vong xu huong\n\n')
    f.write(rules_c2)

# --- Figure 8: Multi-Model Classification Benchmark (F1, ROC Curves, Confusion Matrix) ---
fig, axes = plt.subplots(1, 3, figsize=(19, 5.8), gridspec_kw={'width_ratios': [1.3, 1.05, 0.95]})

# Panel A: Task C1 (3-Class) Macro-F1 across all 11 classifiers (Pure Weather+Subregion vs Full Context)
ord_m = c1_weather_df['model'].tolist()
x_c = np.arange(len(ord_m))
short_clf = ['Dummy', 'Logistic\nMulti', 'Logistic\nOvR', 'CART\nTree', 'Random\nForest', 'GBR', 'Naive\nBayes', 'SVM\nLinear', 'SVM\nRBF', 'MLP\nReLU', 'MLP\nTanh']
axes[0].bar(x_c - 0.19, c1_weather_df['test_f1'], width=0.36, color='#dd6b20', label='Thuần Khí tượng + Tiểu vùng (Test F1)')
axes[0].bar(x_c + 0.19, c1_full_df['test_f1'], width=0.36, color='#2b6cb0', label='Đầy đủ Khí tượng + Tỉnh + Vụ (Test F1)')
axes[0].set_xticks(x_c); axes[0].set_xticklabels(short_clf, fontsize=7.8, rotation=28, ha='right')
axes[0].set_ylim(0, 1.05)
axes[0].set_ylabel('Macro F1-Score (Test 2023–2024, n=52)')
axes[0].set_title('A. Phân lớp 3 hạng năng suất (13 tỉnh, n=257)\nSo sánh 10 hình thái mô hình & 2 chế độ đặc trưng', fontsize=10, fontweight='bold')
axes[0].legend(fontsize=7.8, loc='upper left')

# Panel B: Task C1 3-Class Macro-Average OvR ROC Curves on Test 2023-2024 (Full Context)
roc_models = [
    ('SVM_Linear', 'SVM (Linear)', '#2b6cb0'),
    ('Logistic_Multinomial', 'Logistic (Multinomial)', '#2f855a'),
    ('SVM_RBF', 'SVM (RBF Kernel)', '#dd6b20'),
    ('RandomForest', 'Random Forest', '#805ad5'),
    ('MLP_Tanh', 'MLP Neural Net (Tanh)', '#c53030'),
    ('DecisionTree_CART', 'Decision Tree (CART)', '#d69e2e')
]
grid_fpr = np.linspace(0, 1, 200)
for mk, ml, col in roc_models:
    yt, pr_mat, auc_v = roc_c1_f[mk]
    yt_bin = label_binarize(yt, classes=[0, 1, 2])
    mean_tpr = np.zeros_like(grid_fpr)
    for c_i in range(3):
        f_i, t_i, _ = roc_curve(yt_bin[:, c_i], pr_mat[:, c_i])
        mean_tpr += np.interp(grid_fpr, f_i, t_i)
    mean_tpr /= 3.0
    mean_tpr[0] = 0.0
    axes[1].plot(grid_fpr, mean_tpr, lw=2.1, color=col, label=f'{ml} (AUC={auc_v:.3f})')
axes[1].plot([0, 1], [0, 1], 'k--', lw=1.2, label='Ngẫu nhiên (AUC=0.500)')
axes[1].set_xlabel('False Positive Rate (FPR)')
axes[1].set_ylabel('Macro-Average True Positive Rate (TPR)')
axes[1].set_title('B. Đường cong Macro-ROC (OvR) — 3 hạng năng suất\nSo sánh 6 hình thái mô hình (Test 2023–2024, n=52)', fontsize=10, fontweight='bold')
axes[1].legend(fontsize=7.8, loc='lower right')

# Panel C: Confusion Matrix of best C1 (Full Context) Test model (SVM_RBF, #2 CV & #1 Test)
best_c1_row = c1_full_df[c1_full_df['model'] == 'SVM_RBF'].iloc[0]
best_c1_name = best_c1_row['model']
cm_best = cm_c1_f[best_c1_name]
sns.heatmap(cm_best, annot=True, fmt='d', cmap='Blues', xticklabels=tier_labels, yticklabels=tier_labels, ax=axes[2], cbar=False)
axes[2].set_xlabel('Nhãn dự đoán')
axes[2].set_ylabel('Nhãn thực tế')
axes[2].set_title(f"C. Ma trận nhầm lẫn (Test 23–24, n=52)\nMô hình nổi bật: {best_c1_name}\n(Acc={best_c1_row['test_acc']:.3f}, Macro-F1={best_c1_row['test_f1']:.3f}, AUC={best_c1_row['test_auc']:.3f})", fontsize=9.6, fontweight='bold')

plt.tight_layout()
plt.savefig('results/figures/08_classification_multimodel_roc_and_cm.png', dpi=300)
plt.close()

# =============================================================================
# MODULE 4 (BUOI 11 & 12): MULTI-ALGORITHM CLUSTERING ON 13 MEKONG PROVINCES
# =============================================================================
dx_prof = t2_dx.groupby(['province_id', 'province', 'ecological_subregion']).agg(
    dx_yield_mean=('yield_t_ha', 'mean'),
    dx_yield_std=('yield_t_ha', 'std'),
    dx_yield_min=('yield_t_ha', 'min'),
    dx_vpd_mean=('vpd_mean_kpa', 'mean'),
    dx_precip_mean=('precip_total_mm', 'mean'),
    dx_ws2m_mean=('ws2m_mean_ms', 'mean'),
    dx_rh2m_mean=('rh2m_mean_pct', 'mean'),
    dx_pre90_rain_mean=('pre_season_rain_90d_mm', 'mean')
).reset_index()
comb_prof = t2_comb.groupby('province_id').agg(
    httd_yield_mean=('yield_t_ha', 'mean'),
    httd_yield_std=('yield_t_ha', 'std')
).reset_index()
prov_prof = dx_prof.merge(comb_prof, on='province_id').sort_values('province').reset_index(drop=True)

cluster_feats = ['dx_yield_mean', 'dx_yield_std', 'dx_yield_min', 'httd_yield_mean',
                 'dx_vpd_mean', 'dx_precip_mean', 'dx_ws2m_mean', 'dx_rh2m_mean', 'dx_pre90_rain_mean']
X_cl = StandardScaler().fit_transform(prov_prof[cluster_feats].values)
sub_map = {'upstream_alluvial_3crop': 0, 'middle_south_ql1': 1, 'coastal_salinity_prone': 2}
y_true_sub = prov_prof['ecological_subregion'].map(sub_map).values

def compute_sse(X, labels):
    sse = 0.0
    for c in set(labels):
        if c == -1: continue
        pts = X[labels == c]
        if len(pts) > 0:
            center = pts.mean(axis=0)
            sse += float(np.sum((pts - center) ** 2))
    return sse

def compute_dunn(X, labels):
    uniq = [c for c in sorted(set(labels)) if c != -1]
    if len(uniq) < 2:
        return np.nan
    D = cdist(X, X, metric='euclidean')
    min_inter = np.inf
    max_intra = 0.0
    for i, c1 in enumerate(uniq):
        idx1 = np.where(labels == c1)[0]
        if len(idx1) > 1:
            max_intra = max(max_intra, float(D[np.ix_(idx1, idx1)].max()))
        for c2 in uniq[i + 1:]:
            idx2 = np.where(labels == c2)[0]
            min_inter = min(min_inter, float(D[np.ix_(idx1, idx2)].min()))
    return float(min_inter / max_intra) if max_intra > 0 else np.nan

def pairwise_jaccard_f1(l1, l2):
    n = len(l1)
    tp = fp = fn = 0
    for i in range(n):
        for j in range(i + 1, n):
            s1 = (l1[i] == l1[j])
            s2 = (l2[i] == l2[j])
            if s1 and s2: tp += 1
            elif s1 and not s2: fp += 1
            elif not s1 and s2: fn += 1
    jacc = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return round(jacc, 4), round(f1, 4)

def exact_kmedoids_pam(X, k=3):
    # Exact PAM search over all C(13, k) combinations (only C(13,3)=286 combos — globally optimal!)
    D = cdist(X, X, metric='euclidean')
    best_cost = np.inf
    best_medoids = None
    best_labels = None
    for comb in itertools.combinations(range(len(X)), k):
        d_sub = D[:, list(comb)]
        lbls = np.argmin(d_sub, axis=1)
        cost = float(np.sum(np.min(d_sub, axis=1)))
        if cost < best_cost:
            best_cost = cost
            best_medoids = comb
            best_labels = lbls
    return best_labels, best_medoids

# Elbow & Silhouette scan K=2..6 for K-Means
elbow_rows = []
for k in range(2, 7):
    km = KMeans(n_clusters=k, n_init=50, random_state=42).fit(X_cl)
    elbow_rows.append({
        'k': k,
        'sse': round(float(km.inertia_), 4),
        'silhouette': round(float(silhouette_score(X_cl, km.labels_)), 4),
        'calinski_harabasz': round(float(calinski_harabasz_score(X_cl, km.labels_)), 4),
        'dunn': round(float(compute_dunn(X_cl, km.labels_)), 4)
    })
elbow_df = pd.DataFrame(elbow_rows)

# Run 9 clustering algorithms from Buoi 11 & 12
cl_assignments = prov_prof[['province_id', 'province', 'ecological_subregion']].copy()
cl_models = {}

cl_models['KMeans_K3'] = KMeans(n_clusters=3, n_init=50, random_state=42).fit(X_cl).labels_
pam_lbls, pam_medoids = exact_kmedoids_pam(X_cl, k=3)
cl_models['KMedoids_PAM_K3'] = pam_lbls
cl_models['Agglomerative_Ward_K3'] = AgglomerativeClustering(n_clusters=3, linkage='ward').fit(X_cl).labels_
cl_models['Agglomerative_Complete_K3'] = AgglomerativeClustering(n_clusters=3, linkage='complete').fit(X_cl).labels_
cl_models['Agglomerative_Average_K3'] = AgglomerativeClustering(n_clusters=3, linkage='average').fit(X_cl).labels_
cl_models['Agglomerative_Single_K3'] = AgglomerativeClustering(n_clusters=3, linkage='single').fit(X_cl).labels_
cl_models['BisectingKMeans_K3'] = BisectingKMeans(n_clusters=3, n_init=20, random_state=42).fit(X_cl).labels_
cl_models['DBSCAN_eps2_8_min2'] = DBSCAN(eps=2.8, min_samples=2).fit(X_cl).labels_
cl_models['MeanShift_Auto'] = MeanShift().fit(X_cl).labels_

cl_val_rows = []
for mname, lbls in cl_models.items():
    cl_assignments[mname] = lbls
    uniq_non_noise = [c for c in set(lbls) if c != -1]
    n_cl = len(uniq_non_noise)
    n_noise = int(np.sum(lbls == -1))
    valid_mask = lbls != -1
    if n_cl >= 2 and valid_mask.sum() > n_cl:
        sil = round(float(silhouette_score(X_cl[valid_mask], lbls[valid_mask])), 4)
        ch = round(float(calinski_harabasz_score(X_cl[valid_mask], lbls[valid_mask])), 4)
        dunn = round(float(compute_dunn(X_cl, lbls)), 4)
    else:
        sil, ch, dunn = np.nan, np.nan, np.nan
    sse = round(compute_sse(X_cl, lbls), 4)
    ari = round(float(adjusted_rand_score(y_true_sub, lbls)), 4)
    nmi = round(float(normalized_mutual_info_score(y_true_sub, lbls)), 4)
    fmi = round(float(fowlkes_mallows_score(y_true_sub, lbls)), 4)
    jacc_ext, _ = pairwise_jaccard_f1(y_true_sub, lbls)
    cl_val_rows.append({
        'algorithm': mname, 'n_clusters_found': n_cl, 'n_noise_points': n_noise,
        'internal_sse': sse, 'internal_silhouette': sil,
        'internal_calinski_harabasz': ch, 'internal_dunn': dunn,
        'external_ari_vs_subregion': ari, 'external_nmi_vs_subregion': nmi,
        'external_fmi_vs_subregion': fmi, 'external_jaccard_vs_subregion': jacc_ext
    })

cl_val_df = pd.DataFrame(cl_val_rows)
cl_val_df.to_csv('results/metrics/clustering_13provinces_validation.csv', index=False, encoding='utf-8-sig')
cl_assignments.to_csv('results/metrics/clustering_13provinces_assignments.csv', index=False, encoding='utf-8-sig')

# Relative Validation (Pairwise agreement across core K=3 methods, Buoi 11 Slide 30-32)
rel_methods = ['KMeans_K3', 'KMedoids_PAM_K3', 'Agglomerative_Ward_K3', 'BisectingKMeans_K3']
rel_rows = []
for i in range(len(rel_methods)):
    for j in range(i + 1, len(rel_methods)):
        m1, m2 = rel_methods[i], rel_methods[j]
        l1, l2 = cl_models[m1], cl_models[m2]
        jc, pf1 = pairwise_jaccard_f1(l1, l2)
        rel_rows.append({
            'method_a': m1, 'method_b': m2,
            'pairwise_rand_index': round(float(rand_score(l1, l2)), 4),
            'pairwise_ari': round(float(adjusted_rand_score(l1, l2)), 4),
            'pairwise_f_measure': pf1, 'pairwise_jaccard': jc
        })
rel_df = pd.DataFrame(rel_rows)
rel_df.to_csv('results/metrics/clustering_relative_validation.csv', index=False, encoding='utf-8-sig')

# --- Figure 9: Clustering 13 Provinces (Elbow/Silhouette, Ward Dendrogram, PCA 2D) ---
fig, axes = plt.subplots(1, 3, figsize=(19, 5.8), gridspec_kw={'width_ratios': [0.95, 1.2, 1.15]})

# Panel A: Elbow SSE & Silhouette
ax_s = axes[0]
ax_s2 = ax_s.twinx()
l1 = ax_s.plot(elbow_df['k'], elbow_df['sse'], 'o-', color='#2b6cb0', lw=2, label='SSE (nhỏ hơn tốt hơn)')
l2 = ax_s2.plot(elbow_df['k'], elbow_df['silhouette'], 's--', color='#dd6b20', lw=2, label='Silhouette (lớn hơn tốt hơn)')
ax_s.axvline(3, color='#2f855a', ls=':', lw=1.4)
ax_s.set_xlabel('Số cụm K (K-Means)')
ax_s.set_ylabel('SSE (Tổng bình phương sai số)', color='#2b6cb0')
ax_s2.set_ylabel('Silhouette Coefficient', color='#dd6b20')
ax_s.set_xticks(elbow_df['k'])
lines = l1 + l2
ax_s.legend(lines, [l.get_label() for l in lines], loc='upper center', fontsize=8)
ax_s.set_title('A. Đánh giá trong (Internal Validation)\nElbow SSE & Silhouette theo K', fontsize=10, fontweight='bold')

# Panel B: Ward Dendrogram (Slide 16 Buoi 12) — threshold 5.5 cuts cleanly into exact K=3 clusters
Z_ward = linkage(X_cl, method='ward')
dendrogram(Z_ward, labels=prov_prof['province'].tolist(), leaf_rotation=40, leaf_font_size=8.5,
           color_threshold=5.5, ax=axes[1])
axes[1].axhline(5.5, color='#c53030', ls='--', lw=1.3, label='Ngưỡng cắt K=3 cụm (d=5,5)')
axes[1].set_ylabel('Khoảng cách liên kết Ward')
axes[1].set_title('B. Cây phân cấp Dendrogram (Agglomerative Ward)\nTự phát hiện đúng 3 cụm khí hậu – năng suất 13 tỉnh', fontsize=10, fontweight='bold')
axes[1].legend(fontsize=8.5, loc='upper right')

# Panel C: PCA 2D scatter (Ward Clusters vs Agronomic Subregions) with clean non-overlapping labels
pca = PCA(n_components=2, random_state=42)
coords = pca.fit_transform(X_cl)
ward_lbls = cl_models['Agglomerative_Ward_K3']
cluster_palette = {0: '#2b6cb0', 1: '#dd6b20', 2: '#c53030'}
marker_map = {'upstream_alluvial_3crop': 'o', 'middle_south_ql1': 's', 'coastal_salinity_prone': '^'}
offsets = {
    'An Giang': (0.14, 0.14),
    'Đồng Tháp': (-0.05, -0.40),
    'Tiền Giang': (0.15, -0.25),
    'Long An': (0.16, -0.05),
    'Cần Thơ': (-0.95, 0.18),
    'Vĩnh Long': (-1.15, -0.30),
    'Kiên Giang': (0.16, -0.08),
    'Hậu Giang': (0.15, 0.12),
    'Sóc Trăng': (0.16, 0.10),
    'Bạc Liêu': (0.16, 0.05),
    'Trà Vinh': (0.12, 0.22),
    'Cà Mau': (-0.25, 0.22),
    'Bến Tre': (-0.75, 0.25)
}
for i, r in prov_prof.iterrows():
    axes[2].scatter(coords[i, 0], coords[i, 1], c=cluster_palette[ward_lbls[i]],
                    marker=marker_map[r['ecological_subregion']], s=110, edgecolor='black', lw=0.8, zorder=3)
    dx_off, dy_off = offsets.get(r['province'], (0.12, 0.10))
    axes[2].annotate(r['province'], (coords[i, 0] + dx_off, coords[i, 1] + dy_off), fontsize=8.1, fontweight='bold')
axes[2].set_xlim(coords[:, 0].min() - 0.6, coords[:, 0].max() + 0.8)
axes[2].set_ylim(coords[:, 1].min() - 0.5, coords[:, 1].max() + 0.55)

# Custom legend for clusters & subregions
from matplotlib.lines import Line2D
legend_elems = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#2b6cb0', markersize=8, label='Cụm dữ liệu 0'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#dd6b20', markersize=8, label='Cụm dữ liệu 1'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#c53030', markersize=8, label='Cụm dữ liệu 2'),
    Line2D([0], [0], marker='o', color='black', linestyle='None', markerfacecolor='white', markersize=7, label='Thượng nguồn'),
    Line2D([0], [0], marker='s', color='black', linestyle='None', markerfacecolor='white', markersize=7, label='Vùng giữa'),
    Line2D([0], [0], marker='^', color='black', linestyle='None', markerfacecolor='white', markersize=7, label='Ven biển')
]
axes[2].legend(handles=legend_elems, fontsize=7.5, loc='best', ncol=2)
axes[2].set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% phương sai)')
axes[2].set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% phương sai)')
axes[2].set_title('C. Không gian PCA 2D: Cụm dữ liệu (màu)\nđối chiếu 3 tiểu vùng sinh thái (hình dạng)', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('results/figures/09_clustering_13provinces_dendrogram_and_pca.png', dpi=300)
plt.close()

# =============================================================================
# MODULE 5 (BUOI 06 & 07): QUANTITATIVE ASSOCIATION RULES (EXACT APRIORI)
# =============================================================================
def run_apriori_rules(transactions, target_prefix, min_support=0.08, min_confidence=0.55, max_len=3):
    n_tx = len(transactions)
    tx_sets = [frozenset(t) for t in transactions]
    # Level 1 frequent itemsets
    counts = {}
    for t in tx_sets:
        for item in t:
            k = frozenset([item])
            counts[k] = counts.get(k, 0) + 1
    freq = {k: v / n_tx for k, v in counts.items() if (v / n_tx) >= min_support}
    cur_level = list(freq.keys())

    # Apriori Downward Closure candidate generation
    for length in range(2, max_len + 1):
        cands = set()
        for i in range(len(cur_level)):
            for j in range(i + 1, len(cur_level)):
                u = cur_level[i] | cur_level[j]
                if len(u) == length:
                    # Prune: all (length-1)-subsets must be frequent
                    if all(frozenset(sub) in freq for sub in itertools.combinations(u, length - 1)):
                        cands.add(u)
        next_level = []
        for c in cands:
            sup = sum(1 for t in tx_sets if c.issubset(t)) / n_tx
            if sup >= min_support:
                freq[c] = sup
                next_level.append(c)
        if not next_level:
            break
        cur_level = next_level

    # Generate rules where consequent is a single yield outcome item
    rules = []
    for itemset, sup_xy in freq.items():
        if len(itemset) < 2:
            continue
        for cons_item in itemset:
            if not cons_item.startswith(target_prefix):
                continue
            ant = itemset - frozenset([cons_item])
            if any(a.startswith(target_prefix) for a in ant):
                continue
            sup_x = freq[ant]
            sup_y = freq[frozenset([cons_item])]
            conf = sup_xy / sup_x
            if conf >= min_confidence:
                lift = conf / sup_y
                leverage = sup_xy - sup_x * sup_y
                conviction = np.inf if conf >= 0.999999 else (1.0 - sup_y) / (1.0 - conf)
                rules.append({
                    'antecedent': ' AND '.join(sorted(ant)),
                    'consequent': cons_item,
                    'support': round(float(sup_xy), 4),
                    'confidence': round(float(conf), 4),
                    'lift': round(float(lift), 4),
                    'leverage': round(float(leverage), 4),
                    'conviction': round(float(conviction), 4) if np.isfinite(conviction) else 999.0
                })
    return pd.DataFrame(rules).sort_values(['lift', 'confidence', 'support'], ascending=False)

# Discretize Track A Dong Xuan (n=127) using pd.cut (Buoi 02 + Buoi 06-07 Slide 10)
sub_vn_short = {
    'upstream_alluvial_3crop': 'Vùng=ThượngNguồn',
    'middle_south_ql1': 'Vùng=VùngGiữa',
    'coastal_salinity_prone': 'Vùng=VenBiển'
}
ar_dx = t2_dx.copy()
ar_dx['b_sub'] = ar_dx['ecological_subregion'].map(sub_vn_short)
ar_dx['b_oni'] = pd.cut(ar_dx['oni_pre_season'], [-np.inf, -0.5, 0.5, np.inf], labels=['ENSO=LaNiña', 'ENSO=TrungTính', 'ENSO=ElNiño']).astype(str)
ar_dx['b_pre'] = pd.qcut(ar_dx['pre_season_rain_90d_mm'], 3, labels=['MưaTiềnVụ=Thấp', 'MưaTiềnVụ=TB', 'MưaTiềnVụ=Cao']).astype(str)
ar_dx['b_vpd'] = pd.qcut(ar_dx['vpd_mean_kpa'], 3, labels=['VPD=ẨmThấp', 'VPD=TB', 'VPD=KhôCao']).astype(str)
ar_dx['b_ws'] = pd.qcut(ar_dx['ws2m_mean_ms'], 3, labels=['Gió2m=Yếu', 'Gió2m=TB', 'Gió2m=Mạnh']).astype(str)
ar_dx['b_yield'] = pd.qcut(ar_dx['yield_t_ha'], 3, labels=['NăngSuấtĐX=Thấp', 'NăngSuấtĐX=TB', 'NăngSuấtĐX=Cao']).astype(str)

tx_dx = ar_dx[['b_sub', 'b_oni', 'b_pre', 'b_vpd', 'b_ws', 'b_yield']].values.tolist()
rules_dx = run_apriori_rules(tx_dx, target_prefix='NăngSuấtĐX=', min_support=0.08, min_confidence=0.55, max_len=3)
rules_dx['dataset'] = 'TrackA_DX_13Prov_n127'

# Discretize Track B 3 Seasons (n=90)
ar_t1 = t1.copy()
ar_t1['b_season'] = ar_t1['season'].map({'dong_xuan': 'Vụ=ĐôngXuân', 'he_thu': 'Vụ=HèThu', 'thu_dong': 'Vụ=ThuĐông'})
ar_t1['b_oni'] = pd.cut(ar_t1['oni_pre_season'], [-np.inf, -0.5, 0.5, np.inf], labels=['ENSO=LaNiña', 'ENSO=TrungTính', 'ENSO=ElNiño']).astype(str)
ar_t1['b_rain'] = pd.qcut(ar_t1['precip_total_mm'], 3, labels=['MưaVụ=Ít', 'MưaVụ=TB', 'MưaVụ=Nhiều']).astype(str)
ar_t1['b_vpd'] = pd.qcut(ar_t1['vpd_mean_kpa'], 3, labels=['VPD=ẨmThấp', 'VPD=TB', 'VPD=KhôCao']).astype(str)
ar_t1['b_ws'] = pd.qcut(ar_t1['ws2m_mean_ms'], 3, labels=['Gió2m=Yếu', 'Gió2m=TB', 'Gió2m=Mạnh']).astype(str)
ar_t1['b_yield'] = pd.qcut(ar_t1['yield_t_ha'], 3, labels=['NăngSuất3Vụ=Thấp', 'NăngSuất3Vụ=TB', 'NăngSuất3Vụ=Cao']).astype(str)

tx_t1 = ar_t1[['b_season', 'b_oni', 'b_rain', 'b_vpd', 'b_ws', 'b_yield']].values.tolist()
rules_t1 = run_apriori_rules(tx_t1, target_prefix='NăngSuất3Vụ=', min_support=0.10, min_confidence=0.60, max_len=3)
rules_t1['dataset'] = 'TrackB_3Seasons_n90'

rules_all = pd.concat([rules_dx, rules_t1], ignore_index=True)
rules_all.to_csv('results/metrics/association_rules_agroclimatic.csv', index=False, encoding='utf-8-sig')

# --- Figure 10: Association Rules Scatter & Top Agro-Climatic Rules ---
fig, axes = plt.subplots(1, 2, figsize=(16.5, 6.0), gridspec_kw={'width_ratios': [0.95, 1.35]})
sc_ar = axes[0].scatter(rules_dx['support'], rules_dx['confidence'], c=rules_dx['lift'],
                        s=np.maximum(rules_dx['leverage'] * 1800, 40), cmap='viridis', edgecolor='black', alpha=0.85)
cbar_ar = plt.colorbar(sc_ar, ax=axes[0])
cbar_ar.set_label('Độ nâng (Lift > 1: tương quan dương)')
axes[0].axhline(0.65, color='#e53e3e', ls='--', lw=1.1, alpha=0.7)
axes[0].set_xlabel('Support (Độ hỗ trợ)')
axes[0].set_ylabel('Confidence (Độ tin cậy)')
axes[0].set_title('A. Phân bố luật kết hợp Đông Xuân 13 tỉnh (n=127)\nKích thước điểm ~ Leverage; màu sắc ~ Lift', fontsize=10, fontweight='bold')

top10_dx = rules_dx.head(10).iloc[::-1].copy()
rule_labels = [f"IF {r['antecedent']}\n→ {r['consequent']}" for _, r in top10_dx.iterrows()]
colors_ar = ['#c53030' if 'Thấp' in r['consequent'] else ('#2f855a' if 'Cao' in r['consequent'] else '#d69e2e') for _, r in top10_dx.iterrows()]
bars_ar = axes[1].barh(range(len(top10_dx)), top10_dx['lift'], color=colors_ar, alpha=0.88)
axes[1].set_yticks(range(len(top10_dx)))
axes[1].set_yticklabels(rule_labels, fontsize=7.8)
axes[1].axvline(1.0, color='black', ls='--', lw=1.1)
for idx_b, (_, r) in enumerate(top10_dx.iterrows()):
    axes[1].text(r['lift'] + 0.04, idx_b, f"Lift={r['lift']:.2f} | Conf={r['confidence']:.2f} | Sup={r['support']:.2f}",
                 va='center', fontsize=7.8, fontweight='bold')
axes[1].set_xlim(0, top10_dx['lift'].max() + 1.05)
axes[1].set_xlabel('Lift (Độ nâng)')
axes[1].set_title('B. Top 10 luật kết hợp mạnh nhất (Apriori — Đông Xuân 13 tỉnh)\nĐỏ: Rủi ro năng suất thấp | Xanh: Năng suất cao', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('results/figures/10_association_rules_lift_confidence.png', dpi=300)
plt.close()

# =============================================================================
# SAVE CONSOLIDATED SUMMARY JSON FOR REPORTING
# =============================================================================
suite_summary = {
    'buoi02_3sigma_outliers_count': int(outlier_df['flag_3sigma'].sum()),
    'buoi02_3sigma_outliers': outlier_df[outlier_df['flag_3sigma']].to_dict(orient='records'),
    'buoi04_ols_diagnostics': ols_diag_df.to_dict(orient='records'),
    'buoi04_feature_selection': fs_df.to_dict(orient='records'),
    'buoi04_regularization_coefs': reg_coef_df.to_dict(orient='records'),
    'buoi08_10_classification_c1_weather': c1_weather_df.to_dict(orient='records'),
    'buoi08_10_classification_c1_full': c1_full_df.to_dict(orient='records'),
    'buoi08_10_classification_c2_binary': c2_bin_df.to_dict(orient='records'),
    'buoi11_12_clustering_elbow': elbow_df.to_dict(orient='records'),
    'buoi11_12_clustering_validation': cl_val_df.to_dict(orient='records'),
    'buoi11_12_clustering_relative': rel_df.to_dict(orient='records'),
    'buoi11_12_pam_medoid_provinces': prov_prof.iloc[list(pam_medoids)]['province'].tolist(),
    'buoi06_07_top8_rules_dx': rules_dx.head(8).to_dict(orient='records'),
    'buoi06_07_top5_rules_t1': rules_t1.head(5).to_dict(orient='records')
}
with open('results/metrics/statistical_and_datamining_summary.json', 'w', encoding='utf-8') as f:
    json.dump(suite_summary, f, ensure_ascii=False, indent=2)

print('=== DONE: FULL STATISTICAL & DATA MINING SUITE (BUOI 02-12) GENERATED ===')
print('\n--- BUOI 02: 3-SIGMA YIELD OUTLIERS ---')
print(outlier_df[outlier_df['flag_3sigma']][['dataset', 'province', 'harvest_year', 'season', 'yield_t_ha', 'z_score']].to_string(index=False))
print('\n--- BUOI 04: OLS ASSUMPTIONS (GD1-GD4) ---')
print(ols_diag_df[['model', 'r2', 'adj_r2', 'f_pvalue_gd1', 'shapiro_p_gd2', 'max_vif_gd3', 'bp_p_gd4', 'white_p_gd4', 'aic', 'bic']].to_string(index=False))
print('\n--- BUOI 04: FEATURE SELECTION ---')
print(fs_df[['selection_method', 'n_features', 'adj_r2', 'aic', 'bic', 'max_vif', 'ols_cv_mae', 'ridge_cv_mae', 'ridge_test_mae']].to_string(index=False))
print('\n--- BUOI 04: REGULARIZATION COEFS ---')
print(reg_coef_df.to_string(index=False))
print('\n--- BUOI 08-10: CLASSIFICATION C1 (3-CLASS, FULL CONTEXT) ---')
print(c1_full_df[['model', 'skf5_f1', 'exp_cv_f1', 'test_acc', 'test_f1', 'test_auc']].to_string(index=False))
print('\n--- BUOI 08-10: CLASSIFICATION C1 (3-CLASS, WEATHER+SUBREGION ONLY) ---')
print(c1_weather_df[['model', 'skf5_f1', 'exp_cv_f1', 'test_acc', 'test_f1', 'test_auc']].to_string(index=False))
print('\n--- BUOI 08-10: CLASSIFICATION C2 (BINARY RISK) ---')
print(c2_bin_df[['model', 'skf5_f1', 'exp_cv_f1', 'test_acc', 'test_precision', 'test_recall', 'test_f1', 'test_auc']].to_string(index=False))
print('\n--- BUOI 11-12: CLUSTERING 13 PROVINCES ---')
print(cl_val_df[['algorithm', 'n_clusters_found', 'n_noise_points', 'internal_sse', 'internal_silhouette', 'internal_calinski_harabasz', 'external_ari_vs_subregion', 'external_nmi_vs_subregion']].to_string(index=False))
print('\n--- BUOI 11-12: CLUSTER ASSIGNMENTS ---')
print(cl_assignments[['province', 'ecological_subregion', 'KMeans_K3', 'KMedoids_PAM_K3', 'Agglomerative_Ward_K3', 'DBSCAN_eps2_8_min2']].to_string(index=False))
print('\n--- BUOI 06-07: TOP 8 APRIORI RULES (DONG XUAN 13 PROV) ---')
print(rules_dx.head(8)[['antecedent', 'consequent', 'support', 'confidence', 'lift', 'leverage', 'conviction']].to_string(index=False))
