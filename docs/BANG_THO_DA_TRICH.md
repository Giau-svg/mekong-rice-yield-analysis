# Bảng thô đã trích từ PDF

Các bảng dưới đây thuộc bước thu thập. Số, dấu phân cách và đơn vị được giữ nguyên; chưa quy đổi, điền thiếu, chọn phiên bản nguồn hay ghép thời tiết.

| Tệp | Phạm vi | Số dòng |
|---|---|---:|
| `data/raw/rice_captured_main_seasons.csv` | Kiên Giang, An Giang, Cần Thơ; 2015–2024; Đông Xuân, Hè Thu, Thu Đông riêng | 90 |
| `data/raw/rice_captured_all_categories.csv` | Cùng nguồn, thêm tổng năm, mùa và nếp tùy bảng | 150 |
| `data/raw/nso_rice_province_tables.csv` | 13 tỉnh; 2015–2024; cả năm, Đông Xuân, Hè Thu và Thu Đông gộp, mùa | 467 |
| `data/raw/rice_report_season_values.csv` | Thu Đông Tiền Giang 2021, 2022, 2024 từ báo cáo năm | 3 |

Mỗi dòng có diện tích, năng suất, sản lượng, URL, SHA-256 và trang PDF tương ứng. Không cộng các tệp để tính số mẫu độc lập: chúng có phạm vi trùng nhau và chứa cả tổng năm, vụ gộp.

## Bảng NSO toàn vùng

- Cả năm: 130 dòng; Đông Xuân: 127 dòng; Hè Thu–Thu Đông gộp: 130 dòng; mùa: 80 dòng.
- Cà Mau, Đông Xuân 2015–2019: đã đối chiếu hình trang PDF 525, 527, 529 và xác định hai cột có giá trị thuộc năm 2017, 2019. Các ô năm 2015, 2016, 2018 để trống ở nguồn; không điền 0. Hàng trích gốc vẫn giữ tại `data/raw/nso_rice_table_rows.jsonl`.
- Các tỉnh không xuất hiện trong bảng mùa được ghi tại `data/catalog/nso_rice_capture_issues.json`. Không suy ra bằng 0 hoặc không gieo trồng từ việc vắng dòng.
- Nhãn tham chiếu tỉnh chỉ phục vụ lập chỉ mục. Tên trích gốc được giữ theo từng chỉ tiêu, kể cả khoảng trắng tách chữ trong PDF.
- Số liệu năm cuối mỗi niên giám NSO mang nhãn sơ bộ. Các phiên bản khác vẫn được lưu để đối chiếu ở bước xử lý.

## Chạy lại từ kho PDF hiện có

```powershell
node scripts/capture_rice_tables_raw.mjs
node scripts/capture_nso_rice_raw.mjs
node scripts/index_html_raw.mjs
node scripts/capture_report_values_raw.mjs
node scripts/audit_collection_coverage.mjs
node scripts/catalog_pdf_candidates.mjs
```

Các lệnh cần chỉ mục `data/raw/pdf_text/` đã có. Nếu bổ sung PDF, chạy `scripts/index_pdf_raw.mjs` trước; công cụ cần `pdfjs-dist` trong `tmp/pdf-runtime/node_modules/`.

Chưa đủ bằng chứng xác nhận ba vụ tách riêng cho toàn bộ 13 tỉnh trong cả 10 năm. Danh mục trang có từ khóa lúa là công cụ tìm nguồn, không phải các quan sát số đã được xác minh.

`data/catalog/rice_collection_coverage.csv` kiểm kê 390 tổ hợp tham chiếu; hiện có 190 tổ hợp có giá trị nguồn tách vụ, bao gồm số báo cáo năm chưa đối chiếu bản điều chỉnh. Các tổ hợp còn thiếu nằm trong `data/catalog/rice_collection_gaps.csv`. Đây là kiểm kê thu thập, không xác nhận rằng cả 390 tổ hợp đều có gieo trồng.
