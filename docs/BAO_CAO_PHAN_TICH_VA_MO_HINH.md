# Báo cáo Phân tích Dữ liệu (EDA), Kiểm định Thống kê và So sánh Đa Mô hình

> **Học phần:** Phân tích dữ liệu — Khoa CNTT, Trường Đại học Sài Gòn (**CBGD: Phan Thành Huấn**)  
> **Sinh viên thực hiện:** Lê Thị Ngọc Giàu (`3123410088`) · Trần Ngọc An (`3123410004`)  
> **Phạm vi chính thức (`DeTaiPTDL.pdf`):** Toàn vùng Đồng bằng sông Cửu Long (**13/13 tỉnh** theo địa giới trước 2025, giai đoạn **2015–2024**), triển khai đồng thời qua **2 tuyến phân tích song hành cùng thuộc phạm vi chính**:
> - **Tuyến A (Toàn vùng 13/13 tỉnh ĐBSCL):** Đông Xuân (`n = 127`) và cụm Hè Thu–Thu Đông (`n = 130`), tổng `257` quan sát cấp tỉnh–vụ–năm (nguồn NSO nâng cấp 2019 chính thức + khí tượng trọng số diện tích GADM v4.1 + NOAA ONI).
> - **Tuyến B (Tách riêng 3 mùa vụ trong vùng ĐBSCL):** `An Giang`, `Kiên Giang`, `Cần Thơ` (`n = 90`, chiếm **40,5% tổng sản lượng lúa ĐBSCL**), kết hợp **7 bản ghi ngoại kiểm địa lý OOD** (`Tiền Giang`, `Vĩnh Long`, `Cà Mau`) thuộc vùng giữa và ven biển.
>
> **Mã nguồn tái lập 100%:** `scripts/run_eda_and_modeling.py` · `scripts/run_statistical_and_datamining_suite.py` · `notebooks/Mekong_Rice_Yield_Full_Analysis.ipynb`  
> **Bảng kết quả:** `results/metrics/` · **10 Biểu đồ 300 DPI:** `results/figures/`

---

## 1. Đối tượng thụ hưởng & Bản đồ quy trình KDD (Buổi 01)

### 1.1. Kết quả đầu ra phục vụ cho đối tượng nào?
| Đối tượng thụ hưởng | Nhu cầu thực tế | Đầu ra cụ thể của đồ án đáp ứng | Giới hạn sử dụng (theo `DeTaiPTDL.pdf`) |
|---|---|---|---|
| **Sinh viên, giảng viên & nhà nghiên cứu PTDL / Nông học** | Hiểu rõ sự khác biệt liên hệ khí tượng – năng suất giữa 3 mùa vụ và so sánh hiệu năng đa hình thái mô hình trên cỡ mẫu bảng nhỏ. | Bộ dữ liệu sạch tái lập 100%, kiểm định GĐ1–GĐ4 OLS, bảng đối chiếu 20 mô hình hồi quy & 10 mô hình phân lớp, bằng chứng `regime shift` thích ứng El Niño 2023–2024. | Là phân tích **hồi cứu (reduced-form association)** dùng khí tượng cả vụ; không tuyên bố quan hệ nhân quả tuyệt đối. |
| **Cơ quan quản lý nông nghiệp & khuyến nông địa phương (Sở NN&PTNT, Chi cục Trồng trọt)** | Phân vùng rủi ro 13 tỉnh dựa trên dữ liệu khách quan, nhận diện tổ hợp thời tiết bất lợi và phân hạng nguy cơ vụ mùa. | Bản đồ gom cụm 13 tỉnh (`Ward Dendrogram`, `K-Means`, `DBSCAN`), luật kết hợp `IF–THEN` định lượng (Apriori) & cây quyết định CART, mô hình phân lớp 3 hạng năng suất (`AUC 0,95–0,97`). | Chỉ mang tính **tham khảo hỗ trợ ra quyết định**, không thay thế khuyến cáo nông học chính thức (do chưa có số liệu đo độ mặn thực địa `g/l`). |
| **Doanh nghiệp thu mua, kho vận & chuỗi cung ứng lúa gạo ĐBSCL** | Nắm quy luật phân bậc năng suất 3 vụ (`ĐX > HT > TĐ`), trọng tâm sản lượng vùng và biên độ rủi ro cực đoan ven biển. | Bảng thống kê mô tả theo tỉnh–vụ, bản đồ phần dư rủi ro hạn mặn 10 năm (`Bến Tre`, `Trà Vinh`, `Cà Mau`), mô hình ước lượng năng suất vượt Baseline `>50%` sai số trên Tuyến B. | Cần kết hợp thêm thông tin thị trường, giống lúa và cảnh báo thủy văn lưu vực Mê Kông khi dự báo sớm trước thu hoạch. |

### 1.2. Tiến độ toàn bộ quy trình KDD (7 bước Buổi 01)
1. **Xác định mục tiêu & phạm vi (`DeTaiPTDL.pdf`):** Hoàn tất.
2. **Thu thập đa nguồn & Handoff Gate (`scripts/collect_all_raw.ps1`, `verify_raw_handoff.mjs`):** Hoàn tất (`PASS`).
3. **Tiền xử lý & Làm sạch dữ liệu 9 bước Han & Kamber (`scripts/run_cleaning_pipeline.ps1`, `QUYET_DINH_LAM_SACH.md`):** Hoàn tất (`PASS`, `0` lỗi).
4. **Phân tích khám phá (EDA), Ngoại lệ $3\sigma$ & Kiểm định 4 giả định OLS GĐ1–GĐ4:** Hoàn tất.
5. **Thử nghiệm & So sánh Đa mô hình / Đa thuật toán trên cùng bộ dữ liệu** *(Hồi quy 20 cấu hình · Phân lớp 10 hình thái · Gom cụm 9 thuật toán · Luật kết hợp Apriori)*: Hoàn tất.
6. **Kiểm định độ nhạy (`±10/±15 ngày`, `Zonal vs 1 điểm`), Ngoại kiểm địa lý OOD, Biểu đồ 300 DPI, Notebook & Báo cáo tổng hợp:** Hoàn tất.
7. **Chuẩn bị Slide thuyết trình (15% điểm) & Tập dượt Vấn đáp (5% điểm):** Bước cuối cùng trước ngày báo cáo.

---

## 2. Tiền xử lý, Tóm tắt Mô tả & Kiểm định Ngoại lệ Quy tắc $3\sigma$ (Buổi 02)

- **Chuẩn hóa mã hóa biến phân loại (Buổi 02):** Tuyệt đối **không dùng `LabelEncoder`** cho biến định danh không có thứ tự như `province_id` hay `season` (tránh áp đặt thứ tự giả giữa các tỉnh); thay bằng **One-Hot Encoding** và **Fixed-Effects Centering** fit chỉ trên tập `train`.
- **Kiểm định ngoại lệ theo quy tắc $3\sigma$ ($|z| > 3$, `results/metrics/eda_3sigma_outliers_audit.csv`):**
  - **Tuyến B (`n = 90`, 3 tỉnh thượng nguồn):** **`0` điểm** vượt ngưỡng $3\sigma$ — xác nhận năng suất vùng đầu nguồn ổn định, phân bậc rõ **Đông Xuân (trung vị `7,329`) > Hè Thu (`5,689`) > Thu Đông (`5,505` tấn/ha)** (Hình `01`).
  - **Tuyến A Đông Xuân 13 tỉnh (`n = 127`):** Phát hiện chính xác **`3` điểm** vượt $3\sigma$, **100% đều thuộc vùng ven biển nhạy mặn**:
    - **Bến Tre 2016:** `0,05 tấn/ha` (**$z = -5{,}494$**) — hạn mặn lịch sử 2015–2016.
    - **Bến Tre 2020:** `0,04 tấn/ha` (**$z = -5{,}502$**) — hạn mặn lịch sử 2019–2020.
    - **Cà Mau 2017:** `3,00 tấn/ha` (**$z = -3{,}034$**).
  - **Tuyến A Hè Thu–Thu Đông 13 tỉnh (`n = 130`):** Phát hiện **`1` điểm** vượt $3\sigma$: **Bến Tre 2020** (`3,47 tấn/ha`, **$z = -3{,}423$**).
  - **Quyết định nghiệp vụ:** Không xóa mù quáng ngoại lệ thật của thiên tai; gắn cờ `domain_outlier_flag` để đánh giá song song **Dual-Regime (`127` vs `125`)** và ưu tiên mô hình vững **Huber Loss**.

---

## 3. Kiểm định Thống kê Hồi quy (GĐ1–GĐ4), Chọn biến & Khắc phục Đa cộng tuyến (Buổi 03 & 04)

### 3.1. Giải quyết Đa cộng tuyến (GĐ3 — Slide 51 Buổi 04) & Tương quan phần dư (Hình `02`)
- **Chẩn đoán:** 12 cặp biến khí tượng thô có $|r| \ge 0{,}79$ (`Tmax ↔ Ngày>35°C`: $r=0{,}962$; `Mưa ↔ Ngày khô`: $r=-0{,}924$); **VIF cực đại = `53,47`** (`> 10`, vi phạm nặng GĐ3).
- **Áp dụng trọn bộ 3 cách khắc phục đa cộng tuyến (Slide 51 Buổi 04):**
  1. *Loại biến tương quan cao* → giữ tập trực giao 5 đặc trưng vật lý (`vpd_mean_kpa`, `precip_total_mm`, `ws2m_mean_ms`, `pre_season_rain_90d_mm`, `oni_pre_season`), giảm **VIF max từ `53,47` → `3,55` (thô) và `2,72` (sau khử cố định Tỉnh × Vụ)**.
  2. *Tạo biến tổng hợp mới từ biến cũ* → dùng **`VPD` (áp suất hơi bão hòa thiếu hụt)** tổng hợp vật lý giữa nhiệt độ `T` và độ ẩm tương đối `RH`.
  3. *Dùng hồi quy co hệ số **Ridge (L2)** và **Lasso (L1)*** (bảng hệ số chi tiết tại `results/metrics/regularization_ols_ridge_lasso_huber_coefs.csv`): `Lasso (α=0,03)` co 4 biến tín hiệu yếu về `0,0000`, giữ lại 2 nhân tố mạnh nhất trên toàn cục 3 vụ là xu hướng năm `year_z (+0,1326)` và tốc độ gió `ws2m_mean_ms (-0,0190)`; trong khi `Ridge (α=25)` và `Huber (α=10)` giữ lại toàn bộ cấu trúc đa biến nhưng kiểm soát phương sai hệ số.
- **Phát hiện KDD — Nghịch lý Simpson (Simpson's Paradox) khi trộn mùa vụ (`results/metrics/eda_within_correlations.csv`, Hình `02`):**
  - Nếu phân tích **gộp 3 vụ không khử cố định**, dữ liệu gây ảo giác ngược đời: `Tổng lượng mưa` ($r_{\text{thô}} = -0{,}738$), `Mưa lớn >20mm` ($-0{,}580$) tương quan **âm**, còn `Ngày khô <1mm` ($+0{,}881$), `VPD` ($+0{,}490$), `Ngày >35°C` ($+0{,}475$) tương quan **dương** — vì vụ Đông Xuân năng suất cao rơi vào mùa khô.
  - **Sau khi khử hiệu ứng cố định `Tỉnh × Vụ`, toàn bộ `8/8` biến khí tượng ĐẢO NGƯỢC DẤU HOÀN TOÀN:** `Tổng mưa` đảo **$-0{,}738 \to +0{,}369$** ($p = 0{,}0003$), `Ngày mưa lớn >20mm` đảo **$-0{,}580 \to +0{,}381$** ($p = 0{,}0002$), `Ngày khô` đảo $+0{,}881 \to -0{,}093$, `VPD` đảo $+0{,}490 \to -0{,}160$, `Độ ẩm RH` đảo $-0{,}626 \to +0{,}159$.
- **Khác biệt nút thắt khí tượng giữa 3 vụ (sau khử cố định `Tỉnh × Vụ`, Hình `02B`):**
  - *Đông Xuân:* Nhạy rõ với **mưa 90 ngày tiền vụ** ($r = +0{,}41$) và **ENSO ONI** ($r = -0{,}20$).
  - *Hè Thu:* Nhạy với **stress khô hạn & nắng nóng**: tổng mưa ($r = +0{,}54$), độ ẩm RH ($r = +0{,}46$), số ngày khô ($r = -0{,}51$), VPD ($r = -0{,}42$), ngày >35°C ($r = -0{,}36$).
  - *Thu Đông:* Nhạy mạnh nhất với **tốc độ gió 2m** ($r = -0{,}61$, rủi ro gió bão đổ ngã), VPD ($r = -0{,}56$), tổng mưa ($r = +0{,}68$ — lưu ý liên hệ hồi cứu đồng biến với giai đoạn La Niña 2021–2024); đồng thời có tốc độ tăng cấu trúc nhanh nhất (`+0,078 tấn/ha/năm`).

### 3.2. Kiểm định 4 Giả định Hồi quy Tuyến tính (GĐ1–GĐ4) & Chỉ số `Adj. R² / AIC / BIC` (Hình `07`)
*(Chi tiết hệ số $\hat{\beta}$, `SE cổ điển`, `SE HC3`, `t-stat`, `p-value` từng biến tại `results/metrics/ols_full_coefficients_table.csv` và `ols_assumptions_diagnostics_gd1_to_gd4.csv`.)*

| Mô hình OLS kiểm định | $n$ | $R^2$ | Adj. $R^2$ | **GĐ1: F-test ($p$)** | **GĐ2: Shapiro ($p$)** | **GĐ3: Max VIF** | **GĐ4: BP ($p$)** | **GĐ4: White ($p$)** | **AIC** | **BIC** | Nhận định thống kê |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `TrackB_Direct_OneHot` *(Tỉnh+Vụ+5KT+Năm)* | 90 | `0,9137` | `0,9027` | `<0,0001` (Đạt) | `0,1412` (Đạt) | `11,28` (Vượt 10) | `0,0806` (Đạt) | `0,1281` (Đạt) | `29,04` | `56,53` | Đạt GĐ1, GĐ2, GĐ4 nhưng biến giả vụ dính đa cộng tuyến với khí tượng (`VIF=11,28`). |
| `TrackB_FE_Demeaned` *(Khử Tỉnh×Vụ + 5KT + Năm)* | 90 | `0,4920` | `0,4553` | `<0,0001` (Đạt) | `0,0001` (Đuôi nhẹ) | **`2,90` (Đạt)** | `0,3695` (Đạt) | `0,1915` (Đạt) | **`-6,08`** | **`11,42`** | Triệt tiêu đa cộng tuyến (`VIF=2,90`), `year_z` ($t=6{,}05, p<0{,}001$) và `vpd` ($t=2{,}29, p=0{,}025$) có ý nghĩa thống kê. |
| `TrackA_DX_Full` *(13 tỉnh ĐX — đủ 2 năm mất trắng)* | 127 | `0,2280` | `0,1894` | `0,00002` (Đạt) | **`<1e-10` (Vi phạm nặng)** | `6,35` (Đạt) | `0,2276` (Đạt) | `0,4628` (Đạt) | `273,28` | `293,19` | **Bằng chứng GĐ2:** 2 năm mất trắng Bến Tre kéo lệch nặng phần dư → **OLS mất hiệu lực, bắt buộc dùng Huber Loss**. |
| `TrackA_DX_ExSalinity` *(13 tỉnh ĐX — bỏ 2 điểm mất trắng)* | 125 | `0,2724` | `0,2354` | `<0,00001` (Đạt) | `<0,0001` (Đuôi mặn TV/CM) | `6,29` (Đạt) | `0,8626` (Đạt) | `0,9281` (Đạt) | **`165,46`** | **`185,26`** | Loại 2 năm mất trắng giúp **AIC giảm mạnh `107,8` điểm**, `ws2m` ($p=0{,}034$) và `year_z` ($p<0{,}001$) có ý nghĩa vững cả dưới `HC3`. |
| `TrackA_HTTD` *(13 tỉnh HT–TĐ)* | 130 | `0,4762` | `0,4507` | `<0,0001` (Đạt) | `0,0004` (Vi phạm) | `3,59` (Đạt) | `0,1407` (Đạt) | **`0,0334` (Vi phạm)** | `-54,81` | `-34,74` | **Bằng chứng GĐ4:** White test bác bỏ phương sai đồng nhất ($p=0{,}033$) → phải báo cáo `SE HC3` và dùng hồi quy regularized/vững. |

### 3.3. So sánh các phương pháp Chọn biến (Buổi 04 Slides 39–46 — trên Tuyến B `dev 2015–2022`)
| Phương pháp chọn biến | Số biến | Adj. $R^2$ | AIC | BIC | Max VIF | OLS CV MAE | Ridge CV MAE | Ridge Test MAE | Nhận xét |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `Full_Candidate_10Weather_Plus_Year` | 11 | `0,4995` | `-10,13` | `17,20` | **`353,84`** | `0,2520` | `0,1866` | `0,1880` | Đa cộng tuyến cực nặng làm OLS overfit. |
| `Forward_Selection_AIC` | 6 | `0,5177` | `-17,02` | `-1,08` | `13,61` | `0,2347` | `0,1868` | `0,1612` | Tối ưu AIC nhưng vẫn còn `VIF > 10`. |
| `Backward_Elimination (p ≤ 0,05)` | 3 | `0,4869` | `-15,33` | **`-6,22`** | `18,34` | **`0,1623`** | `0,2065` | **`0,1320`** | Gọn nhất về BIC nhưng chọn cặp biến có `VIF > 10`. |
| `Stepwise_Bidirectional_AIC` | 4 | `0,5088` | **`-17,53`** | `-6,14` | `6,52` | `0,1692` | `0,1935` | `0,1460` | Cân bằng tốt AIC/BIC và `VIF < 10`. |
| `Domain_Orthogonal_5_Plus_Year` | 6 | `0,3744` | `1,71` | `17,64` | **`3,43`** | `0,1993` | `0,1881`* | **`0,1369`**\* | Trực giao vật lý sạch nhất (`VIF = 3,43`), kết hợp tuning `Ridge/Huber` đạt ổn định nhất toàn hệ. |

*(\*Khi tối ưu siêu tham số `alpha` trên Expanding-CV trong `run_eda_and_modeling.py`, `Huber_Anomaly_Ortho5_Trend` đạt CV = `0,1771` và `Ridge_Anomaly_Ortho5_Trend` đạt Test = `0,1369`.)*

---

## 4. So sánh Đa hình thái Mô hình Hồi quy trên cùng bộ dữ liệu (Buổi 04 + 08–10, Hình `03`)

Thực hiện đúng nguyên tắc khoa học của `DeTaiPTDL.pdf`: **chọn cấu hình & mô hình trên Expanding-Window CV (`2019–2022`), khóa kín hoàn toàn Test (`2023–2024`)**. Thay đổi hình thái mô hình trên **cùng tập dữ liệu & cùng hệ độ đo** cho thấy sự phân hóa hiệu năng rất rõ rệt:

### 4.1. Tuyến B — 3 mùa vụ tách riêng (`n = 90`, 20 mô hình thuộc 9 hình thái khác nhau)

| Hình thái mô hình | Mô hình cụ thể | Train MAE (15–22) | **Expanding-CV MAE (19–22)** | Val MAE (21–22) | **Test MAE (23–24)** | Test RMSE | Test $R^2$ | $\Delta$ Test MAE vs Baseline |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Baseline** | `Baseline_Median` (Trung vị Tỉnh–Vụ) | 0,2109 | 0,2624 | 0,3301 | 0,3002 | 0,3400 | 0,8424 | 0,0000 |
| **Cấu trúc** | `Structural_FE_Plus_Trend` (Không khí tượng) | 0,1718 | 0,1988 | 0,1807 | **0,1335** | **0,1675** | **0,9615** | -0,1667 |
| **OLS thuần** | `OLS_Anomaly_Core4` (Không trend, không reg.) | 0,1734 | 0,2303 | 0,3391 | 0,4220 | 0,4666 | 0,7016 | +0,1217 |
| **OLS thuần** | `OLS_Anomaly_Ortho5_Trend` | 0,1682 | 0,1993 | 0,2134 | 0,1565 | 0,2083 | 0,9405 | -0,1437 |
| **Ridge (L2)** | `Ridge_Anomaly_Ortho5_Trend` | 0,1654 | 0,1881 | 0,2306 | **0,1369** | 0,1842 | 0,9538 | **-0,1633** |
| **Lasso (L1)** | `Lasso_Anomaly_Ortho5_Trend` | 0,1662 | 0,1867 | 0,2210 | **0,1374** | 0,1841 | 0,9538 | **-0,1628** |
| **Huber (Robust)** | **`Huber_Anomaly_Ortho5_Trend`** *(Nhất CV)* | 0,1606 | **0,1771** | 0,2397 | **0,1447** | 0,1934 | 0,9490 | **-0,1555** |
| **Cây QĐ (CART)** | `DecisionTree_Anomaly_Trend` | 0,1585 | 0,1787 | 0,1693 | 0,1931 | 0,2264 | 0,9298 | -0,1071 |
| **Rừng ngẫu nhiên** | `Shallow_RF_Direct` (Không khử cố định) | 0,1698 | 0,2755 | 0,3754 | 0,3247 | 0,3735 | 0,8083 | +0,0244 |
| **Rừng ngẫu nhiên** | `Shallow_RF_Anomaly_Trend` | 0,1443 | 0,2285 | 0,3269 | 0,2180 | 0,2586 | 0,9085 | -0,0822 |
| **Gradient Boosting** | `GBR_Anomaly_Trend` | 0,1453 | 0,2226 | 0,3066 | 0,2186 | 0,2544 | 0,9114 | -0,0816 |
| **SVM (Linear)** | `SVR_Linear_Anomaly_Trend` | 0,1623 | **0,1797** | 0,2408 | 0,1556 | 0,2019 | 0,9441 | -0,1446 |
| **SVM (RBF)** | `SVR_RBF_Anomaly_Trend` *(Overfit nặng)* | **0,0780** | 0,1956 | 0,1872 | **0,3372** | 0,3804 | 0,8010 | +0,0370 |
| **Mạng Nơ-ron (ANN)** | `MLP_ReLU_Anomaly_Trend` | 0,1521 | 0,2143 | 0,2636 | 0,1728 | 0,2241 | 0,9312 | -0,1274 |
| **Mạng Nơ-ron (ANN)** | `MLP_Tanh_Anomaly_Trend` | 0,1624 | 0,2061 | 0,2333 | 0,1237 | 0,1645 | 0,9629 | -0,1765 |

- **Kết luận chọn mô hình hồi quy tối ưu trên Tuyến B:**
  1. **Chọn trên Expanding-CV (quy tắc chống nhìn trộm Test):** **`Huber_Anomaly_Ortho5_Trend` (`CV = 0,1771`)** và **`Ridge / Lasso + Trend` (`CV = 0,1867–0,1881`, `Test = 0,1369–0,1374`)** là nhóm tốt nhất — giảm **`32,5%` sai số trên CV** và **`51,8–54,4%` trên Test** so với Baseline (`0,3002`), đồng thời giữ được tính diễn giải cao từng hệ số vật lý.
  2. **So sánh khi đổi hình thái mô hình:**
     - *Họ Cây & Boosting (`DT`, `RF`, `GBR`):* Phân vùng dạng bậc thang nên không ngoại suy xu hướng tăng tuyến tính `year` ở 2023–2024 tốt bằng nhóm tuyến tính (`Test MAE = 0,193–0,219` vs `0,137–0,145`).
     - *Họ SVM (so sánh kernel, Slide 32 Buổi 10):* `SVR_Linear` (`CV = 0,1797`, `Test = 0,1556`) ổn định vượt trội `SVR_RBF` (`Train = 0,0780` nhưng `Test = 0,3372` — bằng chứng rõ nét của overfitting khi dùng kernel phi tuyến trên cỡ mẫu nhỏ).
     - *Họ Mạng Nơ-ron (so sánh hàm kích hoạt, Slide 15 Buổi 10):* Trên Expanding-CV, cả `MLP_ReLU` (`0,2143`) và `MLP_Tanh` (`0,2061`) đều kém hơn `Huber`/`Lasso`/`Ridge`/`SVR_Linear` và khó giải thích (khớp Slide 8 Buổi 10); trên Test, `MLP_Tanh` vượt `MLP_ReLU` (`0,1237` vs `0,1728`) do hàm `tanh` phạt nặng L2 (`alpha=50`) gần như suy biến về ánh xạ tuyến tính mượt.
  3. **Sai số Test theo từng vụ (`Ridge+Trend` / `Huber+Trend` vs `Baseline`):** Đông Xuân `0,1457` vs `0,3607` (`-59,6%`), Hè Thu `0,1390` (`Huber+Trend`) vs `0,2058` (`-32,5%`), Thu Đông `0,0787` (`Ridge+Trend`) vs `0,3342` (`-76,5%`).
  4. **Giải thích Regime Shift El Niño 2023–2024 (Hình `05A`):** Trên Expanding-CV (2019–2022), khí tượng giúp cải thiện rõ so với `Structural_FE_Plus_Trend` (`0,1771` vs `0,1988`), nhưng sang El Niño `2023–2024 (ONI = +1,90)`, nông dân ĐBSCL chủ động xuống giống sớm né mặn nên năng suất giữ vững mức cao (dịch chuyển chế độ thích ứng khí hậu), giải thích vì sao `Structural_FE_Plus_Trend` (`0,1335`) ngang ngửa `Ridge+Trend` (`0,1369`) trên Test.

### 4.2. Tuyến A — Toàn vùng 13/13 tỉnh ĐBSCL (Dual-Regime & Residual Attribution)
- **Đông Xuân 13 tỉnh (`Full 127` vs `Ex-Salinity 125`, Hình `03C`):**
  - **`Huber_Anomaly_Weather`** thắng toàn diện mọi hình thái mô hình trên Expanding-CV ở cả hai chế độ: **`0,4482`** (đủ 127, giảm `11,6%` so với Baseline `0,5070`; trong khi `OLS` vọt lên `0,7180`, `Lasso` `0,6239`, `MLP` `0,6108`, `Ridge` `0,5856`, `DT` `0,5572`, `RF` `0,5280`, `GBR` `0,5050`, `SVR-RBF` `0,4872`) và **`0,3519`** (`Huber+Trend`, chế độ 125, giảm `15,4%` so với Baseline `0,4158`).
  - **Chẩn đoán phần dư LOYO 10 năm & Nghịch lý mưa Bến Tre 2015 vs 2020 (Hình `05`):** 5/5 sai số lớn nhất toàn vùng tập trung ở vùng ven biển hạn mặn: **Bến Tre 2020 (`-5,05`)**, **Bến Tre 2016 (`-4,71`)**, **Cà Mau 2017 (`-3,12`)**, **Trà Vinh 2020 (`-2,98`)**, **Trà Vinh 2016 (`-2,12` tấn/ha)**. Đặc biệt tại cùng tỉnh **Bến Tre**, năm **2020** có `ONI (+0,72)` và `VPD (0,801)` gần y hệt năm **2015** (`ONI +0,70`, `VPD 0,813`) và **mưa 90 ngày tiền vụ nhiều hơn tới `+44%`** (`717,4` vs `497,9 mm`), nhưng năng suất vẫn sập từ **`5,09` xuống `0,04 tấn/ha`** — chứng minh định lượng hạn mặn là cú sốc thủy văn thượng nguồn lưu vực Mê Kông (OVB), không thể dự báo chỉ bằng mưa tại chỗ.
  - **Dịch chuyển chế độ thích ứng (El Niño 2016 vs El Niño 2024):** So sánh trực tiếp 2 đợt El Niño mạnh (`2016: ONI +2,45` vs `2024: ONI +1,90`), **12/12 tỉnh có số liệu 2016 đều tăng mạnh năng suất ĐX 2024** (`Bến Tre +5,04`, `Trà Vinh +2,66`, `Kiên Giang +1,60`, `Bạc Liêu +0,99` tấn/ha) nhờ lịch xuống giống sớm né mặn và công trình thủy lợi.
- **Cụm Hè Thu–Thu Đông 13 tỉnh (`n = 130`):** Trên Expanding-CV, `Ridge_Anomaly_Weather` (`0,1883`) và `Huber+Trend` (`0,1904`) dẫn đầu toàn bộ 13 mô hình (vượt Baseline `0,2450`, `GBR 0,1927`, `MLP 0,2020`, `DT 0,2027`, `RF 0,2061`, `SVR-RBF 0,2432`).

---

## 5. So sánh Đa hình thái Mô hình Phân lớp (Buổi 08, 09, 10 — Hình `08`)

Mở rộng ứng dụng từ chính bộ dữ liệu sạch Tuyến A toàn vùng 13 tỉnh (`n = 257`, `dev 2015–2022 = 205`, `Test 2023–2024 = 52`) để phục vụ bài toán **phân hạng mức năng suất & cảnh báo rủi ro vụ mùa**. Mọi ngưỡng phân lớp và bộ chuẩn hóa chỉ fit trên tập `train/dev` để đảm bảo **0% leakage**.

### 5.1. Bài toán C1 — Phân lớp Đa lớp 3 hạng năng suất (`Thấp < 5,58` · `Trung bình 5,58–6,49` · `Cao ≥ 6,49 tấn/ha`)
So sánh **10 hình thái mô hình** trên **2 chế độ đặc trưng** (*Chế độ 1: Thuần Khí tượng + Tiểu vùng sinh thái* vs *Chế độ 2: Đầy đủ Khí tượng + Tỉnh + Vụ + Năm*, chi tiết tại `results/metrics/classification_multimodel_comparison.csv`):

| Hình thái mô hình | **Chế độ 1 (Thuần KT + Tiểu vùng)** Exp-CV F1 | **Chế độ 1** Test F1 | **Chế độ 1** Test AUC | **Chế độ 2 (Đầy đủ KT+Tỉnh+Vụ)** 5-Fold F1 | **Chế độ 2** Exp-CV F1 | **Chế độ 2** Test Acc | **Chế độ 2** Test F1 | **Chế độ 2** Test AUC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `Dummy_Baseline` | 0,1374 | 0,1164 | 0,5000 | 0,1679 | 0,1374 | 0,2115 | 0,1164 | 0,5000 |
| `Logistic_Multinomial` | 0,7204 | 0,7132 | **0,9219** | 0,7553 | 0,7759 | 0,7885 | 0,7831 | 0,9614 |
| `Logistic_OvR` | 0,7250 | 0,7132 | 0,9038 | 0,7388 | 0,7561 | 0,8462 | 0,8360 | 0,9577 |
| `DecisionTree_CART` | 0,4725 | 0,5790 | 0,7295 | 0,6068 | 0,6122 | 0,6154 | 0,5987 | 0,7135 |
| `RandomForest` | 0,6585 | 0,5320 | 0,8832 | 0,6551 | 0,6863 | 0,7115 | 0,6710 | 0,9326 |
| `GradientBoosting` | 0,7048 | 0,5659 | 0,8475 | 0,7191 | 0,7623 | 0,6923 | 0,6550 | 0,9330 |
| `NaiveBayes_Gaussian` | **0,7356** | 0,6575 | 0,9155 | 0,7088 | 0,7186 | 0,6923 | 0,6349 | 0,9644 |
| `SVM_Linear` | 0,7249 | **0,7341** | 0,9155 | **0,7612** | 0,7874 | 0,8077 | 0,7966 | **0,9669** |
| **`SVM_RBF`** | 0,7176 | 0,5981 | 0,8617 | 0,7502 | **0,8012** | **0,8654** | **0,8717** | 0,9487 |
| `MLP_ReLU` | 0,6866 | 0,4600 | 0,8879 | 0,7559 | 0,7540 | 0,5769 | 0,4600 | 0,9068 |
| `MLP_Tanh` | 0,6876 | 0,5321 | 0,8785 | 0,7551 | **0,8258** | 0,7308 | 0,6929 | 0,9313 |

- **Kết luận phân lớp C1:**
  - Khi **chỉ dùng khí tượng + tiểu vùng**, **`SVM_Linear` (`Test Acc = 76,9%`, `Macro-F1 = 0,734`, `AUC = 0,916`)** và **`Logistic` (`Test F1 = 0,713`, `AUC = 0,922`)** vượt trội hẳn Cây đơn (`0,579`), Rừng ngẫu nhiên (`0,532`) và MLP (`0,460–0,532`).
  - Khi bổ sung **ngữ cảnh Tỉnh + Vụ + Năm**, **`SVM_RBF` (`Exp-CV F1 = 0,801`, `Test Acc = 86,5%`, `Macro-F1 = 0,872`, `AUC = 0,949`)**, **`Logistic_OvR` (`Test F1 = 0,836`, `AUC = 0,958`)** và **`SVM_Linear` (`AUC = 0,967`)** dẫn đầu ổn định. Đáng chú ý, thay đổi hàm kích hoạt của mạng nơ-ron từ `ReLU` sang `Tanh` (đúng ví dụ Slide 15 Buổi 10) đẩy Test Macro-F1 từ `0,460` lên `0,693`.

### 5.2. Bài toán C2 — Phân lớp Nhị phân Cảnh báo Rủi ro Sụt giảm & Minh họa "Accuracy Paradox" (Slide 20 Buổi 08–09)
- Nhãn dương `1`: Vụ có năng suất thấp hơn kỳ vọng xu hướng (`29,3%` dev; `38,5%` test — mất cân bằng nhẹ).
- **Minh họa trực tiếp Slide 20 Buổi 08–09:** Trên Test 2023–2024, `MLP_ReLU` và `MLP_Tanh` đạt `Accuracy = 61,5%` (ngang `Dummy_Baseline`), nhưng **`Precision = 0,0`, `Recall = 0,0`, `F1 = 0,0`** do đoán toàn bộ về lớp đa số! Trong khi **`SVM_Linear` (`class_weight='balanced'`)** đạt **`Recall = 0,60`, `F1 = 0,511`, `AUC = 0,588`** và **`Logistic_Binary`** đạt **`Recall = 0,50`, `F1 = 0,455`, `AUC = 0,569`** (và trên Stratified 5-Fold CV nội kỳ 2015–2022, `RandomForest` đạt `F1 = 0,578`, `AUC = 0,708`).
- **Luật IF–THEN tự động trích xuất từ Cây quyết định CART (`results/metrics/classification_decision_tree_rules.txt`):**
  > `IF oni_pre_season > 0,80 (El Niño mạnh) AND pre_season_rain_90d_mm ≤ -0,47 (thiếu mưa 90 ngày tiền vụ) THEN Rủi ro sụt giảm năng suất (Lớp 1); ELSE (mưa tiền vụ đủ) THEN Đạt/vượt kỳ vọng (Lớp 0).`

---

## 6. Gom cụm 13 tỉnh ĐBSCL — Kiểm chứng khách quan 3 tiểu vùng sinh thái (Buổi 11 & 12, Hình `09`)

Trên bộ hồ sơ chuẩn hóa 9 đặc trưng khí hậu–năng suất của **13 tỉnh ĐBSCL**, đối chiếu **9 thuật toán gom cụm** qua trọn bộ **3 nhóm đánh giá của Buổi 11 (Slide 32)**: *Internal* (`SSE`, `Silhouette`, `Calinski-Harabasz`, `Dunn`), *External* (`ARI`, `NMI`, `FMI`, `Jaccard` so với 3 tiểu vùng nông học) và *Relative* (`Pairwise Rand`, `Pairwise F-measure`).

| Thuật toán gom cụm | Số cụm | Điểm nhiễu | **SSE** (Min) | **Silhouette** (Max) | **Calinski-Harabasz** (Max) | **Dunn** (Max) | **ARI** vs Tiểu vùng | **NMI** vs Tiểu vùng |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`KMeans (K=3)`** | 3 | 0 | **30,32** | **0,3898** | **14,29** | 0,5099 | 0,1374 | 0,3838 |
| **`KMedoids PAM (K=3)`** | 3 | 0 | **30,32** | **0,3898** | **14,29** | 0,5099 | 0,1374 | 0,3838 |
| **`Agglomerative Ward (K=3)`** | 3 | 0 | **30,32** | **0,3898** | **14,29** | 0,5099 | 0,1374 | 0,3838 |
| **`Agglomerative Complete (K=3)`** | 3 | 0 | **30,32** | **0,3898** | **14,29** | 0,5099 | 0,1374 | 0,3838 |
| **`BisectingKMeans (K=3)`** | 3 | 0 | **30,32** | **0,3898** | **14,29** | 0,5099 | 0,1374 | 0,3838 |
| `Agglomerative Average (K=3)` | 3 | 0 | 40,50 | 0,3370 | 9,45 | **0,5528** | **0,4103** | **0,6556** |
| `Agglomerative Single (K=3)` | 3 | 0 | 49,17 | 0,3678 | 6,90 | 0,5528 | 0,1915 | 0,4126 |
| `DBSCAN (eps=2,8, min=2)` | 2 | **1 (Bến Tre)** | 49,17 | **0,4238** | 7,08 | 0,5528 | 0,1915 | 0,4126 |
| `MeanShift (Auto)` | 5 | 0 | 22,65 | 0,2495 | 8,33 | 0,5528 | 0,2783 | 0,5866 |

- **Phát hiện tri thức (KDD) cực kỳ giá trị từ Gom cụm:**
  1. **Độ đồng thuận tuyệt đối (`Relative Pairwise Rand Index = 1,000`):** Cả **5 thuật toán** (`K-Means`, `K-Medoids PAM`, `Agglomerative Ward`, `Complete`, `Bisecting K-Means`) đều hội tụ về **chính xác cùng 3 cụm tự nhiên**:
     - **Cụm 1 — Ven biển rủi ro hạn mặn cực đoan (3 tỉnh):** `Bến Tre`, `Cà Mau`, `Trà Vinh`.
     - **Cụm 2 — Thượng nguồn & Nội đồng Đông Bắc khô ấm (4 tỉnh):** `An Giang`, `Đồng Tháp`, `Long An`, `Tiền Giang` (`VPD 0,91–1,02`, gió yếu `2,11–2,43 m/s`).
     - **Cụm 3 — Giữa & Tây/Nam Sông Hậu ẩm gió, năng suất cao (6 tỉnh):** `Cần Thơ`, `Hậu Giang`, `Kiên Giang`, `Vĩnh Long`, `Sóc Trăng`, `Bạc Liêu`.
  2. **Khám phá dị biệt giữa địa lý hành chính và hành vi thực tế:** `Bạc Liêu` nằm ven biển nhưng nhờ hệ thống cống ngăn mặn vùng ngọt hóa Quản Lộ – Phụng Hiệp nên có năng suất ĐX rất cao (`7,46 tấn/ha`, min `6,77`) và được dữ liệu xếp vào Cụm 3 thay vì Cụm rủi ro mặn!
  3. **Phát hiện ngoại lệ bằng mật độ (`DBSCAN`):** `DBSCAN` tự động gắn nhãn duy nhất **`Bến Tre` là điểm nhiễu `-1`**, khớp 100% với kiểm định $3\sigma$ (Buổi 02) và chẩn đoán LOYO (Mục 4.2)!

---

## 7. Khai phá Luật Kết Hợp Định Lượng — Apriori (Buổi 06 & 07, Hình `10`)

Rời rạc hóa các biến liên tục bằng `pd.cut` / `pd.qcut` (Buổi 02 + Quantitative AR Slide 10 Buổi 06–07) và chạy thuật toán **Apriori** (`min_support = 0,08`, `min_confidence = 0,55`) trên Đông Xuân 13 tỉnh (`n = 127`, đầy đủ tại `results/metrics/association_rules_agroclimatic.csv`):

| Luật kết hợp (`IF Antecedent → Consequent`) | Support | Confidence | **Lift** | Leverage | Conviction | Ý nghĩa nông học |
|---|---:|---:|---:|---:|---:|---|
| `IF MưaTiềnVụ=Cao AND Vùng=ThượngNguồn → NăngSuấtĐX=Cao` | 0,0945 | **1,0000** | **3,0238** | 0,0632 | $\infty$ | Đầu nguồn đủ trữ lượng nước đầu mùa khô đảm bảo 100% năng suất nhóm Cao. |
| `IF ENSO=LaNiña AND Vùng=ThượngNguồn → NăngSuấtĐX=Cao` | 0,1024 | 0,8125 | **2,4568** | 0,0607 | 3,57 | Năm La Niña lưu lượng nước Mê Kông dồi dào đẩy mạnh xác suất được mùa ĐX. |
| `IF Gió2m=Mạnh AND MưaTiềnVụ=TB → NăngSuấtĐX=Thấp` | 0,0945 | 0,7059 | **2,0848** | 0,0492 | 2,25 | Khu vực gió biển mạnh kèm mưa tiền vụ không cao làm tăng gấp đôi nguy cơ năng suất thấp. |
| `IF MưaTiềnVụ=TB AND Vùng=VenBiển → NăngSuấtĐX=Thấp` | 0,0866 | 0,6875 | **2,0305** | 0,0440 | 2,12 | Vùng ven biển nếu thiếu lượng mưa rửa mặn cao trước vụ dễ rơi vào nhóm năng suất thấp. |
| `IF Vùng=VenBiển → NăngSuấtĐX=Thấp` | 0,1811 | 0,6216 | **1,8360** | 0,0825 | 1,75 | Rủi ro cấu trúc mặn – thủy văn đặc thù của vùng ven biển ĐBSCL. |

> **Lưu ý kiểm soát diễn giải (Tránh bẫy trộn mùa):** Nhóm ưu tiên báo cáo các luật Apriori trên **Tuyến A nội trong riêng vụ Đông Xuân (`n = 127`)** vì đã cố định 1 mùa vụ nên phản ánh quy luật khí tượng–vùng sinh thái thực. Ngược lại, các luật gộp 3 vụ ở Tuyến B (như `MưaVụ=Ít → NăngSuất3Vụ=Cao`) chịu ảnh hưởng chu kỳ mùa khô = vụ Đông Xuân nên không dùng để suy diễn nhân quả đơn biến.

---

## 8. Kiểm định Độ nhạy (`±10/±15 ngày`, `Zonal vs 1 điểm`) & Ngoại kiểm Địa lý OOD (Hình `04` & `06`)

1. **Độ nhạy Lịch thời vụ & Không gian (Hình `04`):** Trên cả 6 kịch bản (`zonal_shift_0`, `single_point_shift_0`, `±10 ngày`, `±15 ngày`), `Ridge_Anomaly_Ortho5_Trend` giữ Test MAE cực kỳ ổn định từ `0,1369` đến `0,1683` (chênh giữa Zonal và 1 điểm chỉ `0,0016` tấn/ha; dịch `±10 ngày` chỉ `0,1390–0,1492`), khẳng định kết quả **không mong manh trước sai lệch khung lịch thời vụ**.
2. **Ngoại kiểm Địa lý OOD trên 7 dòng chưa từng huấn luyện (`Tiền Giang`, `Vĩnh Long`, `Cà Mau`, Hình `06A`):** Mang mô hình Ridge học trên 3 tỉnh thượng nguồn dự báo sang 3 tỉnh vùng giữa & ven biển giúp giảm MAE **`23,6%`** (`0,1440` vs Baseline vụ `0,1884` tấn/ha). Ở chiều ngược lại, kiểm định chuyển giao Đông Xuân 2023–2024 sang 10 tỉnh ngoài lõi (Hình `06B`) xác nhận giới hạn ngoại suy khi xảy ra dịch chuyển thích ứng El Niño 2024.

---

## 9. Danh mục sản phẩm bàn giao đầy đủ

- **Mã nguồn & Notebook tái lập 100%:**
  - Pipeline làm sạch: `scripts/run_cleaning_pipeline.ps1` (`clean_rice_data.mjs`, `clean_weather_zonal.mjs`, `clean_season_calendar.mjs`, `build_clean_datasets.mjs`, `verify_cleaned_datasets.mjs`)
  - Pipeline Hồi quy, Độ nhạy & OOD: `scripts/run_eda_and_modeling.py`
  - Pipeline Thống kê (Buổi 02–04), Phân lớp (Buổi 08–10), Gom cụm (Buổi 11–12), Luật kết hợp (Buổi 06–07): `scripts/run_statistical_and_datamining_suite.py`
  - Jupyter Notebook trình diễn: `notebooks/Mekong_Rice_Yield_Full_Analysis.ipynb`
- **10 Biểu đồ 300 DPI (`results/figures/`):**
  - `01_eda_yield_by_season_and_province.png` · `02_eda_collinearity_and_within_corr.png` · `03_model_comparison_tier1_and_tier2.png`
  - `04_sensitivity_calendar_and_spatial.png` · `05_residual_attribution_salinity_13provinces.png` · `06_spatial_generalization_ood_check.png`
  - `07_ols_assumptions_diagnostics_gd1_gd4.png` · `08_classification_multimodel_roc_and_cm.png` · `09_clustering_13provinces_dendrogram_and_pca.png` · `10_association_rules_lift_confidence.png`
- **Bảng kết quả CSV & JSON (`results/metrics/`):**
  - Buổi 02–04: `eda_descriptive_summary.csv`, `eda_3sigma_outliers_audit.csv`, `eda_vif_comparison.csv`, `eda_within_correlations.csv`, `ols_full_coefficients_table.csv`, `ols_assumptions_diagnostics_gd1_to_gd4.csv`, `feature_selection_stepwise_comparison.csv`, `regularization_ols_ridge_lasso_huber_coefs.csv`
  - Hồi quy, Độ nhạy & OOD: `track_b_3seasons_model_comparison.csv`, `track_b_3seasons_test_predictions.csv`, `track_b_test_error_breakdown.csv`, `track_a_delta13_model_comparison.csv`, `track_a_dx_test_predictions.csv`, `track_a_dx_loyo_residuals_attribution.csv`, `track_b_sensitivity_model_results.csv`, `external_ood_7rows_predictions.csv`, `spatial_heterogeneity_transfer_test.csv`
  - Phân lớp, Gom cụm & Luật kết hợp: `classification_multimodel_comparison.csv`, `classification_decision_tree_rules.txt`, `clustering_13provinces_validation.csv`, `clustering_13provinces_assignments.csv`, `clustering_relative_validation.csv`, `association_rules_agroclimatic.csv`
  - Tổng hợp JSON: `master_analysis_summary.json`, `statistical_and_datamining_summary.json`
