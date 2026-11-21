# Kịch bản & Dàn ý Chi tiết 18 Slide Thuyết trình Đồ án Cuối kỳ

> **Học phần:** Phân tích dữ liệu — Khoa CNTT, Trường Đại học Sài Gòn (**CBGD: Phan Thành Huấn**)  
> **Cơ cấu điểm liên quan:** Trình bày **15%** + Nội dung **25%** + Vấn đáp **5%**  
> **Thời lượng chuẩn:** **13–15 phút** (~45 giây/slide) · **Bản trình chiếu 16:9 sẵn sàng mở trên trình duyệt:** `slide/SLIDE_BAO_CAO_DO_AN_SGU.html`  
> **Phân công thuyết trình (khớp mục 6 `DeTaiPTDL.pdf`):**
> - **Lê Thị Ngọc Giàu (`3123410088`):** Slide **01 → 05** và **11** (Bối cảnh, Đối tượng thụ hưởng, Phạm vi 13 tỉnh, Thu thập, Làm sạch 9 bước, $3\sigma$, Độ nhạy & OOD) — ~5 phút.
> - **Trần Ngọc An (`3123410004`):** Slide **06 → 10** và **12 → 18** (VIF, Kiểm định 4 giả định OLS GĐ1–GĐ4, Chọn biến, So sánh 20 mô hình Hồi quy, 10 mô hình Phân lớp, 9 thuật toán Gom cụm, Luật kết hợp Apriori, Tổng kết) — ~9 phút.

---

## SLIDE 01 — Trang bìa *(Giàu — 20s)*
- **Nội dung trên slide:**
  - Tiêu đề: **PHÂN TÍCH MỐI LIÊN HỆ GIỮA KHÍ TƯỢNG VÀ NĂNG SUẤT LÚA Ở ĐỒNG BẰNG SÔNG CỬU LONG THEO BA MÙA VỤ (2015–2024)**
  - Thông tin: Trường ĐH Sài Gòn – Khoa CNTT · Học phần Phân tích Dữ liệu · CBGD: **Phan Thành Huấn**
  - Nhóm thực hiện: **Lê Thị Ngọc Giàu (3123410088)** & **Trần Ngọc An (3123410004)**
- **Lời nói gợi ý:** Chào thầy và lớp, nhóm em trình bày đồ án phân tích mối liên hệ giữa khí tượng và năng suất lúa toàn vùng 13 tỉnh ĐBSCL giai đoạn 2015–2024 theo 3 mùa vụ, triển khai trọn quy trình KDD từ thu thập, làm sạch đến so sánh đa hình thái mô hình.

---

## SLIDE 02 — Bối cảnh, 4 Câu hỏi Nghiên cứu & Đối tượng thụ hưởng *(Giàu — 50s)*
- **Nội dung trên slide:**
  - **4 Câu hỏi nghiên cứu (`DeTaiPTDL.pdf`):** (1) Năng suất & sản lượng khác nhau thế nào giữa 3 vụ, 13 tỉnh và qua các năm? (2) Nhiệt độ, mưa, độ ẩm liên hệ thế nào với năng suất? (3) Mức độ liên hệ có khác giữa các vụ? (4) Mô hình nào ước lượng tốt hơn Baseline?
  - **Bảng Đối tượng thụ hưởng đầu ra:**
    1. *Nhà nghiên cứu / Sinh viên PTDL & Nông học:* Bộ dữ liệu sạch tái lập 100%, kiểm định GĐ1–GĐ4, so sánh 20 mô hình hồi quy & bằng chứng thích ứng El Niño 2024.
    2. *Cơ quan quản lý nông nghiệp / Khuyến nông địa phương:* Bản đồ gom cụm rủi ro 13 tỉnh, luật `IF–THEN` (Apriori & CART) và mô hình phân hạng năng suất (`AUC 0,95–0,97`).
    3. *Doanh nghiệp thu mua / Chuỗi cung ứng lúa gạo:* Quy luật phân bậc 3 vụ (`ĐX > HT > TĐ`), định vị vùng trọng điểm sản lượng & rủi ro hạn mặn ven biển.
  - **Ranh giới khoa học:** Ước lượng **hồi cứu (reduced-form)**, không thay thế khuyến cáo nông học chính thức.
- **Lời nói gợi ý:** Điểm khác biệt của nhóm là không chỉ gộp số liệu lúa cả năm mà bóc tách đúng từng mùa vụ gắn với lịch thời vụ thực tế, đồng thời chỉ rõ từng kết quả đầu ra phục vụ trực tiếp cho nhóm đối tượng nào.

---

## SLIDE 03 — Quy trình KDD 7 bước & Phạm vi 2 Tuyến dữ liệu song hành *(Giàu — 50s)*
- **Nội dung trên slide:**
  - Sơ đồ 7 bước KDD (Buổi 01): Thu thập → Làm sạch (`PASS`) → EDA & $3\sigma$ → Kiểm định OLS GĐ1–GĐ4 → Thử nghiệm Đa mô hình (Hồi quy · Phân lớp · Gom cụm · Luật kết hợp) → Kiểm định Độ nhạy/OOD → Tri thức & Khuyến nghị.
  - **Phạm vi chính thức (13/13 tỉnh ĐBSCL, 2015–2024) tổ chức thành 2 tuyến song hành:**
    - **Tuyến A (13/13 tỉnh ĐBSCL):** Đông Xuân (`n = 127`) + Hè Thu–Thu Đông (`n = 130`) = **`257` dòng** (phủ đủ 3 tiểu vùng: Thượng nguồn, Vùng giữa, Ven biển nhạy mặn).
    - **Tuyến B (Tách riêng 3 mùa vụ):** `An Giang`, `Kiên Giang`, `Cần Thơ` (`n = 90`, chiếm **40,5% sản lượng toàn ĐBSCL**) + **`7` bản ghi ngoại kiểm địa lý OOD** (`Tiền Giang`, `Vĩnh Long`, `Cà Mau`).
- **Lời nói gợi ý:** Toàn vùng 13 tỉnh là phạm vi chính thức chứ không phải phần mở rộng. Do NSO quốc gia gộp Hè Thu–Thu Đông còn nguồn công khai tách riêng 3 vụ 10 năm chỉ đủ ở 3 tỉnh vựa lúa lớn nhất, nhóm thiết kế 2 tuyến song hành và tuyệt đối không chia tách giả tạo số liệu gộp.

---

## SLIDE 04 — Thu thập đa nguồn & 6 Quyết định Tiền xử lý dữ liệu (Buổi 02) *(Giàu — 55s)*
- **Nội dung trên slide:**
  - **4 nguồn chính thức:** NSO (`NGTK 2019/2021/2024`), Niên giám/báo cáo cấp tỉnh, NASA POWER Daily MERRA-2 (`21` ô lưới phủ đất liền theo đa giác GADM v4.1), NOAA PSL ENSO ONI & `17` văn bản lịch thời vụ Cục Trồng trọt.
  - **6 quyết định kỹ thuật đạt `PASS` kiểm định tự động (`verify_cleaned_datasets.mjs`):**
    1. Nâng cấp bắt buộc năm 2019 từ Sơ bộ → Chính thức (`56` quyết định đối soát, `0` dòng 2019 sơ bộ còn sót).
    2. Quy đổi đơn vị chuẩn (`tạ/ha → tấn/ha`), kiểm tra `Diện tích × Năng suất = Sản lượng` (`0` lỗi vượt biên làm tròn).
    3. Trung bình khí tượng **Area-Weighted Zonal Mean** (`13/13` tỉnh tách biệt hoàn toàn, xóa lỗi trùng ô lưới `Bến Tre–Trà Vinh–Vĩnh Long`).
    4. Không điền `0` cho 3 ô Cà Mau không gieo trồng ĐX; giữ nguyên ngoại lệ thiên tai để đánh giá 2 chế độ.
    5. **Mã hóa (Buổi 02):** Dùng **One-Hot / Fixed-Effect**, **không dùng `LabelEncoder`** cho `province`/`season`.
    6. **Anti-Leakage:** Loại `area_ha`, `production_t` khỏi tập đặc trưng `X`; chia thời gian tăng dần.

---

## SLIDE 05 — EDA Câu hỏi 1 & Kiểm định Ngoại lệ $3\sigma$ (Buổi 02) *(Giàu — 50s)*
- **Hình chèn:** `../results/figures/01_eda_yield_by_season_and_province.png`
- **Điểm nhấn số liệu:**
  - Phân bậc rõ rệt **Đông Xuân (`7,33`) > Hè Thu (`5,69`) > Thu Đông (`5,51` tấn/ha)**; 3 tỉnh lớn nhất về sản lượng: Kiên Giang (`18,2%`), An Giang (`16,5%`), Đồng Tháp (`13,7%`).
  - **Quy tắc $3\sigma$ ($|z|>3$, Buổi 02):** Tuyến B có **`0`** ngoại lệ; Tuyến A ĐX phát hiện đúng **`3` ngoại lệ** đều là hạn mặn ven biển (**Bến Tre 2016** `0,05`, $z=-5{,}49$; **Bến Tre 2020** `0,04`, $z=-5{,}50$; **Cà Mau 2017** `3,00`, $z=-3{,}03$); HT–TĐ phát hiện **Bến Tre 2020** (`3,47`, $z=-3{,}42$).
  - **Quyết định:** Không xóa dữ liệu thiên tai thật → đánh giá **Dual-Regime (`127` vs `125`)**.

---

## SLIDE 06 — EDA Câu hỏi 2 & 3: Khắc phục Đa cộng tuyến & Tương quan theo vụ (Buổi 03–04) *(An — 55s)*
- **Hình chèn:** `../results/figures/02_eda_collinearity_and_within_corr.png`
- **Điểm nhấn số liệu:**
  - 12 cặp biến khí tượng thô có $|r| \ge 0{,}79$, **VIF max = `53,47`** (vi phạm nặng GĐ3).
  - Áp dụng **đủ 3 cách khắc phục Slide 51 Buổi 04:** (1) loại biến thừa, (2) tạo biến tổng hợp **`VPD`** từ `T` và `RH`, (3) dùng **`Ridge` & `Lasso`** → **VIF max giảm từ `53,47` xuống `2,72`**.
  - **Phát hiện KDD — Nghịch lý Simpson (Đảo dấu `8/8` biến khí tượng):** Nếu gộp 3 vụ, `Tổng mưa` ($-0{,}74$) tưởng như làm giảm năng suất còn `Ngày khô` ($+0{,}88$), `Nóng >35°C` ($+0{,}48$) lại dương; nhưng sau khi khử cố định `Tỉnh × Vụ`, **cả `8/8` biến đảo chiều dấu** (`Tổng mưa → +0,37, p=0,0003`, `Mưa lớn → +0,38`, `VPD/Nóng → âm`)!
  - **Khác biệt nút thắt giữa 3 vụ:** ĐX nhạy **mưa 90 ngày tiền vụ** ($+0{,}41$) & ENSO ($-0{,}20$); HT nhạy **khô nóng** (`Mưa +0,54`, `Ngày khô -0,51`, `VPD -0,42`); TĐ nhạy mạnh nhất **gió bão 2m** ($r = -0{,}61$).

---

## SLIDE 07 — Kiểm định 4 Giả định OLS (GĐ1–GĐ4) & Chọn biến (Buổi 04) *(An — 60s)*
- **Hình chèn:** `../results/figures/07_ols_assumptions_diagnostics_gd1_gd4.png`
- **Bảng tóm tắt GĐ1–GĐ4:**
  - **GĐ1 (F-test):** Đều đạt ($p < 0{,}0001$); Direct One-Hot Tuyến B đạt $R^2 = 0{,}914$, Adj. $R^2 = 0{,}903$.
  - **GĐ2 (Shapiro-Wilk):** Trên 13 tỉnh ĐX đủ 127 dòng, **Shapiro-Wilk bác bỏ mạnh ($p < 10^{-10}$)** do 2 năm mất trắng Bến Tre (`AIC = 273,3 → 165,5` khi tách 2 điểm này).
  - **GĐ3 (VIF):** Đạt (`VIF = 2,90` Tuyến B; `3,59–6,35` Tuyến A).
  - **GĐ4 (Breusch-Pagan & White):** Tuyến B đạt (`BP p=0,370`, `White p=0,192`); Tuyến A HT–TĐ **vi phạm White (`p=0,033`)** → dùng sai số chuẩn **HC3** & **Huber**.
  - **Chọn biến:** So sánh `Full 11 biến` (`VIF=353,8`), `Forward`, `Backward`, `Stepwise AIC` (`AIC=-17,53`) với `5 biến trực giao vật lý` (`VIF=3,43` sạch nhất).

---

## SLIDE 08 — Thiết kế Thực nghiệm & Chiến lược So sánh Đa mô hình *(An — 40s)*
- **Nội dung trên slide:**
  - **Nguyên tắc chống rò rỉ:** Chia tăng dần theo năm (`2015–2022` cho Expanding-CV 4-fold `2019–2022`; khóa kín hoàn toàn `Test 2023–2024`).
  - **Fixed-Effects Median Centering:** Tách phần nền cấu trúc `Tỉnh × Vụ` (chiếm `87,4%` phương sai) và huấn luyện mô hình dự báo độ lệch $\Delta y$ từ độ lệch khí tượng $\Delta X$ fit chỉ trên train.
  - **Đáp ứng tiêu chuẩn đánh giá đa phương pháp:** Trên **cùng bộ dữ liệu & cùng hệ độ đo**, thử nghiệm **9 hình thái Hồi quy (20 mô hình)**, **10 hình thái Phân lớp**, **9 thuật toán Gom cụm** và **Apriori** để chứng minh lựa chọn tối ưu bằng số liệu.

---

## SLIDE 09 — So sánh Đa hình thái Mô hình Hồi quy — Tuyến B (20 mô hình) *(An — 65s)*
- **Hình chèn:** `../results/figures/03_model_comparison_tier1_and_tier2.png`
- **Bảng so sánh rút gọn (9 hình thái trên Tuyến B `n = 90`):**
  - `Baseline_Median`: CV `0,2624` | Test `0,3002` ($R^2 = 0,842$)
  - `OLS_Anomaly_Ortho5_Trend`: CV `0,1993` | Test `0,1565`
  - **`Huber_Anomaly_Ortho5_Trend` (TỐT NHẤT CV):** **CV `0,1771` (`-32,5%`)** | Test `0,1447` ($R^2 = 0,949$)
  - **`Ridge / Lasso + Trend`:** CV `0,1881 / 0,1867` | **Test `0,1369 / 0,1374` (`-54,4%`, $R^2 = 0,954$)**
  - `DecisionTree / RF / GBR (+Trend)`: CV `0,1787–0,2285` | Test `0,1931–0,2186` *(cây bậc thang khó ngoại suy xu hướng)*
  - `SVR_Linear` vs `SVR_RBF`: Linear CV `0,1797` / Test `0,1556` vs **RBF Train `0,0780` → Test `0,3372` (overfit!)**
  - `MLP_ReLU` vs `MLP_Tanh`: CV `0,2143 / 0,2061` (kém hơn tuyến tính regularized & khó giải thích — Slide 8 Buổi 10).
- **Sai số theo vụ:** Giảm `-59,6%` ĐX, `-32,5%` HT (`Huber 0,1390`), `-76,5%` TĐ (`Ridge 0,0787`).

---

## SLIDE 10 — Hồi quy Tuyến A (13 tỉnh ĐBSCL) & Chẩn đoán Hạn mặn LOYO *(An — 55s)*
- **Hình chèn:** `../results/figures/05_residual_attribution_salinity_13provinces.png`
- **Điểm nhấn số liệu:**
  - Trên Đông Xuân 13 tỉnh (`Full 127` & `Ex-Salinity 125`), **`Huber_Anomaly`** thắng toàn bộ 14 mô hình trên Expanding-CV (`0,4482` vs Baseline `0,5070`, `OLS 0,7180`, `MLP 0,6108`, `RF 0,5280`; chế độ 125 giảm còn `0,3519`).
  - **Nghịch lý mưa Bến Tre 2015 vs 2020 (bằng chứng OVB thủy văn):** Năm **2020** có `ONI (+0,72)` và `VPD (0,80)` gần y hệt **2015** (`+0,70`, `0,81`) và **mưa tiền vụ nhiều hơn `+44%`** (`717` vs `498 mm`), nhưng vẫn mất trắng (`0,04` vs `5,09 tấn/ha`)!
  - **5/5 phần dư âm lớn nhất toàn vùng** nằm đúng ở vùng ven biển hạn mặn (`Bến Tre 2020: -5,05`, `2016: -4,71`, `Cà Mau 2017: -3,12`, `Trà Vinh 2020: -2,98`, `2016: -2,12`).
  - **Phát hiện Regime Shift 2023–2024:** Dù El Niño mạnh (`ONI = +1,90`), **12/12 tỉnh có số liệu 2016 đều tăng năng suất ĐX 2024** (`Bến Tre +5,04`, `Trà Vinh +2,66`, `Kiên Giang +1,60`) nhờ xuống giống sớm né mặn.

---

## SLIDE 11 — Kiểm định Độ nhạy (`±10/±15 ngày`) & Ngoại kiểm Địa lý OOD *(Giàu — 50s)*
- **Hình chèn:** `../results/figures/04_sensitivity_calendar_and_spatial.png` & `../results/figures/06_spatial_generalization_ood_check.png`
- **Điểm nhấn số liệu:**
  - **Độ nhạy Lịch & Không gian (6 kịch bản):** `Ridge+Trend` ổn định tuyệt đối (`Zonal 0,1369` vs `1 điểm 0,1385`, lệch chỉ `0,0016`; dịch `±10 ngày`: `0,1390–0,1492`; dịch `±15 ngày`: `0,1557–0,1683`).
  - **Ngoại kiểm OOD 7 mẫu chưa từng huấn luyện (`Tiền Giang`, `Vĩnh Long`, `Cà Mau`):** Mang mô hình học từ 3 tỉnh thượng nguồn dự báo sang vùng giữa & ven biển giúp **giảm 23,6% sai số** (`0,1440` vs Baseline `0,1884` tấn/ha).

---

## SLIDE 12 — So sánh Đa hình thái Mô hình Phân lớp — 3 Hạng Năng suất (Buổi 08–10) *(An — 55s)*
- **Hình chèn:** `../results/figures/08_classification_multimodel_roc_and_cm.png`
- **Điểm nhấn số liệu (10 hình thái trên `n = 257`, khóa kín Test `2023–2024` `n = 52`):**
  - *Chế độ 1 (Thuần Khí tượng + Tiểu vùng):* **`SVM_Linear`** (`Test Acc 76,9%`, `Macro-F1 0,734`, `AUC 0,916`) và `Logistic` (`F1 0,713`, `AUC 0,922`) vượt xa Cây đơn (`0,579`), RF (`0,532`), MLP (`0,460–0,532`).
  - *Chế độ 2 (Đầy đủ Khí tượng + Tỉnh + Vụ + Năm):* **`SVM_RBF`** dẫn đầu (`Exp-CV F1 0,801`, **`Test Acc 86,5%`, `Macro-F1 0,872`, `AUC 0,949`** — đúng `11/11` lớp Thấp, `0` nhầm lẫn Thấp ↔ Cao); **`Logistic_OvR`** (`F1 0,836`, `AUC 0,958`); **`SVM_Linear`** (`AUC 0,967`).
  - **Ảnh hưởng của hàm kích hoạt (Slide 15 Buổi 10):** Đổi `MLP ReLU → Tanh` đẩy Test Macro-F1 từ `0,460` lên `0,693`.

---

## SLIDE 13 — Phân lớp Rủi ro Nhị phân, Accuracy Paradox & Luật CART *(An — 45s)*
- **Nội dung trên slide:**
  - Bài toán C2: Dự báo vụ sụt giảm dưới kỳ vọng xu hướng (lớp rủi ro `29,3%` dev / `38,5%` test — mất cân bằng nhẹ).
  - **Bằng chứng sống động Slide 20 Buổi 08–09 (*Accuracy Paradox*):**
    - `MLP_ReLU` & `MLP_Tanh`: `Test Acc = 61,5%` (ngang Dummy) nhưng **`Precision = 0, Recall = 0, F1 = 0`** vì dự báo toàn lớp đa số!
    - `SVM_Linear (balanced)`: **`Recall = 0,60`, `F1 = 0,511`, `AUC = 0,588`**; `Logistic_Binary`: `Recall = 0,50`, `F1 = 0,455`.
  - **Luật IF–THEN trích xuất trực tiếp từ Cây CART (Slide 42 Buổi 08–09):**
    > `IF ONI > 0,80 (El Niño mạnh) AND Mưa 90 ngày tiền vụ ≤ -0,47 (thiếu mưa) → Rủi ro sụt giảm năng suất (Lớp 1); ELSE → Đạt/vượt kỳ vọng (Lớp 0).`

---

## SLIDE 14 — Gom cụm 13 tỉnh ĐBSCL — Kiểm chứng 3 Tiểu vùng Sinh thái (Buổi 11–12) *(An — 55s)*
- **Hình chèn:** `../results/figures/09_clustering_13provinces_dendrogram_and_pca.png`
- **Điểm nhấn số liệu (9 thuật toán · 3 nhóm độ đo Internal / External / Relative):**
  - **5 thuật toán** (`K-Means`, `K-Medoids PAM`, `Agglomerative Ward`, `Complete`, `Bisecting K-Means`) đồng thuận **100% (`Relative Rand = 1,000`)**, đạt `SSE = 30,32`, `Silhouette = 0,390`, `Calinski-Harabasz = 14,29`:
    1. *Ven biển rủi ro mặn cực đoan (3 tỉnh):* `Bến Tre`, `Cà Mau`, `Trà Vinh`.
    2. *Nội đồng Đông Bắc khô ấm (4 tỉnh):* `An Giang`, `Đồng Tháp`, `Long An`, `Tiền Giang`.
    3. *Giữa & Tây/Nam Sông Hậu ẩm gió năng suất cao (6 tỉnh):* `Cần Thơ`, `Hậu Giang`, `Kiên Giang`, `Vĩnh Long`, `Sóc Trăng`, `Bạc Liêu`.
  - **Tri thức KDD mới:** `Bạc Liêu` (ven biển) được gom vào nhóm năng suất cao nhờ công trình cống ngăn mặn; **`DBSCAN`** tự cô lập **`Bến Tre` là điểm nhiễu `-1`**.

---

## SLIDE 15 — Khai phá Luật Kết hợp Định lượng — Apriori (Buổi 06–07) *(An — 45s)*
- **Hình chèn:** `../results/figures/10_association_rules_lift_confidence.png`
- **Top 4 luật mạnh nhất (rời rạc hóa `pd.cut` + 5 độ đo `Support / Confidence / Lift / Leverage / Conviction`):**
  1. `IF MưaTiềnVụ=Cao AND Vùng=ThượngNguồn → NăngSuấtĐX=Cao` (`Sup=0,095`, `Conf=1,00`, `Lift=3,02`)
  2. `IF ENSO=LaNiña AND Vùng=ThượngNguồn → NăngSuấtĐX=Cao` (`Sup=0,102`, `Conf=0,81`, `Lift=2,46`)
  3. `IF Gió2m=Mạnh AND MưaTiềnVụ=TB → NăngSuấtĐX=Thấp` (`Sup=0,095`, `Conf=0,71`, `Lift=2,08`)
  4. `IF MưaTiềnVụ=TB AND Vùng=VenBiển → NăngSuấtĐX=Thấp` (`Sup=0,087`, `Conf=0,69`, `Lift=2,03`)

---

## SLIDE 16 — Ma trận Tổng kết: Thay đổi Phương pháp → Thay đổi Kết quả & Lựa chọn Tối ưu *(An — 50s)*
- **Bảng 1 trang trả lời thẳng tiêu chí cốt lõi của giảng viên:**
  | Giai đoạn / Bài toán | Các phương án đã triển khai so sánh | Phương án TỐT NHẤT | Lý do kỹ thuật & Đối tượng thụ hưởng |
  |---|---|---|---|
  | **Chọn đặc trưng** | 11 biến thô (`VIF 353,8`) vs Forward / Backward / Stepwise vs 5 biến vật lý trực giao | **5 biến vật lý trực giao** (`VIF 2,72`) + Stepwise đối chứng | Triệt đa cộng tuyến, giữ nguyên nghĩa vật lý nông học. |
  | **Hồi quy (Tuyến B)** | 20 mô hình (OLS, Ridge, Lasso, Huber, DT, RF, GBR, SVR Linear/RBF, MLP ReLU/Tanh) | **`Huber+Trend`** (CV `0,177`) & **`Ridge/Lasso+Trend`** (Test `0,137`) | Tốt nhất trên cỡ mẫu nhỏ, bền vững & diễn giải được hệ số. |
  | **Hồi quy (Tuyến A 13 tỉnh)** | 14 mô hình (Full `127` vs Ex-Salinity `125`) | **`Huber_Anomaly`** (CV `0,448` / `0,352`) | Miễn nhiễm đuôi hạn mặn vi phạm GĐ2 (`Shapiro p < 10^{-10}`). |
  | **Phân lớp 3 hạng (C1)** | 10 hình thái (Logistic, CART, RF, GBR, NB, SVM, MLP) × 2 chế độ | **`SVM_RBF`** (`F1 0,872`) & **`Logistic_OvR`** (`F1 0,836`, `AUC 0,958`) | Khuyến nông / Quản lý địa phương phân hạng rủi ro vụ mùa. |
  | **Gom cụm 13 tỉnh** | 9 thuật toán (K-Means, PAM, Ward/Comp/Avg/Single, Bisecting, DBSCAN, MeanShift) | **`Ward / K-Means / PAM` ($K=3$)** + **`DBSCAN`** phát hiện nhiễu | Phân vùng khách quan theo dữ liệu, tách riêng cực đoan Bến Tre. |
  | **Luật kết hợp** | Apriori định lượng (`Support, Confidence, Lift, Leverage, Conviction`) | Top luật `Lift 2,03–3,02` | Quy tắc ngôn ngữ tự nhiên dễ truyền đạt cho quản lý nông nghiệp. |

---

## SLIDE 17 — Hạn chế Trung thực & Hướng phát triển *(An — 35s)*
- **3 hạn chế khoa học được định lượng rõ:**
  1. **Biến bỏ sót (OVB):** Chưa có chuỗi đo độ mặn thực địa (`g/l`) và lưu lượng Mê Kông (gây sai số cực đại tại Bến Tre/Trà Vinh 2016, 2020).
  2. **Độ phân giải & Nguồn công bố:** MERRA-2 (`0,5°×0,625°`); chỉ 3/13 tỉnh công khai PDF tách riêng 3 vụ đủ 10 năm.
  3. **Regime Shift thích ứng:** Thay đổi lịch xuống giống né mặn 2024 làm giảm hiệu lực ngoại suy của mô hình tĩnh.
- **Hướng phát triển:** Bổ sung số liệu độ mặn trạm thủy văn Mỹ Thuận/Cần Thơ, viễn thám NDVI (Sentinel-2) và mô hình cập nhật trực tuyến theo mùa vụ.

---

## SLIDE 18 — Kết luận & Cảm ơn / Q&A *(Giàu & An — 25s)*
- **Tóm tắt 4 kết luận tương ứng 4 câu hỏi nghiên cứu:** (1) `ĐX > HT > TĐ`, phân hóa rõ 3 tiểu vùng; (2) Khí tượng liên hệ khác hẳn giữa 3 vụ; (3) Kiểm định GĐ1–GĐ4 chỉ ra hạn chế của OLS và chứng minh `Huber/Ridge/Lasso` vượt trội cây/SVR-RBF/MLP trên cỡ mẫu nhỏ; (4) Kết hợp Phân lớp (`SVM/Logistic`), Gom cụm (`Ward/K-Means/DBSCAN`) và Apriori tạo bộ công cụ hoàn chỉnh phục vụ nghiên cứu, khuyến nông và chuỗi cung ứng lúa gạo ĐBSCL.
- **Lời kết:** Cảm ơn thầy Phan Thành Huấn và các bạn đã lắng nghe; nhóm xin tiếp nhận câu hỏi phản biện!
