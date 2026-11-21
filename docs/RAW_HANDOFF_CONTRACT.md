# Hợp đồng Bàn giao Đầu ra Bước Cào dữ liệu → Đầu vào Bước Làm sạch

> **Trạng thái cổng kiểm định (`Raw-to-Cleaning Handoff Gate`):** **ĐẠT (`PASS`)** — kiểm chứng tự động qua `node scripts/verify_raw_handoff.mjs` (`docs/raw_handoff_readiness.json`).  
> **Nguyên tắc bàn giao:** Toàn bộ tệp dưới đây là dữ liệu thô đã trích bảng có truy xuất nguồn gốc 100% (`source_file`, `source_url`, `source_sha256`); **chưa** quy đổi đơn vị, **chưa** chuẩn hóa số, **chưa** chọn phiên bản, **chưa** tổng hợp thời tiết hay ghép bảng.

---

## 1. Danh mục 4 khối Input bàn giao cho bước Làm sạch

| Khối | Tệp bàn giao (Input cho Cleaning) | Quy mô & Phạm vi | Kiểm định kỹ thuật |
|---|---|---|---|
| **Khối 1: Lúa thô** | • `data/raw/rice_captured_main_seasons.csv`<br>• `data/raw/nso_rice_province_tables.csv`<br>• `data/raw/nso_rice_2021_reconciliation.csv`<br>• `data/raw/rice_report_season_values.csv`<br>• `data/catalog/rice_collection_coverage.csv` | • 90 dòng 3 vụ riêng (`An Giang`, `Kiên Giang`, `Cần Thơ`; 2015–2024)<br>• 467 dòng NSO nền 13 tỉnh (NGTK 2019 & 2024)<br>• 233 dòng NSO NGTK 2021 (chứa **47 dòng 2019 chính thức** đối chiếu bản sơ bộ)<br>• 7 dòng báo cáo năm tỉnh (`Tiền Giang` TĐ 2021–2024; `Vĩnh Long` HT & TĐ 2023; `Cà Mau` HT 2024)<br>• 390 ô kiểm kê (**194 ô** có giá trị tách vụ) | 0 ô trống dữ liệu; 100% SHA-256 khớp `source_catalog.json`; 90 dòng tỉnh khớp NSO Đông Xuân 0 sai lệch & tổng HT+TĐ < 0,5%. |
| **Khối 2: Khí tượng ngày** | • `data/raw/weather_daily_raw.csv`<br>• `data/catalog/weather_inventory.csv`<br>• `config/weather_grid.json` | 132.594 dòng điểm–ngày (33 tệp NASA POWER × 4.018 ngày từ `2014-01-01` đến `2024-12-31`, múi giờ `LST`). | 0 trùng khóa `(point_id, date_yyyymmdd)`; 0 `fill_value` (-999); 0 vi phạm miền vật lý trên 6 biến chung. |
| **Khối 3: Lịch thời vụ thô** | • `data/raw/season_calendar_raw.csv`<br>• `data/catalog/calendar_vietnam_rice_reference.csv` | • 17 bản ghi trích nguyên văn từ **9 văn bản chính thức `.gov.vn`** (khung 3 vụ & 2 vụ Cục Trồng trọt, chỉ đạo tiểu vùng 2014–2024, tiến độ tỉnh, tham chiếu giống 100–105 ngày)<br>• 5 dòng đối chiếu lịch sử SAGE/Sacks | Phủ đủ cả 3 vụ (`Lúa đông xuân`, `Lúa hè thu`, `Lúa thu đông`); 100% khớp nguyên văn với tệp nguồn đã tải & SHA-256. |
| **Khối 4: Ranh giới & Ánh xạ lưới** | • `data/raw/geo/gadm41_VNM_1.json`<br>• `data/catalog/weather_grid_province_overlap.csv` | • GADM v4.1 Level 1: 63 tỉnh Việt Nam trước 2025 (**13/13 tỉnh ĐBSCL**)<br>• 55 dòng ánh xạ giao cắt diện tích giữa 13 tỉnh và 30 ô lưới MERRA-2 (`0,5° × 0,625°`) | **21 ô** phủ ĐBSCL, loại rõ **9 ô biển/ngoài vùng**; **13/13 tỉnh** có hồ sơ trọng số không gian hoàn toàn riêng biệt (tổng trọng số mỗi tỉnh = `1,0000`). |

---

## 2. Chốt phạm vi & Quy tắc nghiệp vụ chuyển giao cho bước Làm sạch

1. **Định vị chính xác phạm vi bắt buộc (theo `DeTaiPTDL.pdf` — KHÔNG coi 13 tỉnh là phần mở rộng):**
   - **Phạm vi chính thức phải thực hiện là TOÀN VÙNG 13 TỈNH ĐBSCL (2015–2024)**, được triển khai qua **2 tuyến dữ liệu song hành cùng thuộc phạm vi chính**:
     - **Tuyến A — Toàn vùng 13 tỉnh ĐBSCL (nguồn NSO):** Vụ `Lúa đông xuân` (127/130 ô) và cụm `Lúa hè thu và thu đông` gộp (130/130 ô) bảo đảm độ phủ địa lý đủ 13/13 tỉnh qua cả 3 tiểu vùng sinh thái.
     - **Tuyến B — Tách riêng 3 mùa vụ ĐBSCL (nguồn Niên giám tỉnh):** 3 tỉnh có Niên giám 10 năm chính thức đầy đủ (`An Giang`, `Kiên Giang`, `Cần Thơ` = **90 quan sát chuẩn**, chiếm **40,5% sản lượng toàn ĐBSCL**). 7 bản ghi lẻ từ báo cáo năm (`Tiền Giang`, `Vĩnh Long`, `Cà Mau`) được làm sạch ở bảng đối chiếu riêng, không trộn vào bảng cân bằng 10 năm.
2. **Xử lý xung đột phiên bản 2019 (bắt buộc):**
   - Đối chiếu `nso_rice_2021_reconciliation.csv` phát hiện **25/47 dòng năm 2019 có điều chỉnh** giữa NGTK 2019 (`Sơ bộ`) và NGTK 2021 (`Chính thức`) ở mục `Lúa cả năm` và `Lúa hè thu và thu đông` (riêng `Lúa đông xuân` khớp 100%). Bước Làm sạch bắt buộc áp luật ưu tiên `NGTK tỉnh 2024 > NSO chính thức (NGTK 2021/2024) > NSO sơ bộ > Báo cáo năm tỉnh` và xuất `reconciliation_log.csv`.
3. **Chuẩn hóa số, đơn vị & xử lý Domain Outliers:**
   - Quy đổi toàn bộ về `ha`, `tấn/ha` (`tạ/ha / 10`), `tấn` (`nghìn ha × 1000`, `nghìn tấn × 1000`).
   - Khi kiểm tra `Diện tích × Năng suất vs Sản lượng`, kết hợp ngưỡng 1% với **biên làm tròn tuyệt đối `±0,1 nghìn tấn`** của NSO để **không xóa nhầm** các năm hạn mặn lịch sử (Bến Tre Đông Xuân 2016 `0,5 tạ/ha`, 2020 `0,4 tạ/ha`) và lưu ý phân biệt diện tích thu hoạch (`99,18%`) ở Cà Mau Hè Thu 2024.
4. **Chuẩn hóa Khí tượng & Áp mặt nạ không gian:**
   - Khóa tập **6 biến chung toàn lưới**: `T2M`, `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, `RH2M`, `WS2M` (không dùng `ALLSKY_SFC_SW_DWN` làm biến bắt buộc vì thiếu ở 20 ô lưới bổ sung).
   - Dùng trực tiếp trọng số `province_area_weight` trong `data/catalog/weather_grid_province_overlap.csv` để tính chuỗi ngày trung bình có trọng số diện tích cho từng trong 13 tỉnh (giải quyết triệt để lỗi trùng ô lưới ở Bến Tre–Trà Vinh–Vĩnh Long và Cần Thơ–Hậu Giang).
5. **Xây dựng Lịch thời vụ & Kiểm định độ nhạy (Sensitivity Analysis):**
   - Dựng bảng lịch chuẩn từ `season_calendar_raw.csv` theo khung chính thức Cục Trồng trọt (Vùng 3 vụ: ĐX xuống giống `10/11–30/12`, HT `15/4–15/5`, TĐ `20/7–20/8`; kết hợp thời gian sinh trưởng ~100–105 ngày và phân vùng sinh thái ven biển/phù sa ngọt/thượng nguồn; Đông Xuân luôn cắt từ cuối năm `t-1`).
   - Bắt buộc chạy kiểm định độ nhạy dịch cửa sổ `±10` và `±15` ngày ở bước tổng hợp đặc trưng.

---

## 3. Lệnh tái lập & kiểm chứng toàn bộ đầu ra bước Cào (không cần mạng)

```powershell
node scripts/inventory_raw.mjs
node scripts/capture_rice_tables_raw.mjs
node scripts/capture_nso_rice_raw.mjs
node scripts/capture_nso_2021_reconciliation_raw.mjs
node scripts/capture_report_values_raw.mjs
node scripts/capture_calendar_raw.mjs
node scripts/verify_geo_grid_mapping.mjs
node scripts/audit_collection_coverage.mjs
node scripts/verify_raw_handoff.mjs
```
