# Kết quả tự kiểm chứng pilot W1 trên 5 khách hàng

> Ngày: 25/11/2026 · Người làm: Claude (đọc bản scan và chạy thử trên hệ thống ở máy local) · Căn cứ: tài liệu 11

## 1. Đã làm gì

- Đọc bản scan của 5 bộ hồ sơ, tập trung vào những trang quyết định hiệu lực: trang đầu, điều khoản thời hạn, trang ký, phụ lục gia hạn, biên bản thanh lý. Tổng cộng khoảng 70 trang trên tổng số 651 trang của 5 bộ.
- Nhập thử bộ **MASAN NĐ** vào hệ thống: 42 dữ kiện, mỗi dữ kiện có số trang và trích dẫn, xác nhận bằng tài khoản thứ hai, rồi bấm công bố.
- Tính trạng thái theo đúng logic của hệ thống cho cả 5 khách hàng, so với văn bản gốc và với tracker Excel.

**Lưu ý:** người đọc và người xác nhận ở đây đều là Claude, nên **đây không phải xác nhận hai người thật**. Dữ liệu chỉ nằm trong máy local, không dùng làm dữ liệu chính thức.

## 2. Kết quả theo từng khách hàng

| Khách hàng         | Văn bản gốc nói gì                                                                                                                                                               | Tracker Excel      | Hệ thống tính ra                                                                    | Đánh giá                                                                                                   |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| MASAN NĐ (KH0124)  | HĐ 2022/MSC-SPIDER/VC ký 15/03/2022, hết hạn 31/12/2022; PL05 gia hạn đến 30/06/2025; **thanh lý 25/03/2025**                                                                    | Hết hạn 30/06/2025 | Còn hiệu lực đến 24/03/2025, **Đã thanh lý** từ 25/03/2025                          | Hệ thống đúng, tracker sai                                                                                 |
| THE SUPRA (KH0668) | HĐ 26022025/HĐVC/SUPRA-SPIDER, hết hạn 24/11/2025; **PL 02.01 gia hạn đến 30/06/2027** hoặc đến khi có HĐ mới                                                                    | Hết hạn 24/11/2025 | **Còn hiệu lực** ngày 25/11/2026                                                    | Hệ thống đúng, tracker sai                                                                                 |
| YUSEN MB (KH0380)  | HĐ 02.2023/YLTV-SPIDER hiệu lực 20/02/2023 – 31/03/2024; điều 1.2 “**có thể** được gia hạn 01 năm” nếu không vi phạm; PL 21/04.2026 gia hạn 01/04/2026 – 31/03/2027              | —                  | Ngày 01/01/2025 ra “Hết hạn” hoặc “Tự gia hạn” **tùy người nhập chọn có hay không** | Văn bản không đủ để kết luận giai đoạn 04/2024 – 03/2026; hệ thống chưa có cách ghi “gia hạn có điều kiện” |
| LAVELA (KH0883)    | HĐ 01/SPIDER_LVL ký 25/11/2025, “hiệu lực **tối thiểu 2 năm**”, **không ghi ngày hết hạn**                                                                                       | Hết hạn 24/11/2027 | Chỉ chọn được “Không thời hạn”                                                      | Ngày trong tracker là tự suy ra; hệ thống chưa có loại thời hạn “tối thiểu”                                |
| VIỆT ÚC (KH0503)   | HĐVC 01032024 ký 01/03/2024, “12 tháng kể từ ngày ký”, **tự gia hạn hằng năm** nếu không báo trước 45 ngày; cộng thêm **4 HĐ thuê kho** ở Đà Nẵng (2025, 2026), TP.HCM, Hưng Yên | 1 dòng, STT 136    | Đang tự gia hạn; **không có cảnh báo** cho hạn báo trước 45 ngày của kỳ sau         | Thiếu cảnh báo; một hồ sơ chứa 5 hợp đồng                                                                  |

**Kết luận:** logic tính trạng thái theo văn bản đã ký **đã đúng ở 2 bộ dữ kiện rõ ràng (Masan, Supra), và ở cả hai bộ này tracker Excel đều sai**. Ba bộ còn lại cho thấy hồ sơ thật đa dạng hơn mô hình hiện tại. Nếu nhập hàng loạt ngay, người nhập sẽ buộc phải **chọn đại** một giá trị, tức là đúng điều mà yêu cầu “không suy đoán” cấm.

## 3. Những chỗ hệ thống phải sửa trước khi cho người thật làm pilot

### Chặn: không nhập hoặc không công bố được

| #   | Vấn đề gặp trên hồ sơ thật                                                                                                           | Bằng chứng                                                                                                             | Đề xuất sửa                                                                                                                                                                                                                                                          |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1  | Số phụ lục không phải số nguyên liên tục: 01A, 01B, 02.01…02.19, 02.15A, 1A, 24.1, 25.2, “21/04.2026”; có cả **hai văn bản cùng số** | Supra; Yusen có 2 bản “PHỤ LỤC 24” (22/04 và 19/06/2026) và 2 bản “PHỤ LỤC 26” (17/07 và 21/08/2026)                   | Ghi số phụ lục **đúng như in trên giấy** (dạng chữ). Sắp thứ tự theo ngày hiệu lực rồi ngày ký. Bỏ ràng buộc mỗi số chỉ một văn bản. Đổi quy tắc “thiếu số” từ chặn thành **cảnh báo**, kèm danh sách số còn thiếu mà người duyệt xác nhận là “không có trong hồ sơ” |
| C2  | Phụ lục **kèm hợp đồng gốc** (bảng giá, quy trình, KPI, quy định an toàn) không phải phụ lục sửa đổi, không có ngày riêng            | Masan PL01–04; Lavela PL1–5; Supra PL01 nằm ngay trong tệp HĐ                                                          | Thêm loại văn bản “Phụ lục kèm HĐ”: không bắt nhập ngày, không tính vào chuỗi sửa đổi. **Masan bị chặn công bố chính vì lỗi này**: hệ thống báo thiếu PL01–04                                                                                                        |
| C3  | Thời hạn không phải lúc nào cũng là “đến ngày X”                                                                                     | Lavela “tối thiểu 2 năm”; Việt Úc “12 tháng kể từ ngày ký”; Supra “đến 30/06/2027 **hoặc** đến khi HĐ mới có hiệu lực” | Thêm loại thời hạn: “có ngày hết hạn”, “theo số tháng” (hệ thống tự tính và ghi rõ là _ngày tính ra_), “tối thiểu N tháng rồi tiếp tục”, “không thời hạn”. Điều kiện “hoặc đến khi có HĐ mới” lưu thành ghi chú bắt buộc                                             |
| C4  | Gia hạn có điều kiện: “**có thể** gia hạn nếu không vi phạm”                                                                         | Yusen điều 1.2                                                                                                         | Ô “Tự gia hạn” có 3 lựa chọn: Có / Không / **Có điều kiện**. Chọn “có điều kiện” thì sau ngày hết hạn trạng thái là **Chưa xác định**, kèm việc cần làm: người phụ trách xác nhận bằng văn bản                                                                       |
| C5  | Phụ lục chỉ gia hạn **bảng giá**, không gia hạn hợp đồng                                                                             | Supra PL01B: gia hạn đơn giá PL01 đến 25/11/2026                                                                       | Ô “gia hạn đến” phải nói rõ gia hạn **hợp đồng** hay **bảng giá**. Chỉ gia hạn hợp đồng mới làm đổi trạng thái hợp đồng                                                                                                                                              |

### Quan trọng: nhập được nhưng kết quả thiếu hoặc dễ hiểu sai

| #   | Vấn đề                                                                                                          | Bằng chứng                                                                                                                                                                                                            | Đề xuất                                                                                                                          |
| --- | --------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Q1  | Hợp đồng tự gia hạn cần cảnh báo **hạn báo trước** của từng kỳ, không chỉ ngày hết hạn đầu tiên                 | Việt Úc 45 ngày; hiện chỉ báo trước khi hết hạn lần đầu                                                                                                                                                               | Sinh cảnh báo cho mỗi kỳ gia hạn: ngày hết kỳ trừ số ngày báo trước                                                              |
| Q2  | Một hồ sơ có nhiều hợp đồng; một khách có nhiều HĐ cùng hiệu lực (vận chuyển, thuê kho ở 3 địa điểm)            | Việt Úc                                                                                                                                                                                                               | Thêm **phạm vi** cho hợp đồng (dịch vụ + địa điểm). Tra cứu đơn lọc theo phạm vi; nếu vẫn ra nhiều HĐ thì liệt kê, không tự chọn |
| Q3  | Công thức giá dầu **khác nhau theo khách**                                                                      | Masan: D=35%, ±10% lũy kế, áp dụng từ ngày thứ 11, làm tròn xuống 100đ (khớp đúng 10/10 mức giá đã ký ở PL08–PL12). Lavela: D=30%, so giá dầu ngày cuối kỳ thanh toán, áp dụng kỳ sau, không làm tròn (ví dụ 750.564) | Tham số giá dầu lưu **theo từng hợp đồng**, không dùng một công thức chung. Cần sửa tài liệu 05 (đang ghi một công thức)         |
| Q4  | Trong hồ sơ có tệp không phải bản ký: .docx, .xlsx, hai bản “PL13” và “PL13 ok”, trang trắng do scan xuyên giấy | Yusen; Lavela                                                                                                                                                                                                         | Cho đánh dấu tệp “không phải văn bản đã ký” để loại khỏi dữ kiện                                                                 |
| Q5  | Báo giá có ký, đóng dấu nhưng không số, không ngày, vẫn ràng buộc giá                                           | Yusen “Báo giá FTN”, “Báo giá 01/02”                                                                                                                                                                                  | Thêm loại văn bản “Báo giá đã ký”, ngày cho phép “Văn bản không ghi”                                                             |
| Q6  | Thư mục con mang tên khác (“Meat life”, “Hưng Yên”, “3F-HÀNG ĐÔNG”) thực chất là phụ lục của HĐ Supra           | Supra                                                                                                                                                                                                                 | Chỉnh lại nhận xét trước đó: **MASAN MEATLIFE không phải đối tác bị thiếu trong MISA**, mà là điểm giao hàng trong phụ lục Supra |

### Những gì đã chạy đúng

- Biên bản thanh lý để trống số (“Số : /20…/TLHĐ”) nhập được bằng lựa chọn **Văn bản không ghi**.
- Không ai tự xác nhận được dữ kiện của chính mình.
- Hai thư mục Lavela trùng nhau chỉ được lưu một lần (cùng mã băm).
- Hệ thống tính đúng trạng thái thanh lý của Masan và trạng thái gia hạn của Supra.

## 4. Khối lượng thực tế

| Bộ        |        Số tệp | Số trang | Văn bản quyết định hiệu lực | Ghi chú                                           |
| --------- | ------------: | -------: | --------------------------- | ------------------------------------------------- |
| MASAN NĐ  |            14 |       40 | 1 HĐ + 8 PL + 1 thanh lý    | Mỗi phụ lục 2 trang, dễ đọc                       |
| THE SUPRA |            52 |      340 | 1 HĐ + 2 PL gia hạn         | 43 tệp phụ lục còn lại **chưa đọc**               |
| YUSEN MB  |            40 |      136 | 1 HĐ + PL gia hạn 2026      | PL01–20 **chưa đọc**; 2 tệp không phải PDF ký     |
| LAVELA    | 24 (+3 trùng) |       81 | 1 HĐ                        | 22 phụ lục điều chỉnh giá dầu                     |
| VIỆT ÚC   |            11 |       54 | 5 HĐ                        | Chưa đọc điều 2 (thời hạn thuê) của 4 HĐ thuê kho |

Nhận xét:

- Phần **xác định hiệu lực** chỉ nằm trên vài trang mỗi văn bản, nhập nhanh.
- Phần nặng là **bảng giá**: hàng chục tuyến, nhiều loại xe, đổi theo giá dầu nhiều lần mỗi năm.
- Nên **tách hai giai đoạn**: (1) số hoá hiệu lực và cảnh báo cho toàn bộ hồ sơ; (2) số hoá bảng giá theo khách hàng ưu tiên. Ước lượng ở tài liệu 08 cần tính lại theo hai giai đoạn này.
- Đây là chỗ **OCR/AI có lợi rõ nhất**: đọc bảng giá dạng lưới in rõ, rồi người đối chiếu.

## 5. Đã sửa (25/11/2026, commit `ade1474`)

Theo quyết định: **một người nhập, tự đối chiếu và công bố**. Bỏ bước người thứ hai xác nhận từng dữ kiện; bấm **Công bố** là lời xác nhận. Sửa sau khi công bố vẫn phải ghi lý do.

| #   | Trạng thái | Cách làm trong hệ thống                                                                                                                                 |
| --- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1  | Đã sửa     | Số văn bản là ô chữ, ghi đúng như in; trùng số vẫn nhận; không còn chặn vì thiếu số                                                                     |
| C2  | Đã sửa     | Thêm loại văn bản **Phụ lục kèm HĐ**: không bắt ngày, không tính vào chuỗi sửa đổi. Masan công bố được                                                  |
| C3  | Đã sửa     | Thời hạn: đến ngày cụ thể / theo số tháng (hệ thống tự tính ngày hết hạn) / tối thiểu số tháng / không thời hạn / đến khi có thông báo hoặc HĐ mới      |
| C4  | Đã sửa     | Gia hạn: không / tự động (kèm số tháng mỗi kỳ) / **có thể (cần thoả thuận)**. Hết hạn mà gia hạn có điều kiện thì trạng thái là **Chưa xác định**       |
| C5  | Đã sửa     | Phụ lục chỉ gia hạn bảng giá thì để trống ô “Gia hạn đến”; ô này chỉ dùng cho gia hạn hợp đồng                                                          |
| Q1  | Một phần   | Cảnh báo 90/60/30 ngày được sinh cho **mỗi kỳ** tự gia hạn. Chưa tính riêng mốc “hết kỳ trừ số ngày báo trước”; số ngày báo trước đã hiện trên hợp đồng |
| Q2  | Một phần   | Thêm ô **Phạm vi** (dịch vụ, địa điểm). Tra cứu liệt kê mọi HĐ còn hiệu lực, chưa lọc theo phạm vi                                                      |
| Q3  | Tài liệu   | Đã ghi vào tài liệu 10: tham số giá dầu theo từng hợp đồng. Sẽ làm cùng module bảng giá (giai đoạn 2)                                                   |
| Q4  | Chưa làm   | Đánh dấu tệp không phải bản ký                                                                                                                          |
| Q5  | Chưa làm   | Loại văn bản “Báo giá đã ký”; tạm nhập như phụ lục kèm HĐ                                                                                               |

## 6. Đề xuất bước tiếp theo

1. ~~Sửa hệ thống theo C1–C5 và Q1–Q2~~ (xem mục 5).
2. ~~Sửa tài liệu 10 cho Q3~~. Tài liệu Word/Excel 01–09 vẫn mô tả bước người thứ hai và một công thức giá dầu chung, cần cập nhật ở lần phát hành sau.
3. Sau đó mới giao người thật chạy pilot theo tài liệu 11, bấm giờ thật.
4. Dữ liệu thử của Claude trong máy local sẽ được xoá trước khi người thật bắt đầu.
