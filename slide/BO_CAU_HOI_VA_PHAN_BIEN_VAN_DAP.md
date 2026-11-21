# Bộ 20 Câu hỏi & Lập luận Phản biện Vấn đáp (5% Điểm Cuối kỳ)

> **Biên soạn bám sát 12 buổi giảng của CBGD Phan Thành Huấn** (Khoa CNTT, ĐH Sài Gòn) và toàn bộ bằng chứng định lượng đã kiểm chứng trong dự án.  
> **Nguyên tắc trả lời vấn đáp:** Ngắn gọn (30–45 giây/câu) → Nêu thẳng **nguyên lý từ slide** → Dẫn **con số thật từ dự án** → Chốt **quyết định kỹ thuật**.

---

## NHÓM 1: PHẠM VI, THU THẬP & TIỀN XỬ LÝ DỮ LIỆU (BUỔI 01 & 02)

### Câu 1: Đề tài đăng ký là ĐBSCL (13 tỉnh, 3 vụ = 390 dòng), tại sao tập tách riêng 3 vụ chỉ có 90 dòng (3 tỉnh)? Có phải làm thiếu phạm vi không?
- **Trả lời:** Dạ **không thiếu phạm vi**. Toàn vùng **13/13 tỉnh ĐBSCL (2015–2024)** là phạm vi chính thức nhóm thực hiện đầy đủ qua **Tuyến A (`257` dòng = `127` ĐX + `130` HT–TĐ từ NSO)**, phủ trọn cả 3 tiểu vùng thượng nguồn – vùng giữa – ven biển. Tuy nhiên, NSO quốc gia chỉ công bố gộp `Hè Thu và Thu Đông`, còn Niên giám tỉnh công khai PDF tách riêng 3 vụ suốt 10 năm hiện chỉ đủ ở 3 tỉnh vựa lúa lớn nhất (`An Giang`, `Kiên Giang`, `Cần Thơ` — chiếm **40,5% sản lượng toàn ĐBSCL**). Thực hiện đúng **phương án dự phòng trong `DeTaiPTDL.pdf`**, nhóm giữ 2 tuyến song hành, tuyệt đối không tự chia giả tạo số liệu gộp, và bổ sung thêm **7 bản ghi ngoại kiểm địa lý OOD** (`Tiền Giang`, `Vĩnh Long`, `Cà Mau`) để kiểm chứng độ tổng quát sang vùng giữa và ven biển.

### Câu 2: Tại sao Cà Mau có 3 năm không có năng suất Đông Xuân (2015, 2016, 2018) mà nhóm không điền bằng `0` hay trung bình (`mean`)?
- **Trả lời:** Theo quy tắc làm sạch dữ liệu (Buổi 02) và cam kết trong `DeTaiPTDL.pdf`: Cà Mau là tỉnh ven biển phụ thuộc nước trời/lúa–tôm, những năm đó **không tổ chức gieo trồng vụ Đông Xuân** (structural missing — không có diện tích canh tác), hoàn toàn khác với mất mùa. Nếu điền `0` sẽ làm méo nghiêm trọng phân phối năng suất và hệ số hồi quy; nếu điền `mean` sẽ tạo ra vụ mùa giả không tồn tại trong thực tế. Vì vậy giữ nguyên `n = 127` là chuẩn nghiệp vụ nhất.

### Câu 3: Tại sao Bến Tre Đông Xuân 2016 (`0,05`) và 2020 (`0,04 tấn/ha`) vượt xa quy tắc ngoại lệ $3\sigma$ ($z \approx -5,5$) mà nhóm không xóa đi?
- **Trả lời:** Theo Buổi 02, phát hiện ngoại lệ bằng quy tắc $3\sigma$ giúp **nhận diện bất thường**, nhưng xử lý ngoại lệ phải phân biệt giữa **lỗi nhập liệu** (phải sửa/xóa) và **sự kiện cực đoan có thật** (domain outlier). Nhóm đã kiểm chứng công thức `Diện tích × Năng suất = Sản lượng` (`pass_within_source_rounding`) và đối chiếu lịch sử: 2016 và 2020 đúng là 2 đợt hạn mặn lịch sử làm mất trắng lúa Đông Xuân ở Bến Tre. Xóa bỏ là che giấu rủi ro thật của ĐBSCL; do đó nhóm giữ nguyên, gắn cờ `domain_outlier_flag`, báo cáo song song **Dual-Regime (`127` vs `125`)** và chuyển sang hàm mất mát vững **Huber Loss**.

### Câu 4: Tại sao không dùng `LabelEncoder` cho tên tỉnh (`province_id`) và mùa vụ (`season`) cho gọn cột?
- **Trả lời:** Đúng như cảnh báo ở **Buổi 02 (Phần Biến đổi dữ liệu)**: `LabelEncoder` chỉ phù hợp khi biến phân loại có **thứ tự ngầm định (ordinal)** (như Thấp < Trung bình < Cao). `province_id` và `season` là biến định danh (**nominal**) không có thứ tự số học; nếu gán An Giang = 0, Bạc Liêu = 1, Bến Tre = 2 thì mô hình tuyến tính hoặc khoảng cách sẽ hiểu nhầm `Bến Tre = 2 × Bạc Liêu`. Do đó nhóm dùng **One-Hot Encoding** và **Fixed-Effects Centering** (fit chỉ trên train).

### Câu 5: Tại sao không đưa `area_ha` (diện tích) và `production_t` (sản lượng) vào làm đặc trưng dự báo năng suất?
- **Trả lời:** Vì theo định nghĩa toán học $\text{Năng suất} = \text{Sản lượng} / \text{Diện tích}$. Đưa `production_t` (hay kèm `area_ha`) vào đầu vào là **rò rỉ mục tiêu (target leakage)**, mô hình sẽ học lại phép chia chứ không học tác động khí tượng. Nhóm chỉ dùng 2 cột này để kiểm tra chất lượng dữ liệu đầu vào và mô tả tỷ trọng vùng.

### Câu 6: Khí tượng NASA POWER độ phân giải lưới `0,5° × 0,625°`, lấy 1 tọa độ trung tâm tỉnh có bị trùng giữa các tỉnh nhỏ không?
- **Trả lời:** Có ạ! Lúc kiểm tra thô, 1 tọa độ trung tâm bị trùng 100% ô lưới MERRA-2 giữa cụm `Bến Tre – Trà Vinh – Vĩnh Long` và `Cần Thơ – Hậu Giang`. Nhóm đã khắc phục triệt để bằng cách tải lưới **21 ô phủ đất liền**, tính giao hình học với ranh giới hành chính **GADM v4.1** để tổng hợp **Area-Weighted Zonal Mean** giúp **13/13 tỉnh tách biệt hoàn toàn**, đồng thời chạy kiểm định độ nhạy `Zonal vs 1 điểm` (sai số Test chênh chỉ `0,0016` tấn/ha).

---

## NHÓM 2: PHÂN TÍCH HỒI QUY, 4 GIẢ ĐỊNH GĐ1–GĐ4 & CHỌN BIẾN (BUỔI 03 & 04)

### Câu 7: Nhóm đã kiểm định đủ 4 giả định hồi quy tuyến tính (GĐ1–GĐ4) chưa? Kết quả có giả định nào bị vi phạm không và nhóm xử lý thế nào?
- **Trả lời:** Dạ đã kiểm định đầy đủ cả 4 giả định (`ols_assumptions_diagnostics_gd1_to_gd4.csv`, Hình `07`):
  - **GĐ1 (Tuyến tính — F-test):** Đạt trên mọi mô hình ($p < 0{,}0001$).
  - **GĐ2 (Phần dư chuẩn, trung bình 0 — Shapiro-Wilk):** Trên Tuyến A ĐX đủ 127 dòng bị **vi phạm rất nặng ($p < 10^{-10}$)** do 2 điểm mất trắng mặn Bến Tre → nhóm xử lý bằng **HuberRegressor** (ít nhạy đuôi ngoại lệ) và **Dual-Regime**.
  - **GĐ3 (Không đa cộng tuyến — VIF & Pearson):** Ban đầu **vi phạm nặng (`VIF max = 53,47`)** → nhóm áp dụng trọn 3 cách Slide 51 Buổi 04, kéo `VIF` về **`2,72` (< 5)**.
  - **GĐ4 (Phương sai không đổi — Breusch-Pagan & White):** Tuyến B đạt (`BP p = 0,370`, `White p = 0,192`), nhưng Tuyến A HT–TĐ **vi phạm White test (`p = 0,033`)** → nhóm báo cáo sai số chuẩn vững **HC3** song song sai số cổ điển.

### Câu 8: Trong 3 cách khắc phục đa cộng tuyến (Buổi 04 Slide 51), nhóm dùng cách nào?
- **Trả lời:** Nhóm kết hợp **cả 3 cách** một cách nhất quán:
  1. *Loại bỏ các biến tương quan rất mạnh* (`Tmax_TB ↔ Ngày>35°C: r=0,962`; `Mưa ↔ Ngày khô: r=-0,924`).
  2. *Tính biến tổng hợp mới từ biến cũ:* dùng **VPD (Vapor Pressure Deficit)** tích hợp vật lý giữa nhiệt độ `T` và độ ẩm tương đối `RH`.
  3. *Dùng hồi quy **Ridge (L2)** và **Lasso (L1)*** (trên Tuyến B, `Lasso` tự co 4 biến nhiễu về `0`, giữ lại `year_z` và `ws2m_mean_ms`; `Ridge` co mượt toàn bộ giúp đạt Test MAE `0,1369`).

### Câu 9: `Stepwise AIC` chọn ra 4 biến có `AIC = -17,53` thấp hơn `5 biến trực giao vật lý` (`AIC = 1,71`), tại sao nhóm vẫn chọn bộ 5 biến trực giao cho hệ thống mô hình chính?
- **Trả lời:** Vì 2 lý do khoa học:
  1. `AIC` đo độ khớp nội mẫu trên `train`, trong khi `Forward`/`Backward` tự động vẫn chọn cặp biến có `VIF = 13,6–18,3 > 10` (mất ổn định hệ số). Bộ 5 biến trực giao có **`VIF = 3,43` (thấp nhất)** và đại diện đủ 5 cơ chế vật lý độc lập (khô khí quyển VPD, mưa trong vụ, gió bão, nước tiền vụ, ENSO lưu vực).
  2. Khi kết hợp với regularization (`Ridge/Huber`) và đánh giá ngoài mẫu trên `Test 2023–2024`, bộ 5 biến đạt Test MAE **`0,1369`** — vượt cả `Stepwise` (`0,1460`) mà không lo chọn nhầm biến do cỡ mẫu nhỏ (`n = 72`).

### Câu 10: Vì sao trên Test `2023–2024`, mô hình không dùng khí tượng (`Structural_FE_Plus_Trend = 0,1335`) lại ngang ngửa `Ridge+Trend` (`0,1369`)? Vậy khí tượng có vô ích không?
- **Trả lời:** Khí tượng **không hề vô ích** — bằng chứng là trên **Expanding-Window CV (2019–2022, 36 điểm OOS)**, thêm khí tượng giúp giảm MAE rõ rệt từ `0,1988` xuống **`0,1771` (`Huber+Trend`)** và **`0,1881` (`Ridge+Trend`)**, thậm chí trên **Test vụ Thu Đông (`0,0787` vs `0,0849`)** và **Hè Thu (`Huber 0,1390` vs `0,1867`)** mô hình có khí tượng vẫn thắng. Lý do duy nhất `Structural+Trend` nhỉnh nhẹ `0,0034` tấn/ha trên tổng Test 2023–2024 là do **Regime Shift thích ứng El Niño 2024**: trong 2015–2022 El Niño mạnh kéo năng suất giảm (2016), nhưng năm 2024 nông dân ĐBSCL chủ động xuống giống sớm né mặn nên Đông Xuân 2024 vẫn trúng mùa — đây là phát hiện thực chứng rất giá trị về thích ứng khí hậu.

---

## NHÓM 3: SO SÁNH ĐA HÌNH THÁI MÔ HÌNH HỒI QUY & PHÂN LỚP (BUỔI 08, 09, 10)

### Câu 11: Tại sao Random Forest và Gradient Boosting (GBR) thường rất mạnh nhưng trên bài toán hồi quy của nhóm lại thua `Huber`, `Ridge`, `Lasso`?
- **Trả lời:** Do 2 đặc tính cốt lõi của dữ liệu và thuật toán:
  1. **Cỡ mẫu bảng nông nghiệp nhỏ (`n = 90` Tuyến B, `train = 72`):** Mô hình cây cần lượng mẫu lớn để chia không gian nhiều chiều ổn định; dù đã khóa nông (`max_depth = 2–3`), phương sai vẫn lớn hơn mô hình tuyến tính regularized (`RF Test = 0,2180`, `GBR = 0,2186` vs `Ridge = 0,1369`).
  2. **Bản chất hàm bậc thang của cây quyết định:** Cây không thể **ngoại suy tuyến tính** vượt ra ngoài biên giá trị `y_train`; khi năng suất `2023–2024` tiếp tục tăng theo xu hướng `year`, cây bị "chặn trần" ở mức lá cao nhất của quá khứ, còn `Ridge/Lasso/Huber` ngoại suy mượt xu hướng tăng.

### Câu 12: Khi thay cây quyết định bằng SVM (`SVR`) và Mạng Nơ-ron (`MLP`), kết quả khác nhau thế nào?
- **Trả lời:** Rất khác biệt và minh họa đúng lý thuyết **Buổi 10**:
  - **SVM Regression (so sánh kernel, Slide 32 Buổi 10):** `SVR_Linear` ổn định rất tốt (`CV = 0,1797`, `Test = 0,1556`), còn `SVR_RBF` (kernel phi tuyến) bị **overfit kinh điển**: `Train MAE = 0,0780` thấp nhất bảng nhưng `Test MAE` vọt lên **`0,3372`**, thua cả Baseline (`0,3002`)!
  - **MLP Neural Net (so sánh hàm kích hoạt, Slide 15 Buổi 10):** Trên Expanding-CV, cả `MLP_ReLU (0,2143)` và `MLP_Tanh (0,2061)` đều thua `Huber (0,1771)`, `SVR_Linear (0,1797)`, `Lasso (0,1867)`, `Ridge (0,1881)` và khó giải thích nguyên nhân vật lý (đúng nhược điểm **Slide 8 Buổi 10**). Đổi hàm kích hoạt từ `ReLU → Tanh` giúp giảm sai số Test từ `0,1728 → 0,1237` nhờ tính mượt của `tanh` dưới phạt L2 mạnh.

### Câu 13: Tại sao trên Test Tuyến B, `MLP_Tanh` đạt `0,1237` (nhỏ nhất Test) nhưng nhóm KHÔNG chọn nó làm mô hình tốt nhất?
- **Trả lời:** Vì nguyên tắc bất di bất dịch trong `DeTaiPTDL.pdf` và thực hành Data Science chuẩn: **chọn mô hình dựa trên Validation / Expanding-Window CV (`2019–2022`), tuyệt đối không nhìn kết quả Test để chọn ngược lại (tránh Test-set overfitting / p-hacking)**. Trên Expanding-CV, `Huber+Trend` (`0,1771`) và `Lasso/Ridge+Trend` (`0,1867–0,1881`) đều vượt rõ `MLP_Tanh` (`0,2061`), đồng thời trên Tuyến A 13 tỉnh `MLP` còn kém xa `Huber` (`0,6108` vs `0,4482`).

### Câu 14: Trong bài toán phân lớp 3 hạng năng suất (C1), tại sao `SVM_RBF` và `Logistic_OvR` lại thắng Cây quyết định CART và Mạng nơ-ron MLP?
- **Trả lời:** Với `n = 205` mẫu huấn luyện (`dev`) và không gian đặc trưng chuẩn hóa có biên phân tách rõ giữa các nhóm năng suất vụ ĐX vs HT–TĐ và các tiểu vùng, `SVM` (tối đa hóa lề — maximum margin) và `Logistic` (phạt L2) chống nhiễu rất tốt (`SVM_RBF`: `Test Acc 86,5%`, `F1 0,872`, `AUC 0,949`; `Logistic_OvR`: `F1 0,836`, `AUC 0,958`). Cây đơn `CART` (`F1 0,599`) dễ biến động ngưỡng cắt nhưng bù lại cho **luật IF–THEN trực quan**; còn `MLP_ReLU` (`F1 0,460`) thiếu dữ liệu nên phân loại kém trên tập Test.

### Câu 15: Trong bài toán phân lớp nhị phân rủi ro (C2), tại sao `MLP` có `Accuracy = 61,5%` cao nhất nhưng lại là mô hình TỆ NHẤT?
- **Trả lời:** Đây chính là **bẫy Accuracy trên dữ liệu mất cân bằng** mà thầy nhấn mạnh ở **Slide 20 Buổi 08–09**! Lớp rủi ro chỉ chiếm `29,3%` ở `dev` và `38,5%` ở `test`. `MLP` học cách "lười biếng" đoán 100% các vụ là an toàn (lớp 0) nên đạt `Accuracy = 61,5%`, nhưng **`Precision = 0`, `Recall = 0`, `F1 = 0`** — tức bỏ sót 100% vụ mất mùa! Do đó phải dùng `class_weight='balanced'` và đánh giá bằng **`Recall`, `F1`, `ROC-AUC`**: khi đó **`SVM_Linear`** đạt `Recall = 0,60`, `F1 = 0,511`.

### Câu 16: Tại sao không dùng K-Fold ngẫu nhiên thuần mà phải dùng Expanding-Window CV?
- **Trả lời:** Vì dữ liệu có cấu trúc **chuỗi thời gian – bảng (2015–2024)** với xu hướng tăng năng suất theo năm và tương quan ENSO liên tỉnh trong cùng năm. K-Fold ngẫu nhiên sẽ trộn năm tương lai (`2023–2024`) vào train để dự báo quá khứ (`2016`), gây **rò rỉ thời gian (temporal leakage)** và làm ảo hóa hiệu năng. Tuy nhiên ở bài toán phân lớp C1/C2, nhóm vẫn báo cáo **song song cả 5-Fold Stratified CV (Buổi 08–09) lẫn Expanding-Window CV** để thấy rõ mức sụt giảm khi chuyển sang kiểm tra tương lai thật.

---

## NHÓM 4: GOM CỤM 13 TỈNH (BUỔI 11–12) & LUẬT KẾT HỢP (BUỔI 06–07)

### Câu 17: Nhóm dựa vào đâu để chọn số cụm $K = 3$ và kết luận thuật toán gom cụm nào tốt nhất cho 13 tỉnh ĐBSCL?
- **Trả lời:** Nhóm đánh giá đủ **3 trụ cột của Buổi 11 (Slide 32)**:
  - **Đánh giá trong (Internal):** Biểu đồ Elbow `SSE` gãy rõ nhất tại $K = 3$ (`56,8 → 30,3`), đồng thời `Silhouette = 0,390` và `Calinski-Harabasz = 14,29` đạt tốt nhất cho cấu trúc 3 nhóm.
  - **Đánh giá tương đối (Relative):** Cả **5 thuật toán độc lập** (`K-Means`, `K-Medoids PAM`, `Agglomerative Ward`, `Complete`, `Bisecting K-Means`) cho kết quả **trùng khớp 100% (`Pairwise Rand Index = 1,000`)** → khẳng định cấu trúc 3 cụm cực kỳ bền vững, không phụ thuộc ngẫu nhiên vào 1 thuật toán.
  - **Giá trị bổ trợ của `DBSCAN`:** Tự động tách **`Bến Tre` là điểm nhiễu (`-1`)**, chứng minh một cách không giám sát rằng rủi ro hạn mặn của Bến Tre dị biệt hoàn toàn với 12 tỉnh còn lại.

### Câu 18: Tại sao chỉ số `ARI` giữa cụm dữ liệu (`K-Means/Ward`) và 3 tiểu vùng hành chính chỉ là `0,137`? Có phải gom cụm bị sai không?
- **Trả lời:** **Không phải sai — mà chính là phát hiện tri thức mới (KDD)!** 3 tiểu vùng nông học phân theo địa giới/lịch thời vụ, trong khi gom cụm nhóm các tỉnh theo **hành vi thực tế của khí hậu + năng suất**. Ví dụ nổi bật: **Bạc Liêu** nằm ven biển nhưng có hệ thống cống ngăn mặn vùng ngọt hóa rất hiệu quả nên năng suất ĐX đạt `7,46 tấn/ha` (min `6,77`), hành xử giống nhóm năng suất cao (`Cần Thơ`, `Hậu Giang`, `Kiên Giang`) chứ không bị sập năng suất như `Bến Tre – Cà Mau – Trà Vinh`. Còn nếu muốn bám sát khoảng cách trung bình địa lý thì `Agglomerative_Average` cho đồng thuận rất cao (`ARI = 0,410`, `NMI = 0,656`).

### Câu 19: Ý nghĩa của 5 độ đo `Support`, `Confidence`, `Lift`, `Leverage`, `Conviction` trong luật kết hợp nhóm rút ra là gì? Nếu `Confidence = 1,0` thì đã chắc chắn là luật tốt chưa?
- **Trả lời:** Chưa đủ nếu chỉ nhìn `Confidence` (Buổi 06–07)! Một luật có `Confidence` cao nhưng vế phải $Y$ vốn đã rất phổ biến (`Support(Y)` cao) thì chỉ là ngẫu nhiên. Phải kiểm tra **`Lift > 1`** (tương quan dương thực sự), **`Leverage > 0`** (vượt mức độc lập) và **`Conviction > 1`** (mức phụ thuộc chiều suy diễn). Luật mạnh nhất nhóm tìm được là `IF MưaTiềnVụ=Cao AND Vùng=ThượngNguồn → NăngSuấtĐX=Cao` có `Support = 0,095`, `Confidence = 1,00`, **`Lift = 3,02`** (tăng gấp 3 lần xác suất đạt năng suất Cao so với ngẫu nhiên), `Leverage = 0,063`, `Conviction = ∞`.

### Câu 20: Nếu chỉ được chọn 1 câu chốt trả lời cho câu hỏi *"Sản phẩm cuối cùng của đồ án phục vụ thực tế cho ai và hạn chế lớn nhất là gì?"*, nhóm nói gì?
- **Trả lời:** Sản phẩm phục vụ **3 nhóm đối tượng** (nhà nghiên cứu/sinh viên PTDL, cơ quan khuyến nông/quản lý địa phương, doanh nghiệp chuỗi cung ứng lúa gạo) như công cụ **phân tích hồi cứu, phân vùng rủi ro và sàng lọc mô hình định lượng** — hoàn toàn minh bạch nguồn & tái lập 100%, kèm Dashboard tương tác offline (`dashboard/index.html`). Hạn chế lớn nhất mà nhóm đã chứng minh định lượng bằng LOYO là **thiếu chuỗi số liệu độ mặn (`g/l`) và lưu lượng nước Mê Kông (OVB)**, khiến khí tượng tại chỗ không thể tự dự báo các cú sốc mất trắng mặn cực đoan như Bến Tre 2016/2020; do đó kết quả mang tính tham khảo khoa học, không thay thế khuyến cáo nông học chính thức.

### Câu 21 (Câu hỏi cốt lõi KDD — Buổi 01 Slide 9): Đồ án của nhóm có khai phá được *tri thức mới* hay *quy luật bất ngờ* nào không, hay toàn những điều ai làm nông cũng biết?
- **Trả lời:** Nhóm phân biệt rõ **điều hiển nhiên** (như `ĐX > HT > TĐ` — chỉ dùng xác nhận dữ liệu sạch) với **5 tri thức phi hiển nhiên thực sự khai phá từ dữ liệu**:
  1. **Nghịch lý Simpson (Đảo dấu `8/8` biến khí tượng):** Phân tích gộp 3 vụ cho kết luận ngược đời (`Mưa: r = -0,738`, `Ngày khô: +0,881`, `Nóng >35°C: +0,475`), nhưng sau khi khử cố định `Tỉnh × Vụ` thì **cả 8/8 biến đảo dấu** (`Mưa → +0,369, p=0,0003`, `Mưa lớn → +0,381, p=0,0002`, `VPD/Nóng → âm`).
  2. **Phân dị nút thắt theo vụ:** ĐX phụ thuộc nước tiền vụ (`+0,41`) & ENSO (`Apriori Lift = 3,02`); HT nhạy khô nóng (`VPD -0,42`); TĐ nhạy nhất **gió bão 2m (`-0,61`)** nhưng lại tăng năng suất nhanh nhất (`+0,078 tấn/ha/năm`).
  3. **Nghịch lý Bạc Liêu (Gom cụm không giám sát):** Có khí hậu ven biển y hệt Bến Tre/Trà Vinh (`gió 3,63 m/s`) nhưng cả 5 thuật toán gom cụm đều tách khỏi nhóm rủi ro mặn sang cụm năng suất cao (`7,46 tấn/ha`, `min 6,77`) nhờ hạ tầng cống ngăn mặn ngọt hóa.
  4. **Nghịch lý mưa Bến Tre 2015 vs 2020:** Năm 2020 có `ONI` và `VPD` gần y hệt 2015 và **mưa tiền vụ nhiều hơn `+44%`** (`717` vs `498 mm`) nhưng vẫn mất trắng (`0,04` vs `5,09`), chứng minh định lượng vai trò thủy văn lưu vực Mê Kông (OVB).
  5. **Regime Shift thích ứng El Niño 2024:** Dưới El Niño mạnh 2024 (`ONI = +1,90`), `12/12` tỉnh có số liệu 2016 đều tăng mạnh năng suất ĐX so với 2016 nhờ chủ động xuống giống sớm né mặn.
  *(Đồng thời nhóm chủ động loại bỏ các luật Apriori Tuyến B bị dính trộn mùa, chỉ báo cáo luật nội vụ Đông Xuân Tuyến A.)*
