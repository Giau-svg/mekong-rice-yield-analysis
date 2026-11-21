# Thu thập dữ liệu thô từ nhiều nguồn

Phạm vi chính: lúa 13 tỉnh ĐBSCL theo địa giới trước 2025, năm thu hoạch 2015–2024; khí tượng từ 2014 để bao phủ vụ Đông Xuân qua năm. Đợt này chỉ thu thập, lưu nguyên bản và lập danh mục nguồn. Làm sạch và ghép bảng thực hiện ở giai đoạn xử lý.

## Kỹ thuật đã áp dụng

1. Tìm kiếm có mục tiêu theo tỉnh, năm, mùa vụ và loại tài liệu; khám phá đường dẫn trên trang niên giám/báo cáo.
2. Cào HTTP các trang HTML và tải PDF, Excel, JSON; đọc payload công khai của trang dùng JavaScript để tìm tệp đính kèm. Không cần đăng nhập.
3. Gọi NASA POWER Daily API, lưu phản hồi JSON nguyên bản cùng URL tham số. Tải liên tiếp với khoảng nghỉ, giới hạn số luồng; dùng cache và tải tiếp tệp dở.
4. Giữ bản gốc; ghi URL, thời điểm tải, SHA-256, trang dẫn đến tài liệu; ghi cả URL thất bại. Mã băm trùng chỉ giúp nhận diện bản sao, không xóa dữ liệu gốc.
5. Kiểm tra vận chuyển: mã HTTP, dung lượng, chữ ký PDF/ZIP, dấu kết thúc PDF, tính đọc được của JSON và số ngày. Đây chưa phải làm sạch dữ liệu thống kê hoặc xác minh từng con số.

## Kết hợp nguồn có căn cứ

| Nhóm | Vai trò | Điều kiện khi xử lý sau |
|---|---|---|
| NSO, thống kê tỉnh, niên giám | Số liệu diện tích, năng suất, sản lượng; nguồn ưu tiên | Xác minh năm, tỉnh, định nghĩa vụ, đơn vị và phiên bản |
| UBND, cơ quan nông nghiệp, bản lưu trên Bộ KHĐT | Bổ sung vụ tách riêng và lịch sản xuất | Ghi rõ sơ bộ/ước/chính thức; bản lưu lại không phải nguồn độc lập |
| Viện nghiên cứu, báo cáo thị trường nông sản | Tiến độ sản xuất, thời vụ, nguồn bổ sung | Truy ngược cơ quan cung cấp; phân biệt dự báo, kế hoạch và kết quả |
| Báo địa phương có dẫn cơ quan nông nghiệp | Bổ sung khoảng trống và bối cảnh | Không dùng mẫu hộ/huyện hay phần mới thu hoạch đại diện toàn tỉnh |
| NASA POWER | Khí tượng ngày | Dữ liệu lưới, không phải trạm quan trắc thực địa; ghép theo lịch vụ sau |

Nhiều trang đăng lại cùng một báo cáo không tạo thêm quan sát độc lập. Một tỉnh có thể có vụ lúa Mùa, lúa–tôm hoặc không canh tác một vụ; không ép mọi tỉnh/năm có đúng ba vụ. Danh sách 390 ô là khung khảo sát, không phải quota phải điền bằng suy đoán.

## Quy tắc suy luận ở bước xử lý sau

- Có thể tính năng suất = sản lượng / diện tích thu hoạch khi cả hai cùng tỉnh, năm, vụ, phạm vi và đơn vị; lưu nhãn `derived`, công thức và hai nguồn đầu vào. Không dùng diện tích gieo trồng thay diện tích thu hoạch khi hai diện tích khác nhau.
- Chỉ suy ra một thành phần từ tổng và các thành phần còn lại nếu chứng minh chúng cùng kỳ, cùng phạm vi, bao phủ đầy đủ, không chồng lặp và cùng phiên bản. Nếu chưa đủ điều kiện, giữ số liệu gộp.
- Không chia đều năng suất của vụ gộp, không trung bình năng suất không trọng số, không gán thiếu bằng 0. Không dùng tỷ lệ tăng giảm đã làm tròn để tạo nhãn “chính thức” cho năm trước.
- Giữ nguyên mọi con số mâu thuẫn trong raw. Quyết định dùng phiên bản nào cần được ghi trong bảng xử lý riêng.
- Không lấy kết quả mô hình điền vào target rồi báo cáo như số liệu thu thập thực tế.

## Khí tượng nhiều điểm

Đã thiết kế lưới 0,5° vĩ × 0,625° kinh theo độ phân giải khí tượng NASA POWER, trong khung 8,5–11°B và 104,375–106,875°Đ (30 ô). Tái sử dụng phản hồi điểm đã có nằm trong cùng ô theo ánh xạ gần nhất trên lưới MERRA-2; đây là chỉ mục tái sử dụng, chưa phải xác minh ranh giới tỉnh. Khung còn có ô biển/vùng lân cận; chưa áp mặt nạ ĐBSCL hoặc trọng số diện tích lúa. Không coi tất cả điểm đã tải là mẫu độc lập. Bức xạ mặt trời có độ phân giải thô hơn khí tượng, chỉ có trong nhóm 13 điểm ban đầu.

Nguồn kỹ thuật: https://power.larc.nasa.gov/docs/services/ và https://power.larc.nasa.gov/docs/services/api/temporal/daily/.

## Tệp kiểm kê

- `data/catalog/source_catalog.csv`: đường dẫn tệp và nguồn; số tệp không đồng nghĩa số quan sát lúa.
- `data/catalog/unavailable_sources.csv`: nguồn chưa tải được, giữ lý do để thử lại.
- `data/catalog/weather_inventory.csv`: phạm vi ngày và tham số từng tệp khí tượng.
- `data/raw/weather_daily_raw.csv`: bản trải phẳng phản hồi NASA; giữ mã thiếu gốc. Ô trống ở tham số chưa yêu cầu không được hiểu là giá trị bằng 0.
- `docs/raw_collection_status.json`: quy mô thu thập thực tế. Độ phủ tỉnh–năm–vụ của dữ liệu lúa chỉ được xác nhận sau bước trích xuất.
