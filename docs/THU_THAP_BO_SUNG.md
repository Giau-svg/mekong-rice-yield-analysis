# Rà soát thu thập bổ sung — 20/11/2026

## Kết quả thực tế

- Kho nguồn: 998 tệp, 994 nội dung khác nhau theo SHA-256; 135 nội dung PDF.
- Chỉ mục PDF: 20087 trang. Chỉ mục HTML: 657 tài liệu.
- OCR đã thực hiện: 5 tài liệu / 50 trang; kết quả máy đọc giữ riêng, không tự xem là số liệu đã xác minh.
- Khí tượng: 132594 dòng điểm–ngày; chưa ghép mùa vụ, chưa áp mặt nạ địa giới hoặc trọng số diện tích lúa.
- Bảng lúa tách vụ: 190 tổ hợp có giá trị nguồn trong 390 tổ hợp tham chiếu. Có 220 dòng nguồn, bao gồm các phiên bản/phạm vi trùng.
- 200 tổ hợp chưa đủ bằng chứng số liệu tách vụ. Không điền 0, không chia bảng gộp thành hai vụ.
- Hàng đợi của lượt cào này còn 0 URL. Hết hàng đợi chỉ nghĩa là đã xử lý liên kết được phát hiện trong phạm vi lượt chạy, không chứng minh Internet không còn nguồn khác.

## Kỹ thuật đã sử dụng

1. Rà soát có hệ thống 100 truy vấn theo tỉnh–năm; lưu 25 phản hồi tìm kiếm tại 'data/raw/search_discovery/systematic_*.txt' và toàn bộ truy vấn tại 'config/gap_search_queries.json'.
2. Theo liên kết lưu trữ, phân trang, tệp đính kèm và các payload bài viết công khai; tải nguyên byte bằng curl, giới hạn đồng thời và khoảng nghỉ giữa yêu cầu; hỗ trợ tải tiếp PDF dở dang.
3. Kiểm tra chữ ký PDF/ZIP, kết thúc PDF, URL đích, dung lượng và SHA-256; giữ các phản hồi đăng nhập hoặc xem trước với trạng thái riêng.
4. Trích văn bản PDF, OCR ảnh và phân tích DOM HTML. Bảng thu thập giữ chuỗi số, đơn vị, nguồn và vị trí trích.
5. Đối chiếu hình trang cho các cột bị bỏ trống ở Cà Mau, Đông Xuân 2015–2019: hai giá trị thuộc 2017 và 2019; các ô trống khác không suy diễn.
6. Ghi lại liên kết ngoài phạm vi tại 'data/catalog/discovery_scope_exclusions.jsonl'; giữ tệp đã tải để truy xuất nguồn. Đây là sàng lọc nguồn thu thập, không phải làm sạch số liệu.

## Những giới hạn còn lại

- NSO toàn quốc cung cấp Hè Thu–Thu Đông gộp. Bảng này có giá trị tham khảo, nhưng không đủ để xác lập từng vụ riêng.
- Một số cổng cũ không còn DNS, lỗi chứng thư hoặc lỗi máy chủ. Chi tiết từng URL nằm trong 'data/catalog/unavailable_sources.csv'.
- Có nguồn thư viện yêu cầu đăng nhập hoặc chỉ cung cấp bản xem trước; không tính chúng là tài liệu đầy đủ.
- RiceAtlas: đã thu metadata qua API Harvard Dataverse; tải tệp yêu cầu phản hồi guestbook ID 40. Chưa gửi biểu mẫu danh tính; xem 'data/catalog/riceatlas_access_status.json'.
- RICA: API Figshare trả metadata phiên bản 1 còn hạn chế tệp; chưa thu được phiên bản 2. Không xem metadata là dữ liệu lịch đã tải.
- Đã tải dữ liệu và tài liệu mô tả SAGE; có 5 dòng tham chiếu lúa Việt Nam. Đây là lịch lịch sử, không thay cho lịch thực tế từng tỉnh–năm.
- PDF kế hoạch 200/KH-UBND Bạc Liêu có các trang kiểm tra hiển thị trống hoặc chỉ watermark. Đã lưu nhận xét, chưa dùng làm lịch xác minh. Nguồn HTML thay thế bị HTTP 403 ở lần tải này.

## Tệp bàn giao

| Tệp | Ý nghĩa |
|---|---|
| 'data/raw/rice_captured_main_seasons.csv' | 90 dòng ba vụ riêng của An Giang, Kiên Giang, Cần Thơ |
| 'data/raw/nso_rice_province_tables.csv' | 467 dòng NSO, bao gồm cả năm, Đông Xuân, vụ gộp và mùa |
| 'data/raw/rice_report_season_values.csv' | 3 dòng Thu Đông Tiền Giang 2021, 2022, 2024; giữ ghi chú thời điểm báo cáo |
| 'data/catalog/rice_collection_coverage.csv' | 390 tổ hợp kiểm kê cùng nguồn đối chiếu |
| 'data/catalog/rice_collection_gaps.csv' | 200 tổ hợp cần bổ sung hoặc xác minh |
| 'data/catalog/source_catalog.csv' | Danh mục tệp, URL, hash, trạng thái vận chuyển và nhận xét nội dung |
| 'data/raw/pdf_text/', 'data/raw/ocr_text/', 'data/raw/html_text/' | Bản trích máy để tiếp tục tìm bảng và kiểm tra nguồn |

**Kết luận:** đã hoàn tất hàng đợi của đợt cào bổ sung; chưa hoàn thành mục tiêu đủ ba vụ tách riêng cho 13 tỉnh trong 2015–2024. Chưa làm sạch, quy đổi đơn vị, điền thiếu, chọn bản điều chỉnh, ghép thời tiết hay huấn luyện mô hình.
