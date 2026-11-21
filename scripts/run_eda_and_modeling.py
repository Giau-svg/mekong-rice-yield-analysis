import os
os.environ['MPLCONFIGDIR'] = os.path.abspath('tmp/mpl-cache')
os.makedirs('tmp/mpl-cache', exist_ok=True)
os.makedirs('results/metrics', exist_ok=True)
os.makedirs('results/figures', exist_ok=True)

import json
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression, Ridge, Lasso, HuberRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style='whitegrid', context='notebook')

# =============================================================================
# 1. LOAD CLEANED DATASETS
# =============================================================================
t1 = pd.read_csv('data/processed/tier1_core_3seasons_model_ready.csv')
t2_dx = pd.read_csv('data/processed/tier2_delta13_dong_xuan_model_ready.csv')
t2_comb = pd.read_csv('data/processed/tier2_delta13_combined_ht_td_model_ready.csv')
ood7 = pd.read_csv('data/processed/external_ood_7rows_supplemental.csv')
sens = pd.read_csv('data/processed/tier1_sensitivity_calendar_and_spatial.csv')

ALL_WEATHER_RAW = [
    't2m_mean_c', 't2m_max_mean_c', 't2m_max_peak_c', 't2m_min_mean_c',
    'precip_total_mm', 'rh2m_mean_pct', 'ws2m_mean_ms', 'vpd_mean_kpa',
    'hot_days_gt35c', 'dry_days_lt1mm', 'max_consecutive_dry_days',
    'heavy_rain_days_gt20mm', 'pre_season_rain_90d_mm', 'oni_pre_season'
]

# Parsimonious orthogonal hydro-meteorological set (physically distinct, VIF < 5 after removing Tmax-VPD redundancy)
PARSIMONIOUS_METEO = [
    'vpd_mean_kpa',            # Atmospheric evaporative demand / heat-dryness stress (physically integrates T & RH)
    'precip_total_mm',         # Seasonal moisture supply
    'ws2m_mean_ms',            # Wind / storm & evapotranspiration exposure
    'pre_season_rain_90d_mm',  # Pre-sowing 90-day water / dryness proxy
    'oni_pre_season'           # Basin-scale ENSO climate signal (NOAA PSL ONI)
]

CORE_4_METEO = ['t2m_max_mean_c', 'precip_total_mm', 'rh2m_mean_pct', 'pre_season_rain_90d_mm']

# =============================================================================
# 2. HELPER FUNCTIONS: VIF, DEMEANING, EXPANDING CV, MODELS, BOOTSTRAP
# =============================================================================
def compute_vif(df, cols):
    X = df[cols].astype(float).values
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-12)
    out = []
    for i, c in enumerate(cols):
        others = np.delete(X, i, axis=1)
        lr = LinearRegression().fit(others, X[:, i])
        r2 = lr.score(others, X[:, i])
        vif = np.inf if r2 >= 0.999999 else 1.0 / (1.0 - r2)
        out.append({'feature': c, 'r2_on_others': round(float(r2), 4), 'vif': round(float(vif), 2)})
    return pd.DataFrame(out)

def fit_group_baseline(train_df, group_cols, agg='median'):
    global_val = float(train_df['yield_t_ha'].median() if agg == 'median' else train_df['yield_t_ha'].mean())
    season_vals = train_df.groupby('season')['yield_t_ha'].agg(agg).to_dict() if 'season' in group_cols else {}
    grp_vals = train_df.groupby(group_cols)['yield_t_ha'].agg(agg).to_dict()
    return {'global': global_val, 'season': season_vals, 'group': grp_vals, 'group_cols': group_cols}

def predict_group_baseline(df, model):
    preds = []
    cols = model['group_cols']
    for _, r in df.iterrows():
        key = tuple(r[c] for c in cols) if len(cols) > 1 else r[cols[0]]
        if key in model['group']:
            preds.append(model['group'][key])
        elif 'season' in cols and r['season'] in model['season']:
            preds.append(model['season'][r['season']])
        else:
            preds.append(model['global'])
    return np.array(preds, dtype=float)

def build_anomaly_matrices(train_df, eval_df, group_cols, feat_cols, include_year=False, coastal_interactions=False, center_agg='median'):
    # Strictly fit robust group centers (median by default to resist salinity crop-failure outliers)
    # and scaling factors on TRAIN ONLY (zero data leakage)
    y_base_fit = fit_group_baseline(train_df, group_cols, agg=center_agg)
    y_train_base = predict_group_baseline(train_df, y_base_fit)
    y_eval_base = predict_group_baseline(eval_df, y_base_fit)
    y_train_res = train_df['yield_t_ha'].values - y_train_base

    grp_centers = train_df.groupby(group_cols)[feat_cols].median() if center_agg == 'median' else train_df.groupby(group_cols)[feat_cols].mean()
    global_centers = train_df[feat_cols].median() if center_agg == 'median' else train_df[feat_cols].mean()

    def demean(df):
        out = pd.DataFrame(index=df.index)
        for c in feat_cols:
            vals = []
            for _, r in df.iterrows():
                key = tuple(r[g] for g in group_cols) if len(group_cols) > 1 else r[group_cols[0]]
                m = grp_centers.loc[key, c] if key in grp_centers.index else global_centers[c]
                vals.append(r[c] - m)
            out[c] = vals
        return out

    X_tr_df = demean(train_df)
    X_ev_df = demean(eval_df)

    # Standardize demeaned anomalies using TRAIN ONLY std
    stds = X_tr_df.std(ddof=0).replace(0, 1.0)
    X_tr_df = X_tr_df / stds
    X_ev_df = X_ev_df / stds

    if include_year:
        y_m, y_s = train_df['harvest_year'].mean(), train_df['harvest_year'].std(ddof=0) or 1.0
        X_tr_df['year_z'] = (train_df['harvest_year'].values - y_m) / y_s
        X_ev_df['year_z'] = (eval_df['harvest_year'].values - y_m) / y_s

    if coastal_interactions:
        tr_c = (train_df['ecological_subregion'] == 'coastal_salinity_prone').astype(float).values
        ev_c = (eval_df['ecological_subregion'] == 'coastal_salinity_prone').astype(float).values
        if 'oni_pre_season' in X_tr_df.columns:
            X_tr_df['oni_x_coastal'] = X_tr_df['oni_pre_season'].values * tr_c
            X_ev_df['oni_x_coastal'] = X_ev_df['oni_pre_season'].values * ev_c
        if 'pre_season_rain_90d_mm' in X_tr_df.columns:
            X_tr_df['prerain_x_coastal'] = X_tr_df['pre_season_rain_90d_mm'].values * tr_c
            X_ev_df['prerain_x_coastal'] = X_ev_df['pre_season_rain_90d_mm'].values * ev_c

    return X_tr_df, y_train_res, X_ev_df, y_eval_base, y_train_base

def build_direct_matrices(train_df, eval_df, cat_cols, feat_cols, include_year=False):
    tr_cat = pd.get_dummies(train_df[cat_cols], drop_first=False, dtype=float)
    ev_cat = pd.get_dummies(eval_df[cat_cols], drop_first=False, dtype=float).reindex(columns=tr_cat.columns, fill_value=0.0)
    cols = list(feat_cols) + (['harvest_year'] if include_year else [])
    if cols:
        means = train_df[cols].mean()
        stds = train_df[cols].std(ddof=0).replace(0, 1.0)
        tr_num = (train_df[cols] - means) / stds
        ev_num = (eval_df[cols] - means) / stds
        X_tr = pd.concat([tr_cat.reset_index(drop=True), tr_num.reset_index(drop=True)], axis=1)
        X_ev = pd.concat([ev_cat.reset_index(drop=True), ev_num.reset_index(drop=True)], axis=1)
    else:
        X_tr, X_ev = tr_cat.reset_index(drop=True), ev_cat.reset_index(drop=True)
    return X_tr, train_df['yield_t_ha'].values, X_ev

def fit_predict_spec(spec_name, train_df, eval_df, group_cols, cat_cols, feat_cols, params=None):
    params = params or {}
    if spec_name == 'Baseline_Median':
        bm = fit_group_baseline(train_df, group_cols, agg='median')
        return predict_group_baseline(train_df, bm), predict_group_baseline(eval_df, bm), None

    if spec_name == 'Structural_FE_Mean':
        bm = fit_group_baseline(train_df, group_cols, agg='mean')
        return predict_group_baseline(train_df, bm), predict_group_baseline(eval_df, bm), None

    if spec_name == 'Structural_FE_Plus_Trend':
        X_tr, y_res, X_ev, ev_base, tr_base = build_anomaly_matrices(train_df, eval_df, group_cols, [], include_year=True)
        mdl = Ridge(alpha=params.get('alpha', 1.0)).fit(X_tr, y_res)
        return tr_base + mdl.predict(X_tr), ev_base + mdl.predict(X_ev), mdl

    if spec_name == 'OLS_Anomaly_Weather':
        X_tr, y_res, X_ev, ev_base, tr_base = build_anomaly_matrices(train_df, eval_df, group_cols, feat_cols, include_year=params.get('include_year', False), coastal_interactions=params.get('coastal_interactions', False))
        mdl = LinearRegression().fit(X_tr, y_res)
        return tr_base + mdl.predict(X_tr), ev_base + mdl.predict(X_ev), (mdl, list(X_tr.columns))

    if spec_name == 'Ridge_Anomaly_Weather':
        X_tr, y_res, X_ev, ev_base, tr_base = build_anomaly_matrices(train_df, eval_df, group_cols, feat_cols, include_year=params.get('include_year', False), coastal_interactions=params.get('coastal_interactions', False))
        mdl = Ridge(alpha=params.get('alpha', 10.0)).fit(X_tr, y_res)
        return tr_base + mdl.predict(X_tr), ev_base + mdl.predict(X_ev), (mdl, list(X_tr.columns))

    if spec_name == 'Lasso_Anomaly_Weather':
        X_tr, y_res, X_ev, ev_base, tr_base = build_anomaly_matrices(train_df, eval_df, group_cols, feat_cols, include_year=params.get('include_year', False), coastal_interactions=params.get('coastal_interactions', False))
        mdl = Lasso(alpha=params.get('alpha', 0.05), max_iter=5000, random_state=42).fit(X_tr, y_res)
        return tr_base + mdl.predict(X_tr), ev_base + mdl.predict(X_ev), (mdl, list(X_tr.columns))

    if spec_name == 'Huber_Anomaly_Weather':
        X_tr, y_res, X_ev, ev_base, tr_base = build_anomaly_matrices(train_df, eval_df, group_cols, feat_cols, include_year=params.get('include_year', False), coastal_interactions=params.get('coastal_interactions', False))
        mdl = HuberRegressor(alpha=params.get('alpha', 1.0), epsilon=params.get('epsilon', 1.35), max_iter=1000).fit(X_tr, y_res)
        return tr_base + mdl.predict(X_tr), ev_base + mdl.predict(X_ev), (mdl, list(X_tr.columns))

    if spec_name == 'DecisionTree_Anomaly':
        X_tr, y_res, X_ev, ev_base, tr_base = build_anomaly_matrices(train_df, eval_df, group_cols, feat_cols, include_year=params.get('include_year', False), coastal_interactions=params.get('coastal_interactions', False))
        mdl = DecisionTreeRegressor(
            max_depth=params.get('max_depth', 2),
            min_samples_leaf=params.get('min_samples_leaf', 6),
            random_state=42
        ).fit(X_tr, y_res)
        return tr_base + mdl.predict(X_tr), ev_base + mdl.predict(X_ev), mdl

    if spec_name == 'Shallow_RF_Direct':
        X_tr, y_tr, X_ev = build_direct_matrices(train_df, eval_df, cat_cols, feat_cols, include_year=params.get('include_year', False))
        mdl = RandomForestRegressor(
            n_estimators=200,
            max_depth=params.get('max_depth', 3),
            min_samples_leaf=params.get('min_samples_leaf', 5),
            max_features='sqrt',
            random_state=42
        ).fit(X_tr, y_tr)
        return mdl.predict(X_tr), mdl.predict(X_ev), mdl

    if spec_name == 'Shallow_RF_Anomaly':
        X_tr, y_res, X_ev, ev_base, tr_base = build_anomaly_matrices(train_df, eval_df, group_cols, feat_cols, include_year=params.get('include_year', False), coastal_interactions=params.get('coastal_interactions', False))
        mdl = RandomForestRegressor(
            n_estimators=200,
            max_depth=params.get('max_depth', 2),
            min_samples_leaf=params.get('min_samples_leaf', 6),
            max_features='sqrt',
            random_state=42
        ).fit(X_tr, y_res)
        return tr_base + mdl.predict(X_tr), ev_base + mdl.predict(X_ev), mdl

    if spec_name == 'GBR_Anomaly':
        X_tr, y_res, X_ev, ev_base, tr_base = build_anomaly_matrices(train_df, eval_df, group_cols, feat_cols, include_year=params.get('include_year', False), coastal_interactions=params.get('coastal_interactions', False))
        mdl = GradientBoostingRegressor(
            n_estimators=params.get('n_estimators', 60),
            learning_rate=params.get('learning_rate', 0.05),
            max_depth=params.get('max_depth', 2),
            min_samples_leaf=params.get('min_samples_leaf', 5),
            subsample=0.8,
            random_state=42
        ).fit(X_tr, y_res)
        return tr_base + mdl.predict(X_tr), ev_base + mdl.predict(X_ev), mdl

    if spec_name == 'SVR_Anomaly':
        X_tr, y_res, X_ev, ev_base, tr_base = build_anomaly_matrices(train_df, eval_df, group_cols, feat_cols, include_year=params.get('include_year', False), coastal_interactions=params.get('coastal_interactions', False))
        mdl = SVR(
            kernel=params.get('kernel', 'rbf'),
            C=params.get('C', 1.0),
            epsilon=params.get('epsilon', 0.1)
        ).fit(X_tr, y_res)
        return tr_base + mdl.predict(X_tr), ev_base + mdl.predict(X_ev), mdl

    if spec_name == 'MLP_Anomaly':
        X_tr, y_res, X_ev, ev_base, tr_base = build_anomaly_matrices(train_df, eval_df, group_cols, feat_cols, include_year=params.get('include_year', False), coastal_interactions=params.get('coastal_interactions', False))
        mdl = MLPRegressor(
            hidden_layer_sizes=params.get('hidden_layer_sizes', (16, 8)),
            activation=params.get('activation', 'relu'),
            alpha=params.get('alpha', 1.0),
            solver='lbfgs',
            max_iter=500,
            random_state=42
        ).fit(X_tr, y_res)
        return tr_base + mdl.predict(X_tr), ev_base + mdl.predict(X_ev), mdl

    raise ValueError(f'Unknown model spec: {spec_name}')

def expanding_cv_select(df, spec_name, group_cols, cat_cols, feat_cols, param_grid, cv_years=(2019, 2020, 2021, 2022)):
    # Strictly evaluates on pre-test years (2015–2022), never touching test (2023–2024)
    best_mae = np.inf
    best_params = None
    best_oof = None
    best_fold_maes = None

    for params in param_grid:
        oof_y, oof_pred, oof_yr, fold_maes = [], [], [], []
        for val_yr in cv_years:
            tr = df[df['harvest_year'] < val_yr]
            va = df[df['harvest_year'] == val_yr]
            _, pred_va, _ = fit_predict_spec(spec_name, tr, va, group_cols, cat_cols, feat_cols, params)
            fold_maes.append(mean_absolute_error(va['yield_t_ha'].values, pred_va))
            oof_y.extend(va['yield_t_ha'].values)
            oof_pred.extend(pred_va)
            oof_yr.extend(va['harvest_year'].values)
        cv_mae = mean_absolute_error(oof_y, oof_pred)
        if cv_mae < best_mae:
            best_mae = cv_mae
            best_params = params
            best_oof = pd.DataFrame({'year': oof_yr, 'y_true': oof_y, 'y_pred': oof_pred})
            best_fold_maes = fold_maes
    return best_params, best_mae, float(np.std(best_fold_maes)), best_oof

def paired_bootstrap_ci(y_true, pred_model, pred_base, n_boot=2000, seed=42):
    rng = np.random.default_rng(seed)
    err_m = np.abs(y_true - pred_model)
    err_b = np.abs(y_true - pred_base)
    diffs = err_m - err_b  # negative means model improves over baseline
    n = len(diffs)
    boot_means = [diffs[rng.integers(0, n, n)].mean() for _ in range(n_boot)]
    lo, hi = np.percentile(boot_means, [2.5, 97.5])
    return float(diffs.mean()), float(lo), float(hi)

def eval_metrics(y_true, y_pred):
    return {
        'mae': round(float(mean_absolute_error(y_true, y_pred)), 4),
        'rmse': round(float(root_mean_squared_error(y_true, y_pred)), 4),
        'r2': round(float(r2_score(y_true, y_pred)), 4)
    }

# =============================================================================
# 3. EDA QUANTITATIVE AUDIT: VIF, VARIANCE DECOMPOSITION, WITHIN-SEASON CORR
# =============================================================================
t1_train = t1[t1['time_split'] == 'train']
vif_raw = compute_vif(t1_train, ['t2m_mean_c', 't2m_max_mean_c', 't2m_max_peak_c', 'precip_total_mm', 'rh2m_mean_pct', 'hot_days_gt35c', 'dry_days_lt1mm'])
vif_raw['feature_set'] = 'raw_7_collinear'
vif_pars = compute_vif(t1_train, PARSIMONIOUS_METEO)
vif_pars['feature_set'] = 'orthogonal_5_physical'

# Demeaned VIF on Train
X_tr_anom_vif, _, _, _, _ = build_anomaly_matrices(t1_train, t1_train, ['province_id', 'season'], PARSIMONIOUS_METEO)
vif_anom = compute_vif(X_tr_anom_vif, PARSIMONIOUS_METEO)
vif_anom['feature_set'] = 'demeaned_anomaly_5_physical'

vif_table = pd.concat([vif_raw, vif_pars, vif_anom], ignore_index=True)
vif_table.to_csv('results/metrics/eda_vif_comparison.csv', index=False, encoding='utf-8-sig')

# Within-Group (Demeaned by Province x Season) Correlations per Season on Track B (n=90)
within_corr_rows = []
t1_dem = t1.copy()
for col in ['yield_t_ha'] + ALL_WEATHER_RAW:
    t1_dem[col + '_anom'] = t1_dem[col] - t1_dem.groupby(['province_id', 'season'])[col].transform('mean')

for scope_name, sub in [('all_3_seasons_pooled', t1_dem), ('dong_xuan', t1_dem[t1_dem['season'] == 'dong_xuan']),
                        ('he_thu', t1_dem[t1_dem['season'] == 'he_thu']), ('thu_dong', t1_dem[t1_dem['season'] == 'thu_dong'])]:
    for f in ALL_WEATHER_RAW:
        r_p, p_p = stats.pearsonr(sub[f + '_anom'], sub['yield_t_ha_anom'])
        r_s, p_s = stats.spearmanr(sub[f + '_anom'], sub['yield_t_ha_anom'])
        r_raw, _ = stats.pearsonr(sub[f], sub['yield_t_ha'])
        within_corr_rows.append({
            'track': 'track_b_3seasons',
            'scope': scope_name,
            'n': len(sub),
            'feature': f,
            'raw_pearson_r': round(float(r_raw), 4),
            'within_pearson_r': round(float(r_p), 4),
            'within_p_value': round(float(p_p), 4),
            'within_spearman_rho': round(float(r_s), 4),
            'within_spearman_p': round(float(p_s), 4)
        })

# Within-Province Correlations on Track A1 (13 provinces Dong Xuan, both full 127 and ex-BenTre-salinity 125)
for regime_name, sub_df in [('delta13_dx_full_127', t2_dx), ('delta13_dx_ex_salinity_125', t2_dx[t2_dx['domain_outlier_flag'] == 'none']),
                            ('delta13_dx_upstream', t2_dx[t2_dx['ecological_subregion'] == 'upstream_alluvial_3crop']),
                            ('delta13_dx_middle', t2_dx[t2_dx['ecological_subregion'] == 'middle_south_ql1']),
                            ('delta13_dx_coastal_ex_fail', t2_dx[(t2_dx['ecological_subregion'] == 'coastal_salinity_prone') & (t2_dx['domain_outlier_flag'] == 'none')]),
                            ('delta13_combined_ht_td_130', t2_comb)]:
    tmp = sub_df.copy()
    for col in ['yield_t_ha'] + ALL_WEATHER_RAW:
        tmp[col + '_anom'] = tmp[col] - tmp.groupby('province_id')[col].transform('mean')
    for f in ALL_WEATHER_RAW:
        r_p, p_p = stats.pearsonr(tmp[f + '_anom'], tmp['yield_t_ha_anom'])
        r_s, p_s = stats.spearmanr(tmp[f + '_anom'], tmp['yield_t_ha_anom'])
        r_raw, _ = stats.pearsonr(tmp[f], tmp['yield_t_ha'])
        within_corr_rows.append({
            'track': 'track_a_delta13',
            'scope': regime_name,
            'n': len(tmp),
            'feature': f,
            'raw_pearson_r': round(float(r_raw), 4),
            'within_pearson_r': round(float(r_p), 4),
            'within_p_value': round(float(p_p), 4),
            'within_spearman_rho': round(float(r_s), 4),
            'within_spearman_p': round(float(p_s), 4)
        })

within_corr_df = pd.DataFrame(within_corr_rows)
within_corr_df.to_csv('results/metrics/eda_within_correlations.csv', index=False, encoding='utf-8-sig')

# =============================================================================
# 4. MODELING — TRACK B: SEPARATE 3 SEASONS (An Giang, Kien Giang, Can Tho, n=90)
# =============================================================================
t1_dev = t1[t1['harvest_year'] <= 2022].copy()   # 72 rows for Expanding-Window CV & final refit
t1_tr6 = t1[t1['time_split'] == 'train'].copy()  # 54 rows (2015–2020)
t1_val = t1[t1['time_split'] == 'val'].copy()    # 18 rows (2021–2022)
t1_test = t1[t1['time_split'] == 'test'].copy()  # 18 rows (2023–2024, LOCKED)

track_b_specs = [
    ('Baseline_Median', 'Baseline_Median', [], [{}]),
    ('Structural_FE_Mean', 'Structural_FE_Mean', [], [{}]),
    ('Structural_FE_Plus_Trend', 'Structural_FE_Plus_Trend', [], [{'alpha': a} for a in [0.1, 1.0, 10.0, 50.0]]),
    ('OLS_Anomaly_Core4', 'OLS_Anomaly_Weather', CORE_4_METEO, [{'include_year': False}]),
    ('OLS_Anomaly_Ortho5_Trend', 'OLS_Anomaly_Weather', PARSIMONIOUS_METEO, [{'include_year': True}]),
    ('Ridge_Anomaly_Ortho5', 'Ridge_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'include_year': False} for a in [1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0]]),
    ('Ridge_Anomaly_Ortho5_Trend', 'Ridge_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'include_year': True} for a in [1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0]]),
    ('Lasso_Anomaly_Ortho5', 'Lasso_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'include_year': False} for a in [0.005, 0.01, 0.03, 0.05, 0.1, 0.2]]),
    ('Lasso_Anomaly_Ortho5_Trend', 'Lasso_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'include_year': True} for a in [0.005, 0.01, 0.03, 0.05, 0.1, 0.2]]),
    ('Huber_Anomaly_Ortho5', 'Huber_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'epsilon': e, 'include_year': False} for a in [0.1, 1.0, 10.0, 50.0] for e in [1.35, 1.5]]),
    ('Huber_Anomaly_Ortho5_Trend', 'Huber_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'epsilon': e, 'include_year': True} for a in [0.1, 1.0, 10.0, 50.0] for e in [1.35, 1.5]]),
    ('DecisionTree_Anomaly_Trend', 'DecisionTree_Anomaly', PARSIMONIOUS_METEO, [{'max_depth': d, 'min_samples_leaf': l, 'include_year': True} for d in [2, 3, 4] for l in [4, 6, 8]]),
    ('Shallow_RF_Direct', 'Shallow_RF_Direct', PARSIMONIOUS_METEO, [{'max_depth': d, 'min_samples_leaf': l, 'include_year': False} for d in [2, 3, 4] for l in [4, 6, 8]]),
    ('Shallow_RF_Anomaly', 'Shallow_RF_Anomaly', PARSIMONIOUS_METEO, [{'max_depth': d, 'min_samples_leaf': l, 'include_year': False} for d in [2, 3] for l in [5, 7, 10]]),
    ('Shallow_RF_Anomaly_Trend', 'Shallow_RF_Anomaly', PARSIMONIOUS_METEO, [{'max_depth': d, 'min_samples_leaf': l, 'include_year': True} for d in [2, 3] for l in [5, 7, 10]]),
    ('GBR_Anomaly_Trend', 'GBR_Anomaly', PARSIMONIOUS_METEO, [{'n_estimators': n, 'learning_rate': lr, 'max_depth': d, 'min_samples_leaf': 5, 'include_year': True} for n in [40, 80] for lr in [0.03, 0.08] for d in [1, 2]]),
    ('SVR_Linear_Anomaly_Trend', 'SVR_Anomaly', PARSIMONIOUS_METEO, [{'kernel': 'linear', 'C': c, 'epsilon': 0.05, 'include_year': True} for c in [0.05, 0.2, 1.0, 5.0]]),
    ('SVR_RBF_Anomaly_Trend', 'SVR_Anomaly', PARSIMONIOUS_METEO, [{'kernel': 'rbf', 'C': c, 'epsilon': 0.05, 'include_year': True} for c in [0.2, 1.0, 5.0, 10.0]]),
    ('MLP_ReLU_Anomaly_Trend', 'MLP_Anomaly', PARSIMONIOUS_METEO, [{'hidden_layer_sizes': h, 'activation': 'relu', 'alpha': a, 'include_year': True} for h in [(8,), (16, 8)] for a in [1.0, 10.0, 50.0]]),
    ('MLP_Tanh_Anomaly_Trend', 'MLP_Anomaly', PARSIMONIOUS_METEO, [{'hidden_layer_sizes': h, 'activation': 'tanh', 'alpha': a, 'include_year': True} for h in [(8,), (16, 8)] for a in [1.0, 10.0, 50.0]])
]

t1_results = []
t1_oof_store = {}
t1_test_preds = pd.DataFrame({
    'province_id': t1_test['province_id'].values,
    'province': t1_test['province'].values,
    'harvest_year': t1_test['harvest_year'].values,
    'season': t1_test['season'].values,
    'y_true': t1_test['yield_t_ha'].values
})

for label, spec, feats, grid in track_b_specs:
    best_p, cv_mae, cv_std, oof_df = expanding_cv_select(t1_dev, spec, ['province_id', 'season'], ['province_id', 'season'], feats, grid)
    t1_oof_store[label] = oof_df

    # Fixed 2015–2020 -> Val 2021–2022 diagnostic (per DeTaiPTDL.pdf)
    tr6_pred, val_pred, _ = fit_predict_spec(spec, t1_tr6, t1_val, ['province_id', 'season'], ['province_id', 'season'], feats, best_p)
    # Final refit on full pre-test 2015–2022 -> evaluate ONCE on locked Test 2023–2024
    dev_pred, test_pred, fitted_obj = fit_predict_spec(spec, t1_dev, t1_test, ['province_id', 'season'], ['province_id', 'season'], feats, best_p)
    t1_test_preds[label] = np.round(test_pred, 4)

    m_tr = eval_metrics(t1_dev['yield_t_ha'].values, dev_pred)
    m_val = eval_metrics(t1_val['yield_t_ha'].values, val_pred)
    m_te = eval_metrics(t1_test['yield_t_ha'].values, test_pred)

    t1_results.append({
        'model': label,
        'selected_params': json.dumps(best_p),
        'train_2015_2022_mae': m_tr['mae'],
        'expanding_cv_mae': round(cv_mae, 4),
        'expanding_cv_std': round(cv_std, 4),
        'val_2021_2022_mae': m_val['mae'],
        'test_2023_2024_mae': m_te['mae'],
        'test_2023_2024_rmse': m_te['rmse'],
        'test_2023_2024_r2': m_te['r2']
    })

t1_res_df = pd.DataFrame(t1_results)
# Add Paired Bootstrap 95% CI vs Baseline_Median on both Expanding CV (n=36) and Test (n=18)
base_oof = t1_oof_store['Baseline_Median']
base_te = t1_test_preds['Baseline_Median'].values
cv_d, cv_lo, cv_hi, te_d, te_lo, te_hi = [], [], [], [], [], []
for label in t1_res_df['model']:
    d1, l1, h1 = paired_bootstrap_ci(base_oof['y_true'].values, t1_oof_store[label]['y_pred'].values, base_oof['y_pred'].values)
    d2, l2, h2 = paired_bootstrap_ci(t1_test_preds['y_true'].values, t1_test_preds[label].values, base_te)
    cv_d.append(round(d1, 4)); cv_lo.append(round(l1, 4)); cv_hi.append(round(h1, 4))
    te_d.append(round(d2, 4)); te_lo.append(round(l2, 4)); te_hi.append(round(h2, 4))

t1_res_df['delta_cv_mae_vs_base'] = cv_d
t1_res_df['delta_cv_ci95_lo'] = cv_lo
t1_res_df['delta_cv_ci95_hi'] = cv_hi
t1_res_df['delta_test_mae_vs_base'] = te_d
t1_res_df['delta_test_ci95_lo'] = te_lo
t1_res_df['delta_test_ci95_hi'] = te_hi

t1_res_df.to_csv('results/metrics/track_b_3seasons_model_comparison.csv', index=False, encoding='utf-8-sig')
t1_test_preds.to_csv('results/metrics/track_b_3seasons_test_predictions.csv', index=False, encoding='utf-8-sig')

# Error breakdown by season & province on Test 2023–2024
t1_breakdown = []
for grp_col in ['season', 'province']:
    for grp_val, sub in t1_test_preds.groupby(grp_col):
        for label in ['Baseline_Median', 'Structural_FE_Plus_Trend', 'Ridge_Anomaly_Ortho5_Trend', 'Lasso_Anomaly_Ortho5_Trend', 'Huber_Anomaly_Ortho5_Trend', 'DecisionTree_Anomaly_Trend', 'Shallow_RF_Anomaly_Trend', 'GBR_Anomaly_Trend', 'SVR_Linear_Anomaly_Trend', 'MLP_ReLU_Anomaly_Trend']:
            t1_breakdown.append({
                'group_type': grp_col,
                'group_value': grp_val,
                'n': len(sub),
                'model': label,
                'test_mae': round(float(mean_absolute_error(sub['y_true'], sub[label])), 4),
                'test_bias': round(float((sub[label] - sub['y_true']).mean()), 4)
            })
pd.DataFrame(t1_breakdown).to_csv('results/metrics/track_b_test_error_breakdown.csv', index=False, encoding='utf-8-sig')

# =============================================================================
# 5. SENSITIVITY ANALYSIS ON TRACK B (6 Calendar ±10/±15d & Spatial Scenarios)
# =============================================================================
sens_rows = []
for sc_name, sc_df in sens.groupby('sensitivity_scenario'):
    sc_dev = sc_df[sc_df['harvest_year'] <= 2022].copy()
    sc_test = sc_df[sc_df['harvest_year'] >= 2023].copy()
    for label, spec, feats, grid in [
        ('Baseline_Median', 'Baseline_Median', [], [{}]),
        ('Ridge_Anomaly_Ortho5', 'Ridge_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'include_year': False} for a in [1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0]]),
        ('Ridge_Anomaly_Ortho5_Trend', 'Ridge_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'include_year': True} for a in [1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0]]),
        ('Huber_Anomaly_Ortho5', 'Huber_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'epsilon': 1.35, 'include_year': False} for a in [0.1, 1.0, 10.0, 50.0]])
    ]:
        bp, cv_m, cv_s, _ = expanding_cv_select(sc_dev, spec, ['province_id', 'season'], ['province_id', 'season'], feats, grid)
        _, te_p, _ = fit_predict_spec(spec, sc_dev, sc_test, ['province_id', 'season'], ['province_id', 'season'], feats, bp)
        m_te = eval_metrics(sc_test['yield_t_ha'].values, te_p)
        sens_rows.append({
            'scenario': sc_name,
            'model': label,
            'selected_params': json.dumps(bp),
            'expanding_cv_mae': round(cv_m, 4),
            'test_mae': m_te['mae'],
            'test_rmse': m_te['rmse']
        })
sens_res_df = pd.DataFrame(sens_rows)
sens_res_df.to_csv('results/metrics/track_b_sensitivity_model_results.csv', index=False, encoding='utf-8-sig')

# =============================================================================
# 6. EXTERNAL GEOGRAPHIC OOD STRESS TEST (7 supplemental rows: TG, VL, CM)
# =============================================================================
# Train season-level (province-agnostic) models on Track B 3 upstream provinces (2015–2022),
# then predict unseen provinces from Middle (Tien Giang, Vinh Long) & Coastal (Ca Mau) subregions.
ood_base_fit = fit_group_baseline(t1_dev, ['season'], agg='median')
ood_pred_base = predict_group_baseline(ood7, ood_base_fit)

X_tr_ood, y_res_ood, X_ev_ood, ev_base_ood, _ = build_anomaly_matrices(t1_dev, ood7, ['season'], PARSIMONIOUS_METEO, include_year=False)
ridge_ood = Ridge(alpha=25.0).fit(X_tr_ood, y_res_ood)
ood_pred_ridge = ev_base_ood + ridge_ood.predict(X_ev_ood)

ood_out = ood7[['province', 'ecological_subregion', 'harvest_year', 'season', 'yield_t_ha']].copy()
ood_out['pred_season_baseline'] = np.round(ood_pred_base, 4)
ood_out['pred_upstream_ridge_weather'] = np.round(ood_pred_ridge, 4)
ood_out['abs_err_baseline'] = np.round(np.abs(ood_out['yield_t_ha'] - ood_out['pred_season_baseline']), 4)
ood_out['abs_err_ridge'] = np.round(np.abs(ood_out['yield_t_ha'] - ood_out['pred_upstream_ridge_weather']), 4)
ood_out['signed_err_ridge'] = np.round(ood_out['pred_upstream_ridge_weather'] - ood_out['yield_t_ha'], 4)
ood_out.to_csv('results/metrics/external_ood_7rows_predictions.csv', index=False, encoding='utf-8-sig')

# =============================================================================
# 7. MODELING — TRACK A: FULL 13-PROVINCE MEKONG DELTA (Dong Xuan Dual-Regime + HT-TD Combined)
# =============================================================================
def run_track_a_suite(df_in, suite_name, coastal_int=True):
    dev = df_in[df_in['harvest_year'] <= 2022].copy()
    tr6 = df_in[df_in['time_split'] == 'train'].copy()
    val = df_in[df_in['time_split'] == 'val'].copy()
    test = df_in[df_in['time_split'] == 'test'].copy()

    specs = [
        ('Baseline_Median_Prov', 'Baseline_Median', [], [{}]),
        ('Structural_Prov_Mean', 'Structural_FE_Mean', [], [{}]),
        ('Structural_Prov_Plus_Trend', 'Structural_FE_Plus_Trend', [], [{'alpha': a} for a in [0.1, 1.0, 10.0, 50.0]]),
        ('OLS_Anomaly_Weather', 'OLS_Anomaly_Weather', PARSIMONIOUS_METEO, [{'include_year': False, 'coastal_interactions': False}]),
        ('Ridge_Anomaly_Weather', 'Ridge_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'include_year': False, 'coastal_interactions': False} for a in [1.0, 10.0, 25.0, 50.0, 100.0, 200.0]]),
        ('Lasso_Anomaly_Weather', 'Lasso_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'include_year': False, 'coastal_interactions': False} for a in [0.01, 0.05, 0.1, 0.2]]),
        ('Huber_Anomaly_Weather', 'Huber_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'epsilon': 1.35, 'include_year': False, 'coastal_interactions': False} for a in [0.1, 1.0, 10.0, 50.0]]),
        ('Huber_Anomaly_Weather_Trend', 'Huber_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'epsilon': 1.35, 'include_year': True, 'coastal_interactions': False} for a in [0.1, 1.0, 10.0, 50.0]]),
        ('DecisionTree_Anomaly', 'DecisionTree_Anomaly', PARSIMONIOUS_METEO, [{'max_depth': d, 'min_samples_leaf': l, 'include_year': False} for d in [2, 3] for l in [6, 10]]),
        ('Shallow_RF_Anomaly', 'Shallow_RF_Anomaly', PARSIMONIOUS_METEO, [{'max_depth': d, 'min_samples_leaf': l, 'include_year': False} for d in [2, 3] for l in [6, 10]]),
        ('GBR_Anomaly', 'GBR_Anomaly', PARSIMONIOUS_METEO, [{'n_estimators': 50, 'learning_rate': lr, 'max_depth': d, 'min_samples_leaf': 6, 'include_year': False} for lr in [0.03, 0.08] for d in [1, 2]]),
        ('SVR_RBF_Anomaly', 'SVR_Anomaly', PARSIMONIOUS_METEO, [{'kernel': 'rbf', 'C': c, 'epsilon': 0.1, 'include_year': False} for c in [0.2, 1.0, 5.0]]),
        ('MLP_ReLU_Anomaly', 'MLP_Anomaly', PARSIMONIOUS_METEO, [{'hidden_layer_sizes': (12,), 'activation': 'relu', 'alpha': a, 'include_year': False} for a in [1.0, 10.0, 50.0]])
    ]
    if coastal_int:
        specs.insert(7, ('Huber_Anomaly_Weather_ONI_Coastal', 'Huber_Anomaly_Weather', PARSIMONIOUS_METEO, [{'alpha': a, 'epsilon': 1.35, 'include_year': False, 'coastal_interactions': True} for a in [0.1, 1.0, 10.0, 50.0]]))

    rows = []
    oof_store = {}
    pred_df = test[['province_id', 'province', 'ecological_subregion', 'harvest_year', 'yield_t_ha', 'domain_outlier_flag']].copy()

    for label, spec, feats, grid in specs:
        bp, cv_m, cv_s, oof_df = expanding_cv_select(dev, spec, ['province_id'], ['province_id'], feats, grid)
        oof_store[label] = oof_df
        _, val_p, _ = fit_predict_spec(spec, tr6, val, ['province_id'], ['province_id'], feats, bp)
        dev_p, te_p, _ = fit_predict_spec(spec, dev, test, ['province_id'], ['province_id'], feats, bp)
        pred_df[label] = np.round(te_p, 4)
        m_tr = eval_metrics(dev['yield_t_ha'].values, dev_p)
        m_va = eval_metrics(val['yield_t_ha'].values, val_p)
        m_te = eval_metrics(test['yield_t_ha'].values, te_p)
        rows.append({
            'suite': suite_name,
            'n_total': len(df_in),
            'model': label,
            'selected_params': json.dumps(bp),
            'train_mae': m_tr['mae'],
            'expanding_cv_mae': round(cv_m, 4),
            'expanding_cv_std': round(cv_s, 4),
            'val_2021_2022_mae': m_va['mae'],
            'test_2023_2024_mae': m_te['mae'],
            'test_2023_2024_rmse': m_te['rmse'],
            'test_2023_2024_r2': m_te['r2']
        })
    res = pd.DataFrame(rows)
    base_oof = oof_store['Baseline_Median_Prov']
    base_te = pred_df['Baseline_Median_Prov'].values
    res['delta_cv_mae_vs_base'] = [round(paired_bootstrap_ci(base_oof['y_true'].values, oof_store[m]['y_pred'].values, base_oof['y_pred'].values)[0], 4) for m in res['model']]
    res['delta_test_mae_vs_base'] = [round(paired_bootstrap_ci(pred_df['yield_t_ha'].values, pred_df[m].values, base_te)[0], 4) for m in res['model']]
    return res, pred_df, oof_store

res_dx_full, pred_dx_full, oof_dx_full = run_track_a_suite(t2_dx, 'delta13_dong_xuan_full_127', coastal_int=True)
res_dx_nosal, pred_dx_nosal, _ = run_track_a_suite(t2_dx[t2_dx['domain_outlier_flag'] == 'none'].copy(), 'delta13_dong_xuan_ex_salinity_125', coastal_int=True)
res_comb, pred_comb, _ = run_track_a_suite(t2_comb, 'delta13_combined_ht_td_130', coastal_int=False)

track_a_all = pd.concat([res_dx_full, res_dx_nosal, res_comb], ignore_index=True)
track_a_all.to_csv('results/metrics/track_a_delta13_model_comparison.csv', index=False, encoding='utf-8-sig')
pred_dx_full.to_csv('results/metrics/track_a_dx_test_predictions.csv', index=False, encoding='utf-8-sig')

# Full 10-year Leave-One-Year-Out Residual Diagnostics on 13-province Dong Xuan (for Salinity Error Attribution)
loyo_rows = []
for yr in sorted(t2_dx['harvest_year'].unique()):
    tr = t2_dx[t2_dx['harvest_year'] != yr]
    te = t2_dx[t2_dx['harvest_year'] == yr]
    _, p_huber, _ = fit_predict_spec('Huber_Anomaly_Weather', tr, te, ['province_id'], ['province_id'], PARSIMONIOUS_METEO, {'alpha': 10.0, 'epsilon': 1.35})
    _, p_base, _ = fit_predict_spec('Baseline_Median', tr, te, ['province_id'], ['province_id'], [], {})
    for idx, (_, r) in enumerate(te.iterrows()):
        loyo_rows.append({
            'province_id': r['province_id'],
            'province': r['province'],
            'ecological_subregion': r['ecological_subregion'],
            'harvest_year': int(r['harvest_year']),
            'yield_t_ha': float(r['yield_t_ha']),
            'pred_huber_loyo': round(float(p_huber[idx]), 4),
            'residual_huber': round(float(r['yield_t_ha'] - p_huber[idx]), 4),
            'abs_err_huber': round(float(abs(r['yield_t_ha'] - p_huber[idx])), 4),
            'abs_err_base': round(float(abs(r['yield_t_ha'] - p_base[idx])), 4),
            'oni_pre_season': float(r['oni_pre_season']),
            'pre_season_rain_90d_mm': float(r['pre_season_rain_90d_mm']),
            'domain_outlier_flag': r['domain_outlier_flag']
        })
loyo_df = pd.DataFrame(loyo_rows)
loyo_df.to_csv('results/metrics/track_a_dx_loyo_residuals_attribution.csv', index=False, encoding='utf-8-sig')

# Out-of-Region Spatial Heterogeneity Test on 13-province Dong Xuan
# Compare Weather-Only Anomaly Transfer: train on 3 core provinces (AG, KG, CT) vs train on other 10 provinces
core3_ids = {'an_giang', 'kien_giang', 'can_tho'}
dx_tr_core3 = t2_dx[(t2_dx['province_id'].isin(core3_ids)) & (t2_dx['harvest_year'] <= 2022)]
dx_tr_all13 = t2_dx[(t2_dx['harvest_year'] <= 2022) & (t2_dx['domain_outlier_flag'] == 'none')]
dx_te_other10 = t2_dx[(~t2_dx['province_id'].isin(core3_ids)) & (t2_dx['harvest_year'] >= 2023)]

# Fit province-mean baseline on each province's own 2015–2022 history, then transfer ONLY the weather slope beta
other10_hist = t2_dx[(~t2_dx['province_id'].isin(core3_ids)) & (t2_dx['harvest_year'] <= 2022)]
prov_base_other10 = fit_group_baseline(other10_hist, ['province_id'], agg='median')
y_base_other10 = predict_group_baseline(dx_te_other10, prov_base_other10)

# Weather slope learned ONLY from 3 core provinces (AG, KG, CT)
X_c3, y_res_c3, _, _, _ = build_anomaly_matrices(dx_tr_core3, dx_tr_core3, ['province_id'], PARSIMONIOUS_METEO)
_, _, X_o10_from_o10, y_mean_o10, _ = build_anomaly_matrices(other10_hist[other10_hist['domain_outlier_flag'] == 'none'], dx_te_other10, ['province_id'], PARSIMONIOUS_METEO)
mdl_c3_slope = HuberRegressor(alpha=10.0, max_iter=1000).fit(X_c3, y_res_c3)
pred_transfer_c3 = y_mean_o10 + mdl_c3_slope.predict(X_o10_from_o10)

# Weather slope learned from all 13 provinces (ex 2 salinity failures)
_, pred_full13_o10, _ = fit_predict_spec('Huber_Anomaly_Weather', dx_tr_all13, dx_te_other10, ['province_id'], ['province_id'], PARSIMONIOUS_METEO, {'alpha': 10.0, 'epsilon': 1.35})

spatial_transfer = pd.DataFrame([
    {'eval_target': '10_other_provinces_DX_2023_2024', 'method': 'Own_Province_Median_Baseline', **eval_metrics(dx_te_other10['yield_t_ha'], y_base_other10)},
    {'eval_target': '10_other_provinces_DX_2023_2024', 'method': 'Weather_Slope_Transferred_From_3Core_Provinces', **eval_metrics(dx_te_other10['yield_t_ha'], pred_transfer_c3)},
    {'eval_target': '10_other_provinces_DX_2023_2024', 'method': 'Weather_Slope_Trained_On_All_13_Provinces', **eval_metrics(dx_te_other10['yield_t_ha'], pred_full13_o10)}
])
spatial_transfer.to_csv('results/metrics/spatial_heterogeneity_transfer_test.csv', index=False, encoding='utf-8-sig')

# =============================================================================
# 8. VISUALIZATION — 6 PUBLICATION-QUALITY PNG FIGURES (300 DPI)
# =============================================================================

# --- Figure 1: Yield Distribution across 3 Seasons (Track B) & 13 Provinces (Track A) ---
fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={'width_ratios': [1.0, 1.35]})

season_labels = {'dong_xuan': 'Đông Xuân', 'he_thu': 'Hè Thu', 'thu_dong': 'Thu Đông'}
t1_plot = t1.copy()
t1_plot['Vụ'] = t1_plot['season'].map(season_labels)
sns.boxplot(data=t1_plot, x='Vụ', y='yield_t_ha', order=['Đông Xuân', 'Hè Thu', 'Thu Đông'],
            palette=['#2b6cb0', '#dd6b20', '#2f855a'], width=0.52, ax=axes[0], showfliers=False)
sns.stripplot(data=t1_plot, x='Vụ', y='yield_t_ha', hue='province', order=['Đông Xuân', 'Hè Thu', 'Thu Đông'],
              dodge=True, alpha=0.85, size=5.5, ax=axes[0])
axes[0].set_title('Tuyến B: Năng suất 3 vụ tách riêng\n(An Giang, Kiên Giang, Cần Thơ; 2015–2024, n=90)', fontsize=11, fontweight='bold')
axes[0].set_ylabel('Năng suất lúa (tấn/ha)')
axes[0].set_xlabel('')
axes[0].legend(title='Tỉnh', loc='lower left', fontsize=8.5)

sub_palette = {'upstream_alluvial_3crop': '#2b6cb0', 'middle_south_ql1': '#d69e2e', 'coastal_salinity_prone': '#c53030'}
sub_vn = {'upstream_alluvial_3crop': 'Thượng nguồn / Phù sa ngọt', 'middle_south_ql1': 'Vùng giữa / Nam QL1', 'coastal_salinity_prone': 'Ven biển nhạy mặn'}
order13 = t2_dx.groupby('province')['yield_t_ha'].median().sort_values(ascending=False).index.tolist()
t2_plot = t2_dx.copy()
t2_plot['Tiểu vùng'] = t2_plot['ecological_subregion'].map(sub_vn)
sns.boxplot(data=t2_plot, y='province', x='yield_t_ha', order=order13, hue='Tiểu vùng',
            palette={'Thượng nguồn / Phù sa ngọt': '#63b3ed', 'Vùng giữa / Nam QL1': '#f6e05e', 'Ven biển nhạy mặn': '#fc8181'},
            dodge=False, ax=axes[1], showfliers=True)
axes[1].annotate('Hạn mặn lịch sử:\n2016 (0,05) & 2020 (0,04)', xy=(0.15, order13.index('Bến Tre')),
                 xytext=(1.1, order13.index('Bến Tre') - 2.1),
                 arrowprops=dict(arrowstyle='->', color='#9b2c2c', lw=1.4),
                 fontsize=8.5, color='#9b2c2c', fontweight='bold')
axes[1].set_title('Tuyến A: Năng suất Đông Xuân đủ 13/13 tỉnh ĐBSCL\n(NSO 2015–2024 đã nâng cấp 2019 chính thức, n=127)', fontsize=11, fontweight='bold')
axes[1].set_xlabel('Năng suất lúa Đông Xuân (tấn/ha)')
axes[1].set_ylabel('')
axes[1].legend(title='Tiểu vùng sinh thái', loc='upper left', fontsize=8.5)

plt.tight_layout()
plt.savefig('results/figures/01_eda_yield_by_season_and_province.png', dpi=300)
plt.close()

# --- Figure 2: Seasonal Confounding (Raw vs Within-Season Anomaly Correlation) ---
fig, axes = plt.subplots(1, 2, figsize=(15, 5.8))
raw_corr_mat = t1[['t2m_max_mean_c', 'hot_days_gt35c', 'precip_total_mm', 'dry_days_lt1mm', 'rh2m_mean_pct', 'vpd_mean_kpa', 'pre_season_rain_90d_mm', 'oni_pre_season']].corr()
short_names = ['Tmax_TB', 'Ngày>35°C', 'Tổng mưa', 'Ngày khô', 'Ẩm RH', 'VPD', 'Mưa 90n trước', 'ENSO ONI']
sns.heatmap(raw_corr_mat, annot=True, fmt='.2f', cmap='RdBu_r', center=0, vmin=-1, vmax=1,
            xticklabels=short_names, yticklabels=short_names, ax=axes[0], cbar_kws={'shrink': 0.8})
axes[0].set_title('A. Đa cộng tuyến khí tượng thô (Seasonal Confounding)\nTuyến B (n=90) — nhiều cặp |r| > 0,90', fontsize=10.5, fontweight='bold')

piv_w = within_corr_df[(within_corr_df['track'] == 'track_b_3seasons') & (within_corr_df['feature'].isin(PARSIMONIOUS_METEO + ['hot_days_gt35c', 'dry_days_lt1mm', 'rh2m_mean_pct']))]
piv_mat = piv_w.pivot(index='feature', columns='scope', values='within_pearson_r')[['dong_xuan', 'he_thu', 'thu_dong', 'all_3_seasons_pooled']]
piv_mat.columns = ['Đông Xuân', 'Hè Thu', 'Thu Đông', 'Gộp 3 vụ']
feat_vn = {
    't2m_max_mean_c': 'Nhiệt cực đại TB', 'hot_days_gt35c': 'Số ngày >35°C',
    'precip_total_mm': 'Tổng lượng mưa', 'dry_days_lt1mm': 'Số ngày khô <1mm',
    'rh2m_mean_pct': 'Độ ẩm tương đối', 'vpd_mean_kpa': 'Khô khí quyển VPD',
    'ws2m_mean_ms': 'Tốc độ gió 2m', 'pre_season_rain_90d_mm': 'Mưa 90 ngày trước vụ',
    'oni_pre_season': 'Chỉ số ENSO (ONI)'
}
piv_mat.index = [feat_vn.get(i, i) for i in piv_mat.index]
sns.heatmap(piv_mat, annot=True, fmt='.2f', cmap='RdBu_r', center=0, vmin=-0.65, vmax=0.65, ax=axes[1], cbar_kws={'shrink': 0.8})
axes[1].set_title('B. Tương quan PHẦN DƯ (khử cố định Tỉnh × Vụ)\nLiên hệ khí tượng – năng suất thay đổi theo từng vụ', fontsize=10.5, fontweight='bold')
axes[1].set_xlabel('')
axes[1].set_ylabel('')

plt.tight_layout()
plt.savefig('results/figures/02_eda_collinearity_and_within_corr.png', dpi=300)
plt.close()

# --- Figure 3: Multi-Paradigm Model Comparison (Track B & Track A) + Error by Season ---
fig, axes = plt.subplots(1, 3, figsize=(19, 6.2), gridspec_kw={'width_ratios': [1.45, 1.0, 1.15]})

m_show_b = [
    'Baseline_Median', 'Structural_FE_Plus_Trend', 'OLS_Anomaly_Ortho5_Trend',
    'Ridge_Anomaly_Ortho5_Trend', 'Lasso_Anomaly_Ortho5_Trend', 'Huber_Anomaly_Ortho5_Trend',
    'DecisionTree_Anomaly_Trend', 'Shallow_RF_Anomaly_Trend', 'GBR_Anomaly_Trend',
    'SVR_Linear_Anomaly_Trend', 'SVR_RBF_Anomaly_Trend', 'MLP_ReLU_Anomaly_Trend', 'MLP_Tanh_Anomaly_Trend'
]
sub_b = t1_res_df[t1_res_df['model'].isin(m_show_b)].set_index('model').loc[m_show_b].reset_index()
short_b = ['Baseline', 'Cấu trúc\n+Trend', 'OLS\n+Trend', 'Ridge\n(L2)', 'Lasso\n(L1)', 'Huber\n(Robust)',
           'Decision\nTree', 'Random\nForest', 'GBR\nBoosting', 'SVR\nLinear', 'SVR\nRBF', 'MLP\nReLU', 'MLP\nTanh']
x = np.arange(len(short_b))
w = 0.36
axes[0].bar(x - w/2, sub_b['expanding_cv_mae'], width=w, label='Expanding CV (19–22)', color='#4299e1')
axes[0].bar(x + w/2, sub_b['test_2023_2024_mae'], width=w, label='Test khóa kín (23–24)', color='#2b6cb0')
axes[0].axhline(sub_b.loc[0, 'expanding_cv_mae'], color='#e53e3e', ls='--', lw=1.1, label='Baseline CV MAE')
axes[0].set_xticks(x); axes[0].set_xticklabels(short_b, fontsize=7.5, rotation=32, ha='right')
axes[0].set_ylim(0, 0.40)
axes[0].set_ylabel('MAE (tấn/ha)')
axes[0].set_title('A. Tuyến B: So sánh đa hình thái mô hình hồi quy (n=90)', fontsize=10.5, fontweight='bold')
axes[0].legend(fontsize=7.5, loc='upper right')

# Panel B: Track B Test MAE by Season across top model families
bd_season = pd.DataFrame(t1_breakdown)
bd_season = bd_season[(bd_season['group_type'] == 'season') & (bd_season['model'].isin(['Baseline_Median', 'Ridge_Anomaly_Ortho5_Trend', 'Huber_Anomaly_Ortho5_Trend', 'Shallow_RF_Anomaly_Trend', 'SVR_Linear_Anomaly_Trend', 'MLP_ReLU_Anomaly_Trend']))]
bd_season['Vụ'] = bd_season['group_value'].map(season_labels)
model_short_map = {
    'Baseline_Median': 'Baseline',
    'Ridge_Anomaly_Ortho5_Trend': 'Ridge (L2)',
    'Huber_Anomaly_Ortho5_Trend': 'Huber',
    'Shallow_RF_Anomaly_Trend': 'Random Forest',
    'SVR_Linear_Anomaly_Trend': 'SVR (Linear)',
    'MLP_ReLU_Anomaly_Trend': 'MLP (ReLU)'
}
bd_season['Mô hình'] = bd_season['model'].map(model_short_map)
sns.barplot(data=bd_season, x='Vụ', y='test_mae', hue='Mô hình', order=['Đông Xuân', 'Hè Thu', 'Thu Đông'], ax=axes[1])
axes[1].set_ylim(0, 0.43)
axes[1].set_title('B. Sai số Test MAE theo từng vụ (Tuyến B)', fontsize=10.5, fontweight='bold')
axes[1].set_ylabel('Test MAE 2023–2024 (tấn/ha)')
axes[1].set_xlabel('')
axes[1].legend(title='Mô hình', fontsize=7.3, loc='upper center', ncol=2)

# Panel C: Track A 13 provinces Dong Xuan Dual-Regime across model families
m_show_a = ['Baseline_Median_Prov', 'OLS_Anomaly_Weather', 'Ridge_Anomaly_Weather', 'Lasso_Anomaly_Weather', 'Huber_Anomaly_Weather', 'Shallow_RF_Anomaly', 'GBR_Anomaly', 'SVR_RBF_Anomaly', 'MLP_ReLU_Anomaly']
sub_a1 = res_dx_full[res_dx_full['model'].isin(m_show_a)].set_index('model').loc[m_show_a].reset_index()
sub_a2 = res_dx_nosal[res_dx_nosal['model'].isin(m_show_a)].set_index('model').loc[m_show_a].reset_index()
short_a = ['Baseline', 'OLS', 'Ridge', 'Lasso', 'Huber', 'RF', 'GBR', 'SVR\n(RBF)', 'MLP\n(ReLU)']
xa = np.arange(len(short_a))
axes[2].bar(xa - 0.18, sub_a1['expanding_cv_mae'], width=0.35, label='CV (Đủ 127 — có hạn mặn)', color='#fc8181')
axes[2].bar(xa + 0.18, sub_a1['test_2023_2024_mae'], width=0.35, label='Test 23–24 (Đủ 13 tỉnh)', color='#2f855a')
axes[2].plot(xa - 0.18, sub_a2['expanding_cv_mae'], 'o--', color='#742a2a', lw=1.4, label='CV (125 — bỏ 2 điểm mất trắng)')
axes[2].set_xticks(xa); axes[2].set_xticklabels(short_a, fontsize=7.5, rotation=28, ha='right')
axes[2].set_ylim(0, 0.83)
axes[2].set_ylabel('MAE (tấn/ha)')
axes[2].set_title('C. Tuyến A: 13 tỉnh Đông Xuân (Dual-Regime)', fontsize=10.5, fontweight='bold')
axes[2].legend(fontsize=7.2, loc='upper right')

plt.tight_layout()
plt.savefig('results/figures/03_model_comparison_tier1_and_tier2.png', dpi=300)
plt.close()

# --- Figure 4: Calendar (±10/±15d) & Spatial (Zonal vs Single-Point) Sensitivity ---
fig, ax = plt.subplots(figsize=(11, 5.8))
sc_order = ['zonal_shift_-15', 'zonal_shift_-10', 'zonal_shift_0', 'zonal_shift_+10', 'zonal_shift_+15', 'single_point_shift_0']
sc_labels = ['Zonal -15 ngày', 'Zonal -10 ngày', 'Zonal chuẩn (0)', 'Zonal +10 ngày', 'Zonal +15 ngày', '1 điểm (0)']
for m, col, mk in [('Baseline_Median', '#e53e3e', 's'), ('Ridge_Anomaly_Ortho5', '#2b6cb0', 'o'),
                   ('Ridge_Anomaly_Ortho5_Trend', '#2f855a', '^'), ('Huber_Anomaly_Ortho5', '#dd6b20', 'D')]:
    sub = sens_res_df[sens_res_df['model'] == m].set_index('scenario').loc[sc_order]
    ax.plot(sc_labels, sub['expanding_cv_mae'], marker=mk, lw=2, color=col, label=f'{m} (Expanding CV)')
    ax.plot(sc_labels, sub['test_mae'], marker=mk, lw=1.5, ls='--', color=col, alpha=0.75, label=f'{m} (Test 23–24)')
ax.set_ylabel('MAE (tấn/ha)')
ax.set_ylim(0.12, 0.37)
ax.set_title('Kiểm định độ nhạy sai số mô hình trước dịch chuyển lịch thời vụ (±10/±15 ngày) & không gian', fontsize=11, fontweight='bold', pad=12)
ax.legend(ncol=2, fontsize=8, loc='upper center', bbox_to_anchor=(0.5, -0.12), frameon=True)
plt.tight_layout()
plt.savefig('results/figures/04_sensitivity_calendar_and_spatial.png', dpi=300, bbox_inches='tight')
plt.close()

# --- Figure 5: Residual Error Attribution for Salinity Intrusion on 13 Provinces ---
fig, axes = plt.subplots(1, 2, figsize=(15.5, 5.8), gridspec_kw={'width_ratios': [1.35, 1.0]})
piv_res = loyo_df.pivot(index='province', columns='harvest_year', values='residual_huber').loc[order13]
sns.heatmap(piv_res, annot=True, fmt='.2f', cmap='RdBu', center=0, vmin=-2.5, vmax=2.5, ax=axes[0], cbar_kws={'label': 'Phần dư (Thực tế - Dự đoán, tấn/ha)'})
axes[0].set_title('A. Bản đồ phần dư LOYO (Huber thuần khí tượng) — 13 tỉnh Đông Xuân\nPhần dư âm cực đại tập trung đúng Bến Tre & Trà Vinh năm hạn mặn 2016, 2020', fontsize=10, fontweight='bold')
axes[0].set_xlabel('Năm thu hoạch')
axes[0].set_ylabel('')

# Panel B: Coastal Ben Tre & Tra Vinh pre-season rain vs Yield & ONI
coastal_2 = loyo_df[loyo_df['province'].isin(['Bến Tre', 'Trà Vinh'])]
sc = axes[1].scatter(coastal_2['pre_season_rain_90d_mm'], coastal_2['yield_t_ha'],
                     c=coastal_2['oni_pre_season'], cmap='coolwarm', s=100, edgecolor='black', vmin=-1.5, vmax=2.5)
for _, r in coastal_2.iterrows():
    if r['harvest_year'] in [2016, 2018, 2020, 2024]:
        axes[1].annotate(f"{r['province'][:2]}'{str(r['harvest_year'])[2:]}",
                         (r['pre_season_rain_90d_mm'] + 12, r['yield_t_ha'] + 0.15), fontsize=8.5, fontweight='bold')
cbar = plt.colorbar(sc, ax=axes[1])
cbar.set_label('Chỉ số ENSO (NOAA ONI tháng 11 năm t-1)')
axes[1].set_xlabel('Tổng mưa 90 ngày tiền vụ tại tỉnh (mm)')
axes[1].set_ylabel('Năng suất Đông Xuân (tấn/ha)')
axes[1].set_title('B. Chứng minh giới hạn khí tượng tại chỗ (OVB Hạn mặn)\n2020 mưa tại chỗ ngang 2018 nhưng vẫn sập mạnh do mặn lưu vực', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('results/figures/05_residual_attribution_salinity_13provinces.png', dpi=300)
plt.close()

# --- Figure 6: Spatial Generalization & External OOD Stress Test ---
fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.2))

s_abbr = {'dong_xuan': 'ĐX', 'he_thu': 'HT', 'thu_dong': 'TĐ'}
labels_ood = [f"{r['province']}\n{s_abbr.get(r['season'], r['season'])} {r['harvest_year']}" for _, r in ood_out.iterrows()]
x_o = np.arange(len(labels_ood))
axes[0].bar(x_o - 0.18, ood_out['abs_err_baseline'], width=0.35, label=f"Baseline vụ (MAE={ood_out['abs_err_baseline'].mean():.3f})", color='#a0aec0')
axes[0].bar(x_o + 0.18, ood_out['abs_err_ridge'], width=0.35, label=f"Ridge 3-tỉnh dự báo OOD (MAE={ood_out['abs_err_ridge'].mean():.3f})", color='#dd6b20')
axes[0].set_xticks(x_o); axes[0].set_xticklabels(labels_ood, fontsize=8.5)
axes[0].set_ylabel('Sai số tuyệt đối |y - ŷ| (tấn/ha)')
axes[0].set_title('A. Ngoại kiểm địa lý OOD (7 dòng Tiền Giang, Vĩnh Long, Cà Mau)\nĐo Domain Shift khi mang mô hình thượng nguồn sang vùng giữa & ven biển', fontsize=9.8, fontweight='bold')
axes[0].legend(fontsize=8.5)

x_t = np.arange(len(spatial_transfer))
t_labels = ['Baseline trung vị\nchính tỉnh đó', 'Chuyển hệ số khí tượng\ntừ 3 tỉnh thượng nguồn', 'Huấn luyện đầy đủ\ntrên cả 13 tỉnh']
bars = axes[1].bar(x_t, spatial_transfer['mae'], width=0.5, color=['#718096', '#ed8936', '#2b6cb0'])
for b, v in zip(bars, spatial_transfer['mae']):
    axes[1].text(b.get_x() + b.get_width()/2, v + 0.008, f'{v:.4f}', ha='center', fontweight='bold', fontsize=9.5)
axes[1].set_xticks(x_t); axes[1].set_xticklabels(t_labels, fontsize=9)
axes[1].set_ylabel('Test MAE 2023–2024 trên 10 tỉnh ngoài lõi (tấn/ha)')
axes[1].set_title('B. Kiểm định chuyển giao không gian (10 tỉnh vùng giữa & ven biển)\nVụ Đông Xuân 2023–2024', fontsize=9.8, fontweight='bold')

plt.tight_layout()
plt.savefig('results/figures/06_spatial_generalization_ood_check.png', dpi=300)
plt.close()

# =============================================================================
# 9. MASTER SUMMARY JSON FOR REPORTING
# =============================================================================
master_summary = {
    'vif_max_raw_7': float(vif_raw['vif'].max()),
    'vif_max_parsimonious_5': float(vif_pars['vif'].max()),
    'vif_max_demeaned_5': float(vif_anom['vif'].max()),
    'track_b_results': t1_res_df.to_dict(orient='records'),
    'track_a_dx_full_127': res_dx_full.to_dict(orient='records'),
    'track_a_dx_ex_salinity_125': res_dx_nosal.to_dict(orient='records'),
    'track_a_combined_130': res_comb.to_dict(orient='records'),
    'external_ood_7_summary': {
        'baseline_mae': round(float(ood_out['abs_err_baseline'].mean()), 4),
        'upstream_ridge_mae': round(float(ood_out['abs_err_ridge'].mean()), 4),
        'mean_signed_bias_upstream_overpredict': round(float(ood_out['signed_err_ridge'].mean()), 4)
    },
    'spatial_transfer_10_provinces': spatial_transfer.to_dict(orient='records'),
    'loyo_top5_salinity_residuals': loyo_df.sort_values('abs_err_huber', ascending=False).head(5)[['province', 'harvest_year', 'yield_t_ha', 'pred_huber_loyo', 'residual_huber', 'oni_pre_season']].to_dict(orient='records')
}
with open('results/metrics/master_analysis_summary.json', 'w', encoding='utf-8') as f:
    json.dump(master_summary, f, ensure_ascii=False, indent=2)

print('=== DONE: EDA, MODELING, SENSITIVITY, OOD & 6 FIGURES GENERATED ===')
print('\n--- VIF MAX COMPARISON ---')
print(f"Raw 7 collinear: {master_summary['vif_max_raw_7']:.2f} | Parsimonious 5: {master_summary['vif_max_parsimonious_5']:.2f} | Demeaned Anomaly 5: {master_summary['vif_max_demeaned_5']:.2f}")
print('\n--- TRACK B (3 SEASONS, n=90) ---')
print(t1_res_df[['model', 'train_2015_2022_mae', 'expanding_cv_mae', 'val_2021_2022_mae', 'test_2023_2024_mae', 'test_2023_2024_r2', 'delta_test_mae_vs_base']].to_string(index=False))
print('\n--- TRACK A (13 PROVINCES DONG XUAN FULL 127 vs EX-SALINITY 125) ---')
print(res_dx_full[['model', 'expanding_cv_mae', 'test_2023_2024_mae', 'test_2023_2024_rmse']].to_string(index=False))
print('\nEx-salinity 125:')
print(res_dx_nosal[['model', 'expanding_cv_mae', 'test_2023_2024_mae', 'test_2023_2024_rmse']].to_string(index=False))
print('\n--- TRACK A COMBINED HT-TD (13 PROVINCES, n=130) ---')
print(res_comb[['model', 'expanding_cv_mae', 'test_2023_2024_mae', 'test_2023_2024_rmse']].to_string(index=False))
print('\n--- EXTERNAL OOD 7 ROWS ---')
print(ood_out.to_string(index=False))
print('\n--- SPATIAL TRANSFER 10 PROVINCES ---')
print(spatial_transfer.to_string(index=False))
print('\n--- TOP 5 LOYO RESIDUALS (SALINITY ATTRIBUTION) ---')
print(pd.DataFrame(master_summary['loyo_top5_salinity_residuals']).to_string(index=False))
