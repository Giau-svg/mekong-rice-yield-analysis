# Đánh giá Logic Thu thập, Ghép nối Đa nguồn và Tài liệu Phản biện Hội đồng

> **Phạm vi rà soát:** Kho dữ liệu thô (`data/raw/`), danh mục kiểm kê (`data/catalog/`), mã nguồn thu thập–trích xuất (`scripts/`) và đề xuất đề tài (`DeTaiPTDL.pdf`).  
> **Trạng thái hiện tại:** **ĐÃ ĐẠT CỔNG BÀN GIAO BƯỚC CÀO (`handoff_gate_passed = true` trong `docs/raw_handoff_readiness.json`)** — sẵn sàng chuyển sang bước Làm sạch & Chuẩn hóa (`docs/RAW_HANDOFF_CONTRACT.md`). Chưa chạy làm sạch, ghép lúa–khí tượng hay huấn luyện mô hình.

---

## 1. Kết luận nhanh: Logic cào & ghép nối hiện tại đã hợp lý chưa?

**Trả lời ngắn gọn:** **ĐÃ HỢP LÝ & ĐẠT CHUẨN NGHIỆP VỤ** cho đầu ra bước Cào dữ liệu trên cả 4 khối Input (Lúa – Khí tượng – Lịch thời vụ – Ranh giới không gian). Các quy tắc ghép nối đã được chuẩn hóa tường minh để triển khai ngay ở bước Làm sạch & Tiền xử lý.

| Khía cạnh | Đánh giá | Bằng chứng thực tế trong dự án |
|---|---|---|
| **Kiến trúc cào & truy xuất nguồn gốc** | **Đạt chuẩn** | Lưu nguyên bản **1.000 tệp** (996 SHA-256 duy nhất, ~1,05 GB), kiểm tra chữ ký `%PDF-`/`%%EOF`, ZIP, đủ 4.018 ngày NASA (2014–2024, 0 `fill_value`), GeoJSON 63 tỉnh, 9 văn bản lịch `.gov.vn`; ghi cả 480 URL thất bại (`unavailable_sources.csv`). |
| **Độ tin cậy liên nguồn (lúa)** | **Rất cao** | Đối chiếu 90 dòng 3 vụ riêng (An Giang, Kiên Giang, Cần Thơ; 2015–2024) với NSO: **0 sai lệch** Đông Xuân; tổng `Hè Thu + Thu Đông` khớp NSO **< 0,5%**; sai số nội tại `Diện tích × Năng suất vs Sản lượng` tối đa **0,009%**. Đã trích thêm **233 dòng NGTK 2021** (bắt được **25/47 dòng năm 2019 có điều chỉnh chính thức** so với NGTK 2019 sơ bộ). |
| **Lịch thời vụ & Ranh giới không gian** | **Đã hoàn thiện Input thô** | • Đã trích **17 bản ghi lịch thời vụ** nguyên văn từ 9 văn bản chính thức `.gov.vn` (khung 3 vụ Cục Trồng trọt + chỉ đạo tiểu vùng) vào `data/raw/season_calendar_raw.csv`.<br>• Đã tải **GADM v4.1** (`gadm41_VNM_1.json`) và tính bảng trọng số giao cắt `weather_grid_province_overlap.csv` (21 ô ĐBSCL, loại 9 ô biển/ngoài vùng, **13/13 tỉnh** có hồ sơ trọng số riêng biệt). |
| **Sẵn sàng bước Làm sạch** | **ĐÃ ĐÁP ỨNG (PASS)** | Kiểm định tự động `node scripts/verify_raw_handoff.mjs` đạt 4/4 khối Input (`docs/raw_handoff_readiness.json`). |

---

## 2. Cô đọng kiến trúc thu thập và quy tắc ghép nối đa nguồn

### 2.1. Vai trò các nhóm nguồn đã thu thập
1. **Niên giám Thống kê cấp tỉnh (`rice_captured_main_seasons.csv`, 90 dòng):** Nguồn **ưu tiên cao nhất** cho bộ ba vụ tách riêng (`An Giang`, `Kiên Giang`, `Cần Thơ`; 2015–2024; đơn vị `ha`, `tạ/ha`, `tấn`).
2. **Niên giám Thống kê quốc gia NSO 2019, 2021 & 2024 (`nso_rice_province_tables.csv`, 467 dòng; `nso_rice_2021_reconciliation.csv`, 233 dòng):** Cung cấp nền chuẩn 13 tỉnh (2015–2024) cho `Lúa cả năm` (130), `Lúa đông xuân` (127), `Lúa hè thu và thu đông` gộp (130), `Lúa mùa` (80), đồng thời cung cấp **47 dòng năm 2019 chính thức** từ NGTK 2021 để đối chiếu cập nhật bản Sơ bộ 2019.
3. **Báo cáo KT-XH năm cấp tỉnh (`rice_report_season_values.csv`, 7 dòng: Tiền Giang TĐ 2021–2024, Vĩnh Long HT & TĐ 2023, Cà Mau HT 2024):** Bổ sung vụ tách riêng có điều kiện; gắn rõ đơn vị gốc (`tấn` vs `nghìn tấn`), tỷ lệ diện tích thu hoạch (`99,18%` ở Cà Mau HT 2024) và phạm vi vụ.
4. **Khí tượng lưới NASA POWER Daily API (`data/raw/weather/` & `data/raw/weather_grid/`):** 33 tệp JSON = 132.594 dòng điểm–ngày từ **01/01/2014 đến 31/12/2024** (chốt 6 biến chung toàn lưới 30 ô; lấy từ 2014 để phủ vụ Đông Xuân 2014–2015 vắt qua 2 năm dương lịch).
5. **Tài liệu lịch thời vụ chính thức (`data/raw/season_calendar_raw.csv`, 17 bản ghi) & ranh giới không gian (`data/raw/geo/gadm41_VNM_1.json` + `weather_grid_province_overlap.csv`, 55 dòng):** Trích nguyên văn từ 9 văn bản `.gov.vn` (Cục Trồng trọt / Bộ NN&PTNT, Trung tâm Khuyến nông Quốc gia, địa phương) + 5 dòng SAGE lịch sử; và ánh xạ diện tích chồng lấp giữa 13 tỉnh ĐBSCL với 21 ô lưới MERRA-2 (loại 9 ô biển/ngoài vùng).

### 2.2. Logic khóa ghép nối theo 3 trục bắt buộc
Để một bản ghi đạt chuẩn đưa vào mô hình (`eligible_for_model = true`), phép ghép phải thỏa mãn đồng thời 3 trục:
- **Trục hành chính – định danh:** Khóa duy nhất `(province_id, harvest_year, season)` theo địa giới 13 tỉnh ĐBSCL trước 2025; `harvest_year` là **năm thu hoạch**, không phải năm gieo.
- **Trục định nghĩa vụ & phiên bản:** Chỉ ghép vào bộ 3-vụ chuẩn các dòng có `season_scope = single` (không chứa Xuân Hè gộp hoặc Hè Thu–Thu Đông gộp), đã chọn 1 phiên bản duy nhất theo thang ưu tiên nguồn.
- **Trục không gian – thời gian (Lúa ↔ Khí tượng):**
  - *Thời gian:* Tổng hợp chuỗi ngày NASA POWER trong cửa sổ `[start_date, end_date]` của từng `(province_id, harvest_year, season)` (Đông Xuân cho phép `start_date` thuộc năm `harvest_year - 1`).
  - *Không gian:* Gán khí tượng theo **lưới tỉnh đã áp mặt nạ địa giới/vùng lúa** (hoặc kiểm định độ nhạy giữa 1 điểm đại diện và trung bình các ô lưới phủ tỉnh).

---

## 3. Năm vấn đề cốt lõi, hướng giải quyết và luận điểm "Vì sao làm vậy?"

### Vấn đề 1: Độ phủ 3 vụ tách riêng không đều (194/390 ô) & khác biệt định nghĩa vụ
- **Thực trạng:** Trong lưới kiểm kê 390 ô (13 tỉnh × 10 năm × 3 vụ), hiện có **194 ô tách vụ** (127 Đông Xuân, 32 Hè Thu, 35 Thu Đông) và **196 ô chưa có tách vụ** (193 ô mới có bảng gộp Hè Thu–Thu Đông của NSO; 3 ô Cà Mau Đông Xuân 2015, 2016, 2018 bỏ trống ở nguồn). Chỉ **3 tỉnh** (`An Giang`, `Kiên Giang`, `Cần Thơ`) đủ cả 3 vụ tách riêng suốt 2015–2024 (90 dòng). Tiền Giang ghi nhận Hè Thu gộp cả Xuân Hè.
- **Vì sao xảy ra:** NSO cấp quốc gia theo chuẩn thống kê chỉ công bố gộp `Hè Thu và Thu Đông`; nhiều cổng thống kê tỉnh cũ đổi tên miền/lỗi chứng thư hoặc không đăng tải công khai toàn bộ Niên giám 10 năm; ngoài ra một số tỉnh ven biển (Cà Mau, Bạc Liêu, Bến Tre, Trà Vinh) thực tế canh tác lúa Mùa / lúa–tôm chứ **không phải năm nào cũng trồng đủ 3 vụ**.
- **Hướng giải quyết:**
  1. Khẳng định rõ **toàn vùng 13 tỉnh ĐBSCL (2015–2024) là phạm vi chính thức bắt buộc của đồ án (KHÔNG phải phần mở rộng)**; vì giới hạn công bố khách quan của hệ thống thống kê công khai, triển khai **2 tuyến phân tích song hành cùng thuộc phạm vi chính** (đúng Phương án dự phòng đã đăng ký trong `DeTaiPTDL.pdf`):
     - **Tuyến toàn vùng 13 tỉnh ĐBSCL (`tier2_delta13_*`, nguồn NSO):** Đủ **13/13 tỉnh ĐBSCL** suốt 2015–2024 trên vụ **Đông Xuân** (127/130 ô) và cụm **Hè Thu–Thu Đông gộp** (130/130 ô) để đảm bảo phạm vi địa lý toàn ĐBSCL qua cả 3 tiểu vùng sinh thái (thượng nguồn – vùng giữa – ven biển hạn mặn).
     - **Tuyến tách riêng 3 mùa vụ trong vùng ĐBSCL (`tier1_core_3seasons_*`, nguồn Niên giám tỉnh):** Thực hiện phân tích sâu 3 vụ riêng rẽ trên nhóm tỉnh có Niên giám 10 năm chính thức đầy đủ (hiện 90 quan sát sạch tại `An Giang`, `Kiên Giang`, `Cần Thơ` — chiếm **40,5% sản lượng toàn ĐBSCL**; tách bạch hẳn khỏi bảng gộp NSO và sẵn sàng nạp thêm nếu tiếp cận được Niên giám tỉnh khác).
- **Vì sao làm vậy (trả lời hội đồng):** Tuyệt đối **không chia tách nhân tạo** bảng gộp NSO và **không điền 0** cho ô trống. Nếu chia theo tỷ lệ diện tích giả định, giá trị target (`yield_t_ha`) sẽ bị chế tạo từ giả thuyết của người làm, khiến mọi kết quả hồi quy/ML về khác biệt giữa Hè Thu và Thu Đông trở nên vô nghĩa (garbage in, garbage out).

### Vấn đề 2: Chưa có lịch thời vụ xác minh theo tỉnh–năm–vụ (`season_calendar.csv` trống)
- **Thực trạng:** Chưa có ngày bắt đầu/kết thúc thực tế cho từng `(province, year, season)`. `SAGE/Sacks` chỉ là lịch lịch sử cấp vùng Nam Bộ (không có Thu Đông riêng); `RiceAtlas` vướng biểu mẫu guestbook; một PDF lịch Bạc Liêu tải về bị trắng/chỉ có watermark.
- **Hướng giải quyết:**
  1. Xây dựng **bảng lịch thời vụ có phân tầng tin cậy (`calendar_tier`)**:
     - *Tier A (Ưu tiên):* Trích khung lịch gieo sạ–thu hoạch chính thức theo từng tỉnh–vụ từ văn bản khuyến nông/Sở NN&PTNT hoặc báo cáo tiến độ sản xuất (Cục Trồng trọt / Viện KHTL Miền Nam) đã có hoặc bổ sung.
     - *Tier B (Khung thời vụ chuẩn tỉnh/tiểu vùng + Kiểm định độ nhạy):* Nếu thiếu ngày cụ thể theo từng năm, áp dụng khung cửa sổ chuẩn theo tỉnh–vụ (ví dụ Đông Xuân: tháng 11 năm $t-1$ đến tháng 3 năm $t$; Hè Thu: tháng 4–7; Thu Đông: tháng 8–11 theo lịch đặc thù từng tỉnh) **kèm bắt buộc chạy phân tích độ nhạy (sensitivity analysis)** dịch cửa sổ $\pm 10$ và $\pm 15$ ngày để chứng minh kết quả mô hình không phụ thuộc mong manh vào mốc ngày giả định.
  2. Giữ quy tắc: **không ghép và không tổng hợp mưa/nhiệt** cho các dòng chưa được gán `calendar_tier` minh bạch.
- **Vì sao làm vậy:** Năng suất lúa nhạy nhất với thời tiết theo giai đoạn sinh trưởng (nhất là nắng nóng > 35°C lúc trổ bông và mưa cực đoan lúc thu hoạch). Nếu áp 1 lịch tháng cố định cho toàn ĐBSCL mà không kiểm định độ nhạy, mô hình sẽ gán nhầm thời tiết lúc đất trống vào vụ lúa; còn nếu dịch cửa sổ kiểm định độ nhạy, hội đồng thấy rõ mức độ vững (robustness) của kết luận.

### Vấn đề 3: Trùng lặp ô lưới khí tượng MERRA-2 & lưới 30 ô chưa áp mặt nạ
- **Thực trạng (phát hiện qua kiểm chứng thực tế dữ liệu):**
  - 13 tọa độ đại diện tỉnh trong `config/weather_points.json` chỉ rơi vào **10 ô lưới MERRA-2 duy nhất (`0,5° vĩ × 0,625° kinh` ≈ 55 × 68 km)**:
    - `Bến Tre`, `Trà Vinh`, `Vĩnh Long` có chuỗi 6 biến khí tượng MERRA-2 **giống hệt nhau 100%** (cùng ô `200:458`).
    - `Cần Thơ`, `Hậu Giang` có chuỗi 6 biến MERRA-2 **giống hệt nhau 100%** (cùng ô `200:457`).
  - Lưới 30 ô (`config/weather_grid.json`) đã tải đủ nhưng (i) chưa cắt theo ranh giới hành chính tỉnh (còn ô ngoài biển/Campuchia) và (ii) 20 ô bổ sung chỉ có 6 biến, **thiếu `ALLSKY_SFC_SW_DWN`** (bức xạ mặt trời, độ phân giải gốc CERES `1° × 1°`).
- **Hướng giải quyết:**
  1. Ở bước tiền xử lý không gian, dùng shapefile/GeoJSON ranh giới 13 tỉnh ĐBSCL (địa giới trước 2025) để **cắt mặt nạ (mask) các ô biển/ngoài vùng** và tính **trung bình theo diện tích chồng lấp (area-weighted zonal mean)** của các ô lưới phủ từng tỉnh thay vì chỉ lấy 1 tọa độ tâm.
  2. Chạy đối chiếu độ nhạy giữa phương án 1 điểm tỉnh và trung bình đa ô lưới; với 3 tỉnh lõi (`An Giang`, `Kiên Giang`, `Cần Thơ`), cả 3 tỉnh vốn đã nằm ở **3 ô lưới MERRA-2 hoàn toàn tách biệt** (`201:456`, `200:456`, `200:457`), không bị trùng.
  3. Chuẩn hóa bộ biến khí tượng chung trên cả lưới 30 ô (bỏ `ALLSKY_SFC_SW_DWN` khỏi feature bắt buộc hoặc tải bổ sung đồng bộ nếu cần dùng bức xạ) và giữ rõ giới hạn độ phân giải ~55 × 68 km trong phần hạn chế nghiên cứu.
- **Vì sao làm vậy:** Dùng 1 điểm/tỉnh cho các tỉnh diện tích nhỏ dẫn đến đa cộng tuyến hoàn hảo (duplicate weather features) giữa các tỉnh chung ô lưới. Dùng lưới 30 ô nhưng không áp mặt nạ sẽ kéo thời tiết biển vào đất liền; ngược lại, tuyệt đối không dùng 30 ô để nhân bản thành 30 mẫu năng suất vì nhãn năng suất chỉ có ở cấp tỉnh.

### Vấn đề 4: Xung đột phiên bản nguồn, chuẩn hóa đơn vị & Domain Outliers (Hạn mặn)
- **Thực trạng:**
  - Số liệu năm cuối mỗi Niên giám NSO (2019 trong NGTK 2019; 2024 trong NGTK 2024) mang nhãn **Sơ bộ**; 3 bản ghi Thu Đông Tiền Giang trích từ báo cáo năm (bản 2022 tính đến 15/12/2022) có thể chênh nhẹ so với Niên giám chính thức.
  - Đơn vị và dấu phân cách khác nhau: NSO dùng `nghìn ha`, `tạ/ha`, `nghìn tấn`; Niên giám tỉnh dùng `ha`, `tạ/ha`, `tấn`; PDF dùng dấu `.` ngăn cách hàng nghìn và dấu `,` thập phân.
  - Kiểm tra công thức `Diện tích × Năng suất vs Sản lượng` trên 467 dòng NSO phát hiện 7 dòng có sai số tương đối 1,01%–6,00%, cao nhất là **Bến Tre Đông Xuân 2016 (5,63%; năng suất 0,5 tạ/ha)** và **2020 (6,00%; năng suất 0,4 tạ/ha)**.
- **Hướng giải quyết:**
  1. Thiết lập **Thang ưu tiên nguồn (Source Precedence)** rõ ràng khi hợp nhất: `Niên giám tỉnh chính thức > Niên giám NSO chính thức > Niên giám sơ bộ > Báo cáo năm cấp tỉnh`. Giữ toàn bộ bản ghi gốc và ghi bảng quyết định chọn phiên bản (`reconciliation_log.csv`).
  2. Quy đổi thống nhất về `ha`, `tấn/ha`, `tấn`; lưu song song đơn vị gốc và nguồn.
  3. **Điều chỉnh quy tắc kiểm tra sản lượng:** Không dùng cứng ngưỡng sai số tương đối 1% để loại dòng. Kết hợp ngưỡng tương đối 1% với **ngưỡng làm tròn tuyệt đối** (vì NSO làm tròn đến 0,1 nghìn tấn, khi sản lượng chỉ `0,2–0,8 nghìn tấn`, sai số làm tròn tự nhiên đã là 6%–25%).
  4. **Giữ lại điểm ngoại lai Bến Tre 2016 & 2020** trong tập phân tích (không xóa nhầm như lỗi nhập liệu), gắn cờ sự kiện cực đoan (hạn mặn lịch sử 2015–2016 và 2019–2020) để phân tích riêng độ nhạy mô hình (có/không có điểm cực đoan mặn).
- **Vì sao làm vậy:** Nếu lọc mù theo ngưỡng 1% hoặc loại outlier tự động sẽ xóa mất chính những năm thiên tai nghiêm trọng nhất của ĐBSCL — làm mô hình đánh giá thấp rủi ro thực tế và sai lệch bản chất bài toán.

### Vấn đề 5: Quy mô mẫu vừa phải, thiếu biến phi khí tượng & ranh giới diễn giải
- **Thực trạng:** Sau khi giữ nguyên tắc không chế biến dữ liệu, tuyến tách riêng 3 vụ hiện có 90 quan sát sạch ở 3 tỉnh trọng điểm (và tuyến toàn vùng 13 tỉnh ĐBSCL có 127 dòng Đông Xuân + 130 dòng cụm Hè Thu–Thu Đông). Ngoài ra, dữ liệu chỉ có khí tượng (nhiệt, mưa, ẩm, gió), chưa có độ mặn, mực nước lũ, giống lúa, phân bón.
- **Hướng giải quyết:**
  1. **Tách tập theo thời gian tăng dần** (ví dụ Train 2015–2020, Validation 2021–2022, Test 2023–2024), tuyệt đối không random split để tránh rò rỉ tương lai.
  2. **So sánh nghiêm ngặt với Baseline** (trung vị theo `province × season`), ưu tiên mô hình ít tham số (**Linear / Ridge Regression** có regularize) trước khi thử Random Forest để tránh overfitting trên mẫu nhỏ; kiểm định giá trị gia tăng của khí tượng bằng cách so sánh mô hình **chỉ có `(tỉnh, vụ, năm)`** vs **có thêm khí tượng**.
  3. Giới hạn rõ phạm vi phát biểu: kết quả khí tượng toàn vụ là **ước lượng hồi cứu (retrospective association)**, không tuyên bố dự báo sớm trước thu hoạch hay quan hệ nhân quả tuyệt đối.
- **Vì sao làm vậy:** Trong phân tích dữ liệu khoa học, 90–180 dòng sạch, truy xuất được từng trang PDF và đánh giá không leakage có giá trị học thuật cao hơn nhiều so với 390 dòng chắp vá bằng số liệu suy diễn.

---

## 4. Bộ Câu hỏi Phản biện Hội đồng (Q&A thực chiến)

### Q1. "Đề xuất ghi 13 tỉnh × 10 năm × 3 vụ = 390 dòng, sao hiện mới thu được 190 ô và chỉ 3 tỉnh đủ 3 vụ?"
> **Trả lời:** Trong phiếu đăng ký đề tài (`DeTaiPTDL.pdf`), **toàn vùng 13 tỉnh ĐBSCL là phạm vi chính thức phải thực hiện**, còn 390 là **trần lý thuyết của lưới kiểm kê**, không phải số mẫu đã tồn tại. Thực tế kiểm kê cho thấy: (1) Niên giám NSO quốc gia phủ đủ 13/13 tỉnh nhưng công bố gộp `Hè Thu–Thu Đông`; (2) Một số tỉnh ven biển không trồng đủ 3 vụ hằng năm (trồng lúa Mùa/lúa–tôm); (3) Chỉ 3/13 cổng tỉnh mở công khai PDF Niên giám 10 năm đầy đủ. Do đó, nhóm thực hiện **2 tuyến phân tích song hành cùng thuộc phạm vi chính của đồ án** (không coi 13 tỉnh là phần mở rộng): (i) **Toàn vùng 13/13 tỉnh ĐBSCL** trên số liệu NSO Đông Xuân (127 dòng) + cụm Hè Thu–Thu Đông (130 dòng) để phủ trọn không gian toàn đồng bằng, và (ii) **Tách riêng 3 mùa vụ** trên 3 tỉnh trọng điểm có Niên giám chính thức đầy đủ (`An Giang`, `Kiên Giang`, `Cần Thơ` — 90 dòng, chiếm **40,5% sản lượng toàn ĐBSCL**, khớp < 0,5% với NSO) đúng theo Phương án dự phòng đã đăng ký trong đề cương.

### Q2. "Sao không tách bảng gộp Hè Thu–Thu Đông của NSO theo tỷ lệ để có đủ 390 dòng cho mô hình mạnh hơn?"
> **Trả lời:** Vì làm vậy sẽ **tạo dữ liệu giả cho biến mục tiêu (target fabrication)**. Năng suất Hè Thu và Thu Đông chịu hai chế độ thời tiết khác nhau (đầu mùa mưa vs đỉnh mưa–lũ cuối vụ). Nếu chia đều hoặc chia theo tỷ lệ ước đoán, mô hình sẽ học đúng giả định chia của người làm chứ không học quy luật tự nhiên.

### Q3. "Tại sao phải cào tới 998 tệp (~1 GB) mà chỉ trích ra vài trăm dòng bảng?"
> **Trả lời:** Vì nguồn thống kê nông nghiệp Việt Nam phân tán trên nhiều cổng tỉnh với cấu trúc web, PDF và tệp đính kèm khác nhau. Cào rộng theo seed có mục tiêu giúp **kiểm chứng có hệ thống** nơi nào có/không có số liệu (đặc biệt để chứng minh khoảng trống là do nguồn không công bố, không phải do tìm qua loa), đồng thời lưu trọn vết kiểm toán (URL, SHA-256, trang PDF) để mọi con số trong bảng đều tái lập được 100%.

### Q4. "Tại sao dùng NASA POWER lưới thô (~55 × 68 km) thay vì trạm khí tượng KTTV? Lại còn bị trùng ô giữa Bến Tre–Trà Vinh–Vĩnh Long và Cần Thơ–Hậu Giang?"
> **Trả lời:** Dữ liệu trạm KTTV Việt Nam theo ngày giai đoạn 2014–2024 không mở công khai miễn phí ở quy mô 13 tỉnh. NASA POWER (MERRA-2) là nguồn chuẩn quốc tế miễn phí, liên tục 100% ngày (0 giá trị thiếu trong 4.018 ngày) và tái lập được qua API. Nhóm **đã tự phát hiện** việc 13 điểm tỉnh bị gộp về 10 ô lưới MERRA-2 nên đã tải thêm toàn bộ lưới 30 ô phủ ĐBSCL để tính trung bình theo đa giác tỉnh (sau khi cắt mặt nạ biển) và kiểm định độ nhạy, đồng thời khai báo minh bạch giới hạn độ phân giải không gian. Riêng 3 tỉnh lõi (An Giang, Kiên Giang, Cần Thơ) nằm trên **3 ô lưới độc lập hoàn toàn**.

### Q5. "Chưa có ngày xuống giống/thu hoạch chính xác từng tỉnh từng năm thì ghép khí tượng có bị lệch không?"
> **Trả lời:** Có rủi ro lệch pha nếu chỉ ghép theo tháng cố định toàn vùng. Vì vậy nhóm **tạm khóa bước ghép** cho đến khi chốt được lịch thời vụ theo từng tỉnh–vụ từ tài liệu khuyến nông/báo cáo sản xuất địa phương, lấy khí tượng từ năm 2014 để bao phủ đúng vụ Đông Xuân vắt năm, và **bắt buộc kiểm định độ nhạy dịch cửa sổ ±10–15 ngày** để chứng minh kết luận ổn định trước sai số lịch thời vụ.

### Q6. "Dữ liệu NSO có vài dòng (như Bến Tre Đông Xuân 2016, 2020) sai số tích diện tích × năng suất lên tới 6%, lại có năng suất chỉ 0,04–0,05 tấn/ha. Có phải lỗi trích xuất PDF?"
> **Trả lời:** Không phải lỗi trích xuất. Nhóm đã kiểm tra đối chiếu trực tiếp: (1) Năm 2015–2016 và 2019–2020 là hai đợt **hạn mặn lịch sử ĐBSCL** khiến lúa Đông Xuân Bến Tre mất trắng (năng suất tính trên diện tích gieo trồng tụt xuống 0,4–0,5 tạ/ha); (2) Do NSO làm tròn sản lượng đến `0,1 nghìn tấn`, khi sản lượng chỉ còn `0,2–0,8 nghìn tấn`, sai số làm tròn tự nhiên đã là 6%–25%. Đây là bằng chứng vì sao không được xóa outlier một cách máy móc.

### Q7. "Năng suất lúa ĐBSCL phụ thuộc cả giống, phân bón, thủy lợi, xâm nhập mặn; chỉ ghép khí tượng thì mô hình giải thích được bao nhiêu?"
> **Trả lời:** Chính vì vậy đề tài thiết kế theo hướng **định lượng giá trị đóng góp biên của khí tượng** (so sánh mô hình có vs không có khí tượng so với baseline tỉnh–vụ) và phát biểu kết quả ở mức **liên hệ hồi cứu**, không gán nhân quả tuyệt đối. Các biến không quan sát được như hạ tầng thủy lợi hay trình độ canh tác đặc thù từng tỉnh phần nào được hấp thụ qua biến phân loại `province` và `season`, còn phần dư lớn ở các năm hạn mặn ven biển sẽ được chỉ rõ là giới hạn của nhóm biến khí tượng thuần.

---

## 5. Trạng thái hoàn thành bước Cào & Bước tiếp theo (Làm sạch → Ghép nối)

- **Đã hoàn tất & kiểm chứng tự động ở bước Cào (`node scripts/verify_raw_handoff.mjs` = PASS):**
  1. Khóa phạm vi 2 tầng (`An Giang`, `Kiên Giang`, `Cần Thơ` = 90 dòng lõi 3 vụ; 13 tỉnh NSO = Đông Xuân 127 dòng + gộp 130 dòng) và bổ sung `nso_rice_2021_reconciliation.csv` (25/47 dòng 2019 chính thức có điều chỉnh so với sơ bộ).
  2. Thu thập & trích `data/raw/season_calendar_raw.csv` (17 bản ghi từ 9 văn bản `.gov.vn`, đủ khung 3 vụ Cục Trồng trọt).
  3. Tải `data/raw/geo/gadm41_VNM_1.json` (13/13 tỉnh ĐBSCL) và tạo `data/catalog/weather_grid_province_overlap.csv` (loại 9 ô biển, tạo 13/13 hồ sơ trọng số không gian tách biệt).
  4. Chốt 6 biến khí tượng chung toàn lưới 30 ô (`T2M`, `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, `RH2M`, `WS2M`).
- **Bước kế tiếp (Giai đoạn Làm sạch & Tiền xử lý — `data/interim/` & `data/processed/`):**
  1. Chuẩn hóa bảng lúa (`reconciliation` 2019 chính thức, quy đổi đơn vị, giữ cờ hạn mặn Bến Tre 2016/2020).
  2. Tính chuỗi khí tượng ngày trung bình có trọng số diện tích cho 13 tỉnh từ `weather_daily_raw.csv` × `weather_grid_province_overlap.csv`.
  3. Dựng bảng `season_calendar_clean.csv` từ `season_calendar_raw.csv` và chạy tổng hợp đặc trưng + kiểm định độ nhạy dịch cửa sổ `±10` và `±15` ngày trước khi xuất bộ dữ liệu huấn luyện.
