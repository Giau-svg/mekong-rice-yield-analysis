# Phân tích mối liên hệ giữa khí tượng và năng suất lúa ở Đồng bằng sông Cửu Long theo ba mùa vụ (2015–2024)

**Đồ án môn học Phân tích Dữ liệu — Khoa CNTT, Trường Đại học Sài Gòn (CBGD: Phan Thành Huấn)**  
**Sinh viên thực hiện:** Lê Thị Ngọc Giàu (`3123410088`) · Trần Ngọc An (`3123410004`)

---

## 1. Phạm vi chính thức & Thiết kế dữ liệu
- **Phạm vi (`DeTaiPTDL.pdf`):** Toàn vùng **13/13 tỉnh ĐBSCL** theo địa giới trước 2025, giai đoạn **2015–2024**, tổ chức qua **2 tuyến phân tích song hành cùng thuộc phạm vi chính**:
  - **Tuyến A (Toàn vùng 13 tỉnh):** Đông Xuân (`127` dòng) và cụm Hè Thu–Thu Đông (`130` dòng), tổng `257` dòng từ NSO (đã nâng cấp số liệu 2019 chính thức) ghép khí tượng trọng số diện tích GADM v4.1 (21 ô lưới đất liền NASA POWER MERRA-2) và chỉ số ENSO (NOAA PSL ONI).
  - **Tuyến B (Tách riêng 3 mùa vụ):** `An Giang`, `Kiên Giang`, `Cần Thơ` (`90` dòng cân bằng `3 tỉnh × 10 năm × 3 vụ`, chiếm **40,5% sản lượng lúa toàn ĐBSCL**) + `7` bản ghi ngoại kiểm địa lý OOD (`Tiền Giang`, `Vĩnh Long`, `Cà Mau`).
- **Chống rò rỉ dữ liệu (Anti-Leakage):** Chia tập theo thời gian tăng dần (`train 2015–2020`, `val 2021–2022` / `Expanding-Window CV 2019–2022`, khóa kín `test 2023–2024`); tuyệt đối không đưa `area_ha` và `production_t` vào đầu vào dự báo năng suất.

## 2. Cấu trúc thư mục dự án
```text
mekong-rice-yield-analysis/
├── DeTaiPTDL.pdf                                 # Phiếu đăng ký đề tài chính thức
├── data/
│   ├── raw/                                      # Dữ liệu gốc bất biến + SHA-256 catalog
│   ├── interim/                                  # Bảng trung gian, log đối soát & lịch thời vụ
│   └── processed/                                # 5 bảng sạch sẵn sàng phân tích & kiểm định độ nhạy
├── scripts/
│   ├── collect_all_raw.ps1                       # Thu thập dữ liệu gốc đa nguồn
│   ├── run_cleaning_pipeline.ps1                 # Pipeline làm sạch 5 bước & tự động verify PASS
│   ├── run_eda_and_modeling.py                   # EDA, VIF, 20 mô hình hồi quy, Độ nhạy & OOD (Hình 01–06)
│   ├── run_statistical_and_datamining_suite.py   # Ngoại lệ 3σ, GĐ1–GĐ4 OLS, Stepwise, Phân lớp 10 mô hình,
│   │                                             # Gom cụm 9 thuật toán, Luật kết hợp Apriori (Hình 07–10)
│   └── build_dashboard.py                        # Sinh Dashboard tương tác offline từ dữ liệu & trọng số thật
├── dashboard/
│   └── index.html                                # Dashboard tương tác 5 tab (chạy offline trên trình duyệt)
├── notebooks/
│   └── Mekong_Rice_Yield_Full_Analysis.ipynb     # Notebook tổng hợp toàn bộ quy trình KDD
├── slide/
│   ├── SLIDE_BAO_CAO_DO_AN_SGU.html              # Bộ 18 slide trình chiếu 16:9 (tích hợp đủ 10 biểu đồ)
│   ├── SLIDE_THUYET_TRINH_DO_AN.md               # Kịch bản thuyết trình chi tiết (15% điểm)
│   └── BO_CAU_HOI_VA_PHAN_BIEN_VAN_DAP.md        # Bộ 20 câu hỏi & đáp án vấn đáp (5% điểm)
├── results/
│   ├── figures/                                  # 10 biểu đồ PNG 300 DPI
│   └── metrics/                                  # 22 bảng kết quả CSV/JSON & luật cây quyết định
└── docs/
    ├── PHAN_BIEN_THU_THAP_VA_GHEP_NOI.md         # Phản biện logic thu thập & ghép nối đa nguồn
    ├── QUYET_DINH_LAM_SACH.md                    # 6 quyết định nghiệp vụ – kỹ thuật làm sạch
    ├── DATA_DICTIONARY.md                        # Từ điển dữ liệu đầy đủ
    └── BAO_CAO_PHAN_TICH_VA_MO_HINH.md           # Báo cáo phân tích, kiểm định & so sánh đa mô hình
```

## 3. Hướng dẫn tái lập 100% (Offline, không cần mạng)
Yêu cầu: Node.js 18+ (cho bước làm sạch) và Python 3.10+ (`numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`, `seaborn`).

```powershell
# Bước 1: Tái tạo & kiểm định toàn bộ dữ liệu sạch (PASS gate)
powershell -ExecutionPolicy Bypass -File scripts/run_cleaning_pipeline.ps1

# Bước 2: Chạy EDA, VIF, 20 mô hình hồi quy đa hình thái, Độ nhạy & Ngoại kiểm OOD (Hình 01–06)
python scripts/run_eda_and_modeling.py

# Bước 3: Chạy Ngoại lệ 3σ, Kiểm định GĐ1–GĐ4 OLS, Chọn biến, Phân lớp (10 mô hình),
#         Gom cụm 13 tỉnh (9 thuật toán + Dendrogram) & Luật kết hợp Apriori (Hình 07–10)
python scripts/run_statistical_and_datamining_suite.py

# Bước 4: Tái tạo Dashboard trực quan tương tác offline (dashboard/index.html)
python scripts/build_dashboard.py
```

## 4. Tóm tắt kết quả nổi bật
- **Tiền xử lý & Kiểm định GĐ1–GĐ4 (Buổi 02–04):** Kiểm định $3\sigma$ phát hiện chính xác 3 sự kiện hạn mặn lịch sử ĐX (`Bến Tre 2016/2020`, `Cà Mau 2017`) → Shapiro-Wilk bác bỏ phân phối chuẩn ($p < 10^{-10}$) và White test phát hiện phương sai thay đổi ở cụm HT–TĐ ($p = 0{,}033$), cung cấp bằng chứng toán học cho việc chọn **Huber Loss**, **HC3 SE** và **Dual-Regime Evaluation**; VIF giảm từ `53,47 → 2,72`.
- **Hồi quy đa hình thái (20 mô hình):** Trên Tuyến B (`n=90`), **`Huber_Anomaly_Ortho5_Trend`** tốt nhất trên Expanding-CV (`0,1771` vs Baseline `0,2624`, `-32,5%`) và **`Ridge/Lasso + Trend`** đạt Test MAE `0,1369–0,1374` ($R^2 = 0{,}954$, giảm `-54%` so với Baseline `0,3002`), vượt trội `OLS thuần`, `Decision Tree`, `Random Forest`, `GBR`, `SVR-RBF` (overfit `0,3372`) và `MLP-ReLU`. Trên Tuyến A 13 tỉnh ĐX, **`Huber`** đứng đầu tuyệt đối ở cả 2 chế độ (`0,4482` full; `0,3519` ex-salinity).
- **Phân lớp 3 hạng năng suất (10 hình thái, `n=257`):** **`SVM_RBF`** đạt Test Acc `86,5%`, Macro-F1 `0,872`, AUC `0,949`; **`Logistic_OvR`** đạt Macro-F1 `0,836`, AUC `0,958`; **`SVM_Linear`** đạt AUC cao nhất `0,967` (chỉ dùng khí tượng + tiểu vùng vẫn đạt Test F1 `0,734`, AUC `0,916`).
- **Gom cụm 13 tỉnh (9 thuật toán):** 5 thuật toán (`K-Means`, `K-Medoids PAM`, `Agglomerative Ward/Complete`, `Bisecting K-Means`) đồng thuận 100% (`Relative Rand = 1,000`, `Silhouette = 0,390`) tách riêng 3 tỉnh ven biển rủi ro mặn cực đoan (`Bến Tre`, `Cà Mau`, `Trà Vinh`); riêng `DBSCAN` tự gắn nhãn `Bến Tre` là điểm nhiễu `-1`.
- **Luật kết hợp Apriori:** Phát hiện quy luật mạnh `IF MưaTiềnVụ=Cao AND Vùng=ThượngNguồn → NăngSuấtĐX=Cao (Conf=1,00, Lift=3,02)` và `IF Vùng=VenBiển AND MưaTiềnVụ=TB → NăngSuấtĐX=Thấp (Conf=0,69, Lift=2,03)`.

Chi tiết đầy đủ xem tại [BAO_CAO_PHAN_TICH_VA_MO_HINH.md](docs/BAO_CAO_PHAN_TICH_VA_MO_HINH.md), [QUYET_DINH_LAM_SACH.md](docs/QUYET_DINH_LAM_SACH.md) và [PHAN_BIEN_THU_THAP_VA_GHEP_NOI.md](docs/PHAN_BIEN_THU_THAP_VA_GHEP_NOI.md).
