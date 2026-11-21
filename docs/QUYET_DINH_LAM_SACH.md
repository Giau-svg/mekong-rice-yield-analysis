# Phương án và Quyết định Nghiệp vụ – Kỹ thuật Giai đoạn Làm sạch Dữ liệu

> **Trạng thái kiểm định (`scripts/verify_cleaned_datasets.mjs`):** **PASS (`cleaning_verification_passed: true`, `ready_for_eda_and_modeling: true`)** — chi tiết định lượng tại `docs/cleaning_verification_report.json`.  
> **Nguyên tắc xuyên suốt:** Bảo toàn 100% tệp gốc trong `data/raw/`; mọi quyết định hợp nhất, quy đổi, ánh xạ không gian và cửa sổ thời vụ đều viết bằng mã tái lập có `assert` tự động và xuất log kiểm toán riêng.

---

## 1. Kiến trúc 5 bước của Pipeline Làm sạch

```text
data/raw/ (4 khối Input đã đạt Handoff Gate)
  ├── [1] scripts/clean_rice_data.mjs        ──► data/interim/rice_tier1_core_3seasons.csv (90)
  │                                          ──► data/interim/rice_tier2_delta13_nso.csv (257)
  │                                          ──► data/interim/rice_supplemental_reports.csv (7)
  │                                          ──► data/interim/rice_reconciliation_log.csv (56)
  │                                          ──► data/interim/rice_cleaning_quality_audit.csv (354)
  ├── [2] scripts/clean_weather_zonal.mjs    ──► data/interim/weather_daily_province_zonal.csv (52.234)
  │                                          ──► data/interim/weather_daily_province_single_point.csv (52.234)
  ├── [3] scripts/clean_season_calendar.mjs  ──► data/interim/season_calendar_clean.csv (520)
  │                                          ──► data/interim/season_calendar_sensitivity_shifts.csv (2.600)
  ├── [4] scripts/build_clean_datasets.mjs   ──► data/processed/tier1_core_3seasons_model_ready.csv (90)
  │                                          ──► data/processed/tier2_delta13_dong_xuan_model_ready.csv (127)
  │                                          ──► data/processed/tier2_delta13_combined_ht_td_model_ready.csv (130)
  │                                          ──► data/processed/tier1_sensitivity_calendar_and_spatial.csv (540)
  └── [5] scripts/verify_cleaned_datasets.mjs ──► docs/cleaning_verification_report.json
```

---

## 2. Sáu Quyết định Nghiệp vụ – Kỹ thuật cốt lõi và Lý do lựa chọn

### Quyết định 1: Tổ chức 2 tuyến phân tích song hành cho phạm vi bắt buộc toàn vùng ĐBSCL (không ép gộp nhân tạo thành 390 dòng)
- **Nguyên tắc phạm vi (theo `DeTaiPTDL.pdf`):** **Toàn vùng 13 tỉnh ĐBSCL (2015–2024) là phạm vi chính thức phải thực hiện của đồ án — KHÔNG phải phần mở rộng.** Do cấu trúc công bố thống kê công khai tại Việt Nam (NSO quốc gia công bố đầy đủ 13/13 tỉnh nhưng gộp `Hè Thu và Thu Đông`, còn Niên giám cấp tỉnh công khai PDF tách riêng 3 vụ suốt 10 năm hiện chỉ có ở 3/13 cổng tỉnh), phạm vi chính thức toàn ĐBSCL được tách thành **2 tuyến dữ liệu song hành cùng thuộc phạm vi chính**:
  - **Tuyến A — Toàn vùng 13 tỉnh ĐBSCL (`tier2_delta13_dong_xuan_model_ready.csv`, 127 dòng & `tier2_delta13_combined_ht_td_model_ready.csv`, 130 dòng):** Đảm bảo độ phủ không gian bắt buộc **13/13 tỉnh ĐBSCL** suốt 2015–2024 trên cả 3 tiểu vùng sinh thái (thượng nguồn – vùng giữa – ven biển hạn mặn).
  - **Tuyến B — Tách riêng 3 mùa vụ trong vùng ĐBSCL (`tier1_core_3seasons_model_ready.csv`, 90 dòng):** Bảng cân bằng `3 tỉnh trọng điểm (An Giang, Kiên Giang, Cần Thơ — chiếm 40,5% sản lượng toàn ĐBSCL) × 10 năm × 3 vụ tách riêng (dong_xuan, he_thu, thu_dong)`, thực hiện đúng phương án dự phòng đã đăng ký trong `DeTaiPTDL.pdf` để phân tích riêng rẽ Hè Thu và Thu Đông mà không chế biến dữ liệu.
  - **Bảng đối chiếu báo cáo lẻ (`rice_supplemental_reports.csv`, 7 dòng):** Lưu riêng 7 bản ghi lẻ từ báo cáo năm (Tiền Giang, Vĩnh Long, Cà Mau), không trộn lẫn vào bảng cân bằng 10 năm.
- **Phương án bị loại & Lý do:** Không chia tách nhân tạo bảng gộp Hè Thu–Thu Đông của NSO, không điền 0 cho 3 ô bỏ trống ở Cà Mau (Đông Xuân 2015, 2016, 2018), và tuyệt đối không coi 13 tỉnh là "phần mở rộng" hay coi 3 tỉnh là "đại diện đủ cho vùng ven biển ĐBSCL".

### Quyết định 2: Thang ưu tiên nguồn & Nâng cấp bắt buộc năm 2019 từ Sơ bộ lên Chính thức
- **Phương án chọn:** Áp thang ưu tiên `Niên giám tỉnh 2024 > NSO chính thức (NGTK 2021 cho năm 2019; NGTK 2019 cho 2015–2018; NGTK 2024 cho 2020–2023) > NSO sơ bộ (2024) > Báo cáo năm cấp tỉnh`. Mọi quyết định chọn/loại được ghi vào `data/interim/rice_reconciliation_log.csv` (**56 quyết định**).
- **Bằng chứng thực tế:** Trong Tầng 2, **13/13 tỉnh** mục `Hè Thu–Thu Đông` năm 2019 thực sự có điều chỉnh số liệu khi chuyển từ NGTK 2019 (Sơ bộ) sang NGTK 2021 (Chính thức); riêng 13/13 tỉnh `Đông Xuân` 2019 khớp 100%. Sau làm sạch, **0 dòng năm 2019 sơ bộ** còn tồn tại trong Tầng 2.

### Quyết định 3: Kiểm tra sản lượng kết hợp biên làm tròn nguồn & Bảo toàn Domain Outliers hạn mặn
- **Phương án chọn:**
  - Chuẩn hóa toàn bộ định dạng số Việt Nam (`.` hàng nghìn, `,` thập phân) sang hệ đơn vị thống nhất: `ha`, `tấn/ha` (`tạ/ha ÷ 10`), `tấn`.
  - Kiểm tra công thức `Diện tích × Năng suất vs Sản lượng` theo ngưỡng tương đối `1%` **kết hợp biên làm tròn nửa đơn vị gốc của NSO** (`±50 tấn`, `±50 ha`, `±0,005 tấn/ha`). Kết quả: **349 dòng `pass`**, **4 dòng `pass_within_source_rounding`** (Bến Tre Đông Xuân 2016, 2020, 2023, 2024), **1 dòng `pass_harvested_area_basis_note`** (Cà Mau Hè Thu 2024 thu hoạch 99,18% diện tích gieo trồng), **0 lỗi vượt biên**.
  - **Không xóa outlier thật:** Gắn cờ `domain_outlier_flag = extreme_salinity_crop_failure` cho **Bến Tre Đông Xuân 2016 (`0,05 tấn/ha`) và 2020 (`0,04 tấn/ha`)** — hai đợt hạn mặn lịch sử ĐBSCL — để giữ nguyên dữ liệu thực và chạy kiểm định độ nhạy (có/không có điểm cực đoan mặn) ở bước mô hình.

### Quyết định 4: Khí tượng Trung bình theo diện tích chồng lấp (Area-Weighted Zonal Mean) & 6 biến chung
- **Phương án chọn:**
  - Dùng trọng số diện tích từ GADM v4.1 (`data/catalog/weather_grid_province_overlap.csv`) trên **21 ô lưới MERRA-2 phủ đất liền** (loại bỏ **9 ô biển/ngoài vùng**) để tính chuỗi khí tượng ngày cho từng trong 13 tỉnh (`52.234` dòng, 0 missing, 0 vi phạm vật lý).
  - Khóa tập **6 biến chung toàn lưới**: `T2M`, `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, `RH2M`, `WS2M` (loại `ALLSKY_SFC_SW_DWN` khỏi feature bắt buộc vì 20 ô bổ sung không tải biến này và độ phân giải gốc CERES thô hơn `1° × 1°`).
- **Lý do & Bằng chứng:** Giải quyết triệt để lỗi trùng 100% đặc trưng MERRA-2 giữa `Bến Tre–Trà Vinh–Vĩnh Long` và `Cần Thơ–Hậu Giang` → **13/13 tỉnh có hồ sơ khí tượng tách biệt hoàn toàn**. Đồng thời xuất chuỗi `single_point` để kiểm định độ nhạy: trên 3 tỉnh lõi, tương quan giữa `zonal_mean` và `single_point` đạt **$r = 0{,}9967\text{–}0{,}9994$** (sai lệch nhiệt độ trung bình chỉ `0,043°C`).

### Quyết định 5: Lịch thời vụ phân theo 3 tiểu vùng sinh thái (Tier B) + Kiểm định độ nhạy `±10 / ±15 ngày`
- **Phương án chọn:** Dựng cửa sổ sinh trưởng (~107–123 ngày, phù hợp chu kỳ giống ngắn ngày 100–105 ngày + rải trà xuống giống) dựa trực tiếp trên **17 bản ghi văn bản chính thức Cục Trồng trọt / Bộ NN&PTNT** (`season_calendar_raw.csv`), chia 3 tiểu vùng sinh thái:
  - *Thượng nguồn / Phù sa ngọt 3 vụ* (`An Giang`, `Đồng Tháp`, `Cần Thơ`, `Kiên Giang`): ĐX `15/11(t-1)–15/03(t)`, HT `15/04–31/07`, TĐ `25/07–15/11`.
  - *Vùng giữa / Nam QL1* (`Vĩnh Long`, `Tiền Giang`, `Hậu Giang`, `Sóc Trăng`, `Long An`): ĐX `10/11(t-1)–10/03(t)`, HT `01/05–15/08`, TĐ `01/08–20/11`.
  - *Ven biển nhạy mặn* (`Bến Tre`, `Trà Vinh`, `Bạc Liêu`, `Cà Mau`): ĐX `25/10(t-1)–25/02(t)` (xuống giống sớm né mặn), HT `15/05–31/08` (đợi mưa rửa mặn), TĐ `01/08–20/11`.
- **Kiểm định độ nhạy định lượng (`tier1_sensitivity_calendar_and_spatial.csv`, 540 dòng):**
  - Dịch **±10 ngày:** Các biến trung bình/tổng cực kỳ bền vững (`T2M`: $r = 0{,}971\text{–}0{,}988$; `PRECTOTCORR`: $r = 0{,}979\text{–}0{,}987$; `dry_days_lt1mm`: $r = 0{,}992\text{–}0{,}993$).
  - Dịch **±15 ngày:** Biến ngưỡng cực đoan **`hot_days_gt35c` nhạy nhất với mốc lịch** ($r = 0{,}831\text{–}0{,}880$, MAD `7,3–7,6 ngày`) vì nắng nóng >35°C tập trung gắt giai đoạn chuyển mùa tháng 3–4 → bước mô hình bắt buộc kiểm tra độ ổn định sai số trên tập độ nhạy này.

### Quyết định 6: Kiểm soát chống rò rỉ dữ liệu (Anti-Leakage) ngay tại bảng đầu ra
- Khóa sẵn cột chia thời gian tăng dần `time_split`: **`train` (2015–2020: 54 dòng Tầng 1 / 75 dòng Tầng 2 ĐX)**, **`val` (2021–2022: 18 / 26 dòng)**, **`test` (2023–2024: 18 / 26 dòng)** — không dùng random split.
- Bảo lưu `area_ha` và `production_t` với vai trò **mô tả/đối chiếu**, tuyệt đối không đưa vào ma trận đặc trưng `X` dự báo `yield_t_ha`.
- Kiểm định 0 ngày khí tượng thiếu trong mọi cửa sổ trước khi tổng hợp `precip_total_mm` và các biến đếm ngày.

---

## 3. Kiểm tra nhanh tính hợp lý nông học trên bộ sạch Tầng 1 (90 dòng)

| Vụ lúa (An Giang, Kiên Giang, Cần Thơ; 2015–2024) | Số mẫu | Min (tấn/ha) | Trung vị (tấn/ha) | Trung bình (tấn/ha) | Max (tấn/ha) |
|---|---:|---:|---:|---:|---:|
| **Đông Xuân (`dong_xuan`)** | 30 | 6,024 | 7,329 | 7,223 | 7,750 |
| **Hè Thu (`he_thu`)** | 30 | 5,112 | 5,689 | 5,692 | 6,133 |
| **Thu Đông (`thu_dong`)** | 30 | 4,650 | 5,505 | 5,467 | 6,239 |

Kết quả phân bậc năng suất **Đông Xuân > Hè Thu > Thu Đông** và biên độ biến động lớn nhất ở Thu Đông phản ánh chính xác thực tế sản xuất lúa vùng ĐBSCL.

---

## 4. Lệnh chạy lại toàn bộ Pipeline Làm sạch (tái lập 100%, không cần mạng)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_cleaning_pipeline.ps1
```
