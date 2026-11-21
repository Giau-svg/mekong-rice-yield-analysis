# Từ điển dữ liệu (Data Dictionary)

Định dạng chung: CSV UTF-8 có BOM, dấu phẩy phân cột, dấu chấm thập phân (`.`), ngày chuẩn ISO `YYYY-MM-DD`, ô trống là không có thông tin.  
Chi tiết quyết định làm sạch xem tại [QUYET_DINH_LAM_SACH.md](QUYET_DINH_LAM_SACH.md).

## 1. Bảng đầu ra chính thức sẵn sàng cho EDA & Mô hình (`data/processed/`)

> **Phạm vi chính thức của đồ án:** Toàn vùng 13 tỉnh Đồng bằng sông Cửu Long (2015–2024), triển khai đồng thời qua 2 tuyến dữ liệu song hành cùng thuộc phạm vi chính (không coi 13 tỉnh là phần mở rộng).

- `data/processed/tier2_delta13_dong_xuan_model_ready.csv`: **127 dòng** (**Tuyến toàn vùng 13/13 tỉnh ĐBSCL**; 2015–2024; vụ Đông Xuân, đã cập nhật 2019 chính thức).
- `data/processed/tier2_delta13_combined_ht_td_model_ready.csv`: **130 dòng** (**Tuyến toàn vùng 13/13 tỉnh ĐBSCL**; 2015–2024; cụm Hè Thu–Thu Đông gộp, đã cập nhật 2019 chính thức).
- `data/processed/tier1_core_3seasons_model_ready.csv`: **90 dòng** (**Tuyến tách riêng 3 mùa vụ trong vùng ĐBSCL**; `An Giang`, `Kiên Giang`, `Cần Thơ` — chiếm 40,5% sản lượng ĐBSCL; 2015–2024).
- `data/processed/tier1_sensitivity_calendar_and_spatial.csv`: **540 dòng** (90 dòng tuyến tách 3 vụ × 6 kịch bản độ nhạy lịch `0/±10/±15 ngày` và không gian `zonal` vs `single_point`).

| Trường | Vai trò | Kiểu / Đơn vị | Ý nghĩa |
|---|---|---|---|
| `dataset_tier` | Metadata | string | Phân tầng tập dữ liệu (`tier1_core_3seasons`, `tier2_delta13_nso`) |
| `province_id` / `province` | Khóa / Feature phân loại | string | Mã tỉnh chuẩn / tên 13 tỉnh ĐBSCL theo địa giới trước 2025 |
| `ecological_subregion` | Feature phân loại / Nhóm | string | Tiểu vùng sinh thái: `upstream_alluvial_3crop`, `middle_south_ql1`, `coastal_salinity_prone` |
| `harvest_year` | Khóa / Trục thời gian | int (2015–2024) | **Năm thu hoạch** (Đông Xuân gieo từ cuối năm `harvest_year - 1`) |
| `season` | Khóa / Feature phân loại | string | `dong_xuan`, `he_thu`, `thu_dong`, `he_thu_thu_dong_combined` |
| `season_scope` | Kiểm soát phạm vi | string | `single` (vụ đơn chuẩn) hoặc `combined_he_thu_thu_dong` (vụ gộp NSO) |
| `time_split` | Chia tập chống leakage | string | `train` (2015–2020), `val` (2021–2022), `test` (2023–2024) |
| `yield_t_ha` | **Target (biến mục tiêu)** | float (tấn/ha) | Năng suất lúa quy đổi từ `tạ/ha ÷ 10` |
| `area_ha` | **Chỉ mô tả (KHÔNG làm feature)** | float (ha) | Diện tích gieo trồng quy đổi về ha |
| `production_t` | **Chỉ mô tả (KHÔNG làm feature)** | float (tấn) | Sản lượng quy đổi về tấn (cấm đưa vào đầu vào mô hình để tránh leakage) |
| `spatial_method` | Metadata không gian | string | `gadm_area_weighted_zonal_mean` (chính) hoặc `single_acquisition_point` (độ nhạy) |
| `calendar_tier` / `calendar_shift_days` | Metadata lịch vụ | string / int | Phân tầng khung lịch (`B_official_subregional_framework`) và độ dịch ngày (`0, ±10, ±15`) |
| `window_start_date` / `window_end_date` | Cửa sổ khí tượng | date (`YYYY-MM-DD`) | Ngày đầu – cuối cửa sổ mùa vụ dùng cắt chuỗi khí tượng ngày |
| `cross_calendar_year` | Kiểm soát năm | bool | `true` với vụ Đông Xuân vắt qua 2 năm dương lịch |
| `window_days` / `grid_cells_used` | Kiểm soát tổng hợp | int | Số ngày khí tượng hợp lệ trong vụ (0 ngày thiếu) / số ô MERRA-2 giao cắt tỉnh |
| `t2m_mean_c` | Feature khí tượng | float (°C) | Nhiệt độ trung bình 2m suốt cửa sổ mùa vụ |
| `t2m_max_mean_c` / `t2m_max_peak_c` | Feature khí tượng | float (°C) | Nhiệt độ cực đại ngày trung bình / đỉnh nhiệt cực đại cả vụ |
| `t2m_min_mean_c` | Feature khí tượng | float (°C) | Nhiệt độ cực tiểu ngày trung bình cả vụ |
| `precip_total_mm` / `precip_mean_mm_day` | Feature khí tượng | float (mm / mm·ngày⁻¹) | Tổng lượng mưa cả vụ / lượng mưa trung bình ngày (`PRECTOTCORR`) |
| `rh2m_mean_pct` | Feature khí tượng | float (%) | Độ ẩm tương đối trung bình 2m cả vụ |
| `ws2m_mean_ms` | Feature khí tượng | float (m/s) | Tốc độ gió trung bình 2m cả vụ |
| `hot_days_gt35c` | Feature cực đoan | int (ngày) | Số ngày có `T2M_MAX > 35°C` trong vụ |
| `dry_days_lt1mm` / `dry_days_lt2mm` | Feature cực đoan / Độ nhạy | int (ngày) | Số ngày mưa `< 1 mm` (chính) và `< 2 mm` (độ nhạy ngưỡng khô) |
| `heavy_rain_days_gt20mm` | Feature cực đoan | int (ngày) | Số ngày mưa lớn `>= 20 mm` trong vụ |
| `revision_status` / `source_tier` | Truy xuất phiên bản | string | `official` vs `preliminary` (2024) và cấp nguồn ưu tiên |
| `formula_check_status` | Kiểm soát chất lượng | string | `pass` hoặc `pass_within_source_rounding` |
| `domain_outlier_flag` | Cờ sự kiện cực đoan | string | `none` hoặc `extreme_salinity_crop_failure` (Bến Tre ĐX 2016 & 2020 — bảo toàn, không xóa) |
| `source_file` / `source_sha256` / `source_locator` | Truy xuất nguồn gốc | string | Tệp nguồn gốc trong `data/raw/`, mã băm SHA-256 và trang PDF / block HTML |
| `sensitivity_scenario` *(chỉ trong file độ nhạy)* | Nhãn kịch bản | string | `zonal_shift_0`, `zonal_shift_-15`, `zonal_shift_-10`, `zonal_shift_+10`, `zonal_shift_+15`, `single_point_shift_0` |

## 2. Bảng trung gian & Kiểm toán (`data/interim/`)

- `rice_tier1_core_3seasons.csv` (90), `rice_tier2_delta13_nso.csv` (257), `rice_supplemental_reports.csv` (7): Bảng lúa đã chuẩn hóa đơn vị trước khi ghép khí tượng.
- `rice_reconciliation_log.csv` (56 dòng): Nhật ký từng quyết định chọn phiên bản nguồn (bao gồm nâng cấp 2019 sơ bộ → NGTK 2021 chính thức và đối chiếu NGTK tỉnh vs NSO).
- `rice_cleaning_quality_audit.csv` (354 dòng): Sai số tuyệt đối, sai số tương đối, biên làm tròn nguồn và cờ domain outlier của toàn bộ bản ghi lúa.
- `weather_daily_province_zonal.csv` (52.234 dòng) & `weather_daily_province_single_point.csv` (52.234 dòng): Chuỗi khí tượng ngày chuẩn hóa 13 tỉnh × 4.018 ngày (2014–2024, `LST`, 6 biến chung).
- `season_calendar_clean.csv` (520 dòng) & `season_calendar_sensitivity_shifts.csv` (2.600 dòng): Cửa sổ thời vụ 13 tỉnh × 10 năm × 4 hạng mục vụ cho 5 mức dịch `{0, -15, -10, +10, +15}` ngày.
