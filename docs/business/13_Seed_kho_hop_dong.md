# 13. Dữ liệu hợp đồng cũ: đọc một lần, nạp bằng seed

Thay cho việc nhân viên nhập tay từng hồ sơ, toàn bộ kho scan được đọc một lần, kiểm tra, rồi đóng gói
thành `apps/api/seed/archive.json`. Hệ thống nạp tệp này bằng lệnh `import-archive`, ở local và
production như nhau.

## 1. Kết quả

| Hạng mục                                                               | Số lượng                                                  |
| ---------------------------------------------------------------------- | --------------------------------------------------------- |
| Tệp trong kho (không trùng nội dung)                                   | 1.988 — đã đọc 1.986 (2 tệp `.rar` cần giải nén thủ công) |
| Hợp đồng                                                               | 1.083                                                     |
| Phụ lục, phụ lục kèm, thanh lý gắn đúng hợp đồng                       | 669                                                       |
| Hồ sơ theo đối tác (gom tệp nằm rải rác nhiều thư mục)                 | 904                                                       |
| Đối tác có trên hợp đồng nhưng chưa có trong danh mục (mã `ARC-<MST>`) | 84                                                        |
| Chuỗi tái ký (hợp đồng mới thay hợp đồng cũ)                           | 42                                                        |

Báo giá, biên bản và tài liệu khác (≈ 200 tệp) được giữ trong hồ sơ đối tác để tra cứu, không tạo
hợp đồng.

## 2. Cách làm

1. **OCR toàn bộ** (Apple Vision, tiếng Việt), 11.008 trang.
2. **Đọc từng tệp**: loại văn bản, số, đối tác + MST, ngày ký, hiệu lực, hết hạn, gia hạn, báo
   trước, công nợ, hợp đồng gốc (với phụ lục). Mỗi giá trị phải tìm lại được nguyên văn trong
   OCR; không tìm thấy thì gắn cờ.
3. **Gom và nối**:
   - Đối tác: theo MST → tên pháp lý → tên ngắn → thư mục; đối chiếu thêm với
     `Danh sách HĐKH và NCC (Cập nhật 23.11.2026).xlsx`.
   - Bản scan trùng (cùng số, cùng ngày) gộp làm một.
   - Phụ lục gắn theo số hợp đồng gốc in trên phụ lục, nếu không có thì theo ngày.
   - **Tái ký**: hợp đồng sau cùng đối tác, cùng dịch vụ, bắt đầu sau ngày hết hạn ghi trên hợp
     đồng trước → hợp đồng trước chuyển **Đã thay thế** từ ngày hợp đồng sau có hiệu lực.
4. **Tự kiểm tra lại** 550 văn bản bị gắn cờ (đọc lại nguyên văn, quyết định đối tác / hợp đồng gốc
   / sửa ngày).
5. **Sổ kiểm tra** `docs/business/data/.extract/Kiem_tra_so_hoa.xlsx`: danh sách cờ, mẫu ngẫu
   nhiên 10%, toàn bộ văn bản kèm đường dẫn tệp.

## 3. Quy tắc trạng thái khi thiếu ngày

- Không ghi ngày hiệu lực → tính từ **ngày ký** (BLDS 2015, Điều 401).
- Không có cả ngày ký lẫn ngày hiệu lực → **Chưa xác định**, không đoán.
- Hết hạn mà có điều khoản tự động gia hạn → **Tự động gia hạn**; gia hạn có điều kiện → **Chưa xác
  định**.

## 4. Còn để người kiểm tra

- **Chưa nối tái ký (107 hợp đồng)**: cùng đối tác, cùng dịch vụ nhưng thời hạn chồng nhau hoặc
  không ghi ngày hết (ví dụ Viettel nhiều chi nhánh, PVCFC mỗi việc một hợp đồng). Giữ riêng từng
  hợp đồng; nếu thực tế là tái ký, mở hợp đồng cũ và nhập **Ngày chấm dứt** bằng một văn bản thanh lý.
- **Khác với file theo dõi Excel**: 118 khác đối tác, 83 khác ngày — phần lớn do file theo dõi ghi
  mã cũ hoặc ngày gia hạn.
- 2 tệp `.rar` trong kho.

## 5. Nạp dữ liệu

```bash
# local (apps/api)
uv run python -m app.cli sync-partners --customers … --suppliers …
uv run python -m app.cli ingest-documents --customers … --suppliers …
uv run python -m app.cli import-archive --actor <email>

# production
scripts/live.sh user <email> "<tên>" admin
scripts/live.sh import <email>
```

Mỗi bước chạy lại bao nhiêu lần cũng được: chỉ thêm phần còn thiếu.
