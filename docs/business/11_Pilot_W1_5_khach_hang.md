# Pilot W1 – Số hoá 5 khách hàng mục tiêu

> Ngày lập: 25/11/2026 · Căn cứ: tài liệu 10, mục đợt W1 · Người thực hiện: phía Spider (nhập liệu + xác nhận)

## 1. Mục tiêu pilot

1. Chạy trọn quy trình trên dữ liệu thật: gắn hồ sơ → nhập dữ kiện có trích dẫn → đối chiếu → công bố → tra cứu → cảnh báo.
2. Đo **thời gian thực tế** cho mỗi bộ hồ sơ để ước lượng lại các đợt W2–W4 (tài liệu 08 đang giả định 8 / 45 / 180 phút cho Tier A / B / C).
3. Ghi lại mọi chỗ hệ thống **thiếu trường, thiếu thao tác hoặc gây chậm** để sửa trước khi làm hàng loạt.
4. Quyết định có dùng OCR/AI gợi ý hay không (chỉ dùng nếu tiết kiệm thời gian rõ rệt; người vẫn xác nhận từng dữ kiện).

## 2. Năm khách hàng được chọn

Chọn để phủ đủ tình huống khó: nhiều phụ lục, phụ lục giá dầu, thanh lý, hợp đồng thuê kho, một đối tác vừa là KH vừa là NCC.

| #   | Mã KH  | Đối tác                      | Bộ hồ sơ trong hệ thống                                                         | Số tệp | Tình huống cần kiểm                                                                                                                            |
| --- | ------ | ---------------------------- | ------------------------------------------------------------------------------- | -----: | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | KH0124 | Masan (Hàng tiêu dùng Masan) | `1.HĐVC+PL(KH)-MASAN NĐ`                                                        |     14 | 12 phụ lục, PL05 gia hạn nhưng tiêu đề ghi giá dầu, PL12 đổi giá + gốc dầu + địa chỉ, **đã thanh lý 25/03/2025**; đối tác vừa là KH vừa là NCC |
| 2   | KH0668 | The Supra                    | `241.HĐVC(KH)-THE SUPRA`                                                        |     52 | Nhiều phụ lục giá dầu; tracker ghi hết hạn 24/11/2025, cần xem có phụ lục gia hạn không                                                        |
| 3   | KH0380 | Yusen (Miền Bắc)             | `58.HĐVC+PL(KH)-YUSEN MB`                                                       |     39 | Chuỗi phụ lục dài, kiểm tra quy tắc số phụ lục liên tục                                                                                        |
| 4   | KH0883 | Lavela                       | `355.HĐ(THUÊ KHO-VẬN CHUYỂN)-LAVELA` và `II…/10.HĐ(THUÊ KHO-VẬN CHUYỂN)-LAVELA` | 24 + 3 | Hợp đồng thuê kho + vận chuyển, hai thư mục cho cùng đối tác, hiệu lực đến 24/11/2027                                                          |
| 5   | KH0503 | XNK Việt Úc                  | `135.HĐVC(KH)-VIỆT ÚC.pdf` và `II…/2.HĐ(THUÊ KHO)-VIỆT ÚC`                      | 1 + 10 | Một HĐ vận chuyển + một HĐ thuê kho; **tracker ghi STT 136, thư mục ghi 135**                                                                  |

Cả 5 mã đều đã có trong danh mục đối tác và không có xung đột dữ liệu đang mở.

## 3. Chuẩn bị (một lần)

- Một tài khoản vai trò `accountant` (Kế toán) là đủ: cùng một người nhập, đối chiếu và công bố.
- Tạo tài khoản (admin chạy trong `apps/api`):

  ```bash
  uv run python -m app.cli create-user <email> "<Họ tên>" --role accountant
  ```

## 4. Trình tự cho mỗi bộ hồ sơ

| Bước | Ai         | Màn hình                             | Việc làm                                                                                                                                                          |
| ---- | ---------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | Người nhập | **Hồ sơ** → mở bộ hồ sơ              | Bấm chọn đối tác gợi ý **chỉ khi khớp mã/MST**; không chắc thì để trống và ghi vào nhật ký                                                                        |
| 2    | Người nhập | Chi tiết hồ sơ → **Tạo hợp đồng**    | Chọn họ hợp đồng (vận chuyển, thuê kho…)                                                                                                                          |
| 3    | Người nhập | Chi tiết hợp đồng → **Thêm văn bản** | Thêm hợp đồng gốc, phụ lục kèm HĐ (bảng giá, KPI…), từng phụ lục sửa đổi, biên bản thanh lý; chọn đúng tệp và trang. Số phụ lục ghi **đúng như in** (01A, 02.01…) |
| 4    | Người nhập | Từng văn bản → nhập dữ kiện          | Mỗi dữ kiện ghi **số trang + trích nguyên văn**. Không thấy thì chọn “Văn bản không ghi”, “Không đọc được” hoặc “Thiếu trang”; **không suy đoán**                 |
| 5    | Người nhập | Cùng màn hình                        | Đối chiếu lại từng dữ kiện với bản scan; sai thì bấm **Nhập** để sửa                                                                                              |
| 6    | Người nhập | Chi tiết hợp đồng → **Công bố**      | Công bố được khi đủ dữ kiện bắt buộc. Sau khi công bố, mỗi lần sửa phải ghi lý do                                                                                 |
| 7    | Bất kỳ     | **Tra cứu** và **Cảnh báo**          | Tra cứu theo đối tác + ngày; so trạng thái và ngày hết hạn với tracker Excel                                                                                      |

## 5. Nhật ký pilot (điền khi làm)

Bấm giờ từ lúc mở bộ hồ sơ đến lúc công bố. Ghi riêng thời gian xác nhận.

| #   | Bộ hồ sơ            | Số văn bản | Số trang | Phút nhập | Phút xác nhận | Số dữ kiện phải sửa | Trạng thái hệ thống | Khớp tracker? | Vướng mắc / đề xuất |
| --- | ------------------- | ---------: | -------: | --------: | ------------: | ------------------: | ------------------- | ------------- | ------------------- |
| 1   | MASAN NĐ            |            |          |           |               |                     |                     |               |                     |
| 2   | THE SUPRA           |            |          |           |               |                     |                     |               |                     |
| 3   | YUSEN MB            |            |          |           |               |                     |                     |               |                     |
| 4   | LAVELA (2 thư mục)  |            |          |           |               |                     |                     |               |                     |
| 5   | VIỆT ÚC (2 thư mục) |            |          |           |               |                     |                     |               |                     |

Kết quả mong đợi ví dụ: MASAN NĐ phải ra trạng thái **Đã thanh lý**, không phải “hết hạn 30/06/2025” như tracker.

## 6. Tiêu chí kết thúc pilot

- 5/5 bộ hồ sơ đã công bố, hoặc có lý do ghi rõ vì sao chưa (thiếu trang, chưa rõ đối tác…).
- Mọi chênh lệch giữa hệ thống và tracker đều đã được giải thích bằng văn bản gốc.
- Có số phút trung bình cho mỗi văn bản và mỗi bộ, đủ để ước lượng lại W2–W4.
- Có danh sách vướng mắc xếp theo mức độ, gửi lại để sửa hệ thống trước đợt W2.

## 7. Chưa có trong bản này

- Bảng giá và phụ lục giá dầu mới ghi dạng **tóm tắt** (trường “Nội dung”), chưa nhập từng dòng giá. Nhập bảng giá chi tiết là việc của giai đoạn sau, sẽ quyết định dựa trên kết quả pilot.
- OCR/AI gợi ý chưa bật.
