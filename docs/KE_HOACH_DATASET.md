# Kế hoạch dataset theo đề tài

Đọc từ DeTaiPTDL.pdf (2 trang). Câu hỏi: so sánh năng suất ba vụ; liên hệ nhiệt độ, mưa, ẩm với năng suất; khác biệt giữa vụ; so sánh mô hình với baseline. Dữ liệu 2015–2024, tối đa 13 tỉnh theo địa giới trước 2025. 390 là số ô kiểm kê lý thuyết, không phải số quan sát đã có. Các mẫu 65 dòng được nhắc trong PDF không có file kèm thư mục nên chưa coi là đã thu thập.

## Quyết định để có kết quả đáng tin cậy

1. Ưu tiên nhãn năng suất chính thức và ba vụ riêng; chấp nhận thu hẹp tỉnh/năm. Không tự tách số liệu gộp và không thay dữ liệu thiếu bằng 0.
2. Mỗi dòng khóa tỉnh + năm thu hoạch + vụ. Giữ tên vụ nguyên văn, trạng thái chính thức/sơ bộ, URL, vị trí đoạn/bảng, đơn vị gốc. Khi có nguồn mới mâu thuẫn, giữ cả bản gốc và ghi quyết định chọn phiên bản.
3. Tiền Giang 2024: Đông Xuân 7,02; Hè Thu 5,75; Thu Đông 5,60 tấn/ha. Hè Thu bao gồm Xuân Hè nên chưa đạt định nghĩa vụ riêng. Không suy ra năng suất Hè Thu từ tỷ lệ diện tích.
4. Lịch mùa vụ phải theo tỉnh, năm và phạm vi vụ, có nguồn. Đông Xuân có thể bắt đầu năm trước; cần khí tượng từ 2014 cho nhãn thu hoạch 2015. Không áp lịch tháng chung toàn vùng.
5. Điểm NASA (10,45; 106,35) chỉ kiểm chứng pipeline. Sau khi có phạm vi trồng lúa, lấy các ô lưới phủ vùng canh tác và đánh giá độ nhạy với nhiều điểm; tránh tải lặp cùng ô. LST là giờ mặt trời địa phương, không đồng nhất UTC+7.
6. Chỉ tổng hợp khi lịch đã xác minh, đủ ngày và biến hợp lệ. Đặc trưng: T2M trung bình, T2M_MAX lớn nhất/trung bình, tổng PRECTOTCORR, RH2M trung bình, số ngày T2M_MAX >35°C, số ngày mưa <1 mm. Ngưỡng khô là định nghĩa vận hành, cần phân tích độ nhạy. Không tổng mưa khi còn ngày thiếu.

## Thứ tự mở rộng thu thập

- Kiểm kê niên giám NSO 2024 bảng 213–224 cho dữ liệu nền; các bảng gộp Hè Thu–Thu Đông chỉ dùng đối chiếu.
- Tìm báo cáo KT-XH năm và niên giám từng tỉnh, ưu tiên Tiền Giang, Đồng Tháp, An Giang, Cần Thơ, Kiên Giang; lùi 2023 về 2015. Đây là thứ tự khảo sát, chưa phải cam kết nguồn đủ.
- Dùng coverage_inventory.csv theo dõi toàn bộ 390 ô: not_collected khác missing trong nguồn và khác not_planted. Chỉ chuyển trạng thái sau kiểm tra nguồn.
- Với mỗi ô thu được, kiểm chứng lịch xuống giống/thu hoạch từ báo cáo nông nghiệp địa phương. Số liệu gieo trồng và thu hoạch phải cùng mẫu số khi kiểm tra sản lượng.
- Khi có ít nhất nhiều năm liên tiếp và ba vụ đủ tin cậy, chốt phạm vi thực tế; không tăng số dòng bằng nội suy target.

## Thiết kế phân tích sau thu thập

EDA theo tỉnh/vụ/năm, missing và outlier; đối chiếu diện tích × năng suất với sản lượng, dung sai ban đầu 1% chỉ dùng cảnh báo (không tự sửa). Tách dữ liệu theo năm thu hoạch, dự kiến train 2015–2020, validation 2021–2022, test 2023–2024 nếu độ phủ cho phép. Chốt mốc trước khi xem metric test. Baseline trung vị tỉnh–vụ, fallback vụ rồi toàn train. Ridge/Linear trước, Random Forest khi đủ mẫu; tiền xử lý chỉ fit train. Báo cáo MAE chính, RMSE/R² phụ và sai số từng vụ/tỉnh; so sánh mô hình có và không có khí tượng để đánh giá giá trị bổ sung. Dữ liệu khí tượng toàn vụ chỉ hỗ trợ hồi cứu; không kết luận nhân quả hoặc cảnh báo sớm. Không dùng sản lượng hay năng suất suy từ sản lượng làm feature.

## Nguồn đã xác minh trực tuyến

- Báo cáo Tiền Giang, công bố 03/01/2025: https://thongkedongthap.nso.gov.vn/tin-tuc/140
- NASA POWER Daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- NSO có các bảng vụ gộp: https://www.nso.gov.vn/so-lieu-thong-ke/

Chưa có lịch vụ được kiểm chứng; chưa tạo tập ghép dùng huấn luyện. Không thể kết luận mô hình nào tốt nhất ở thời điểm này.
