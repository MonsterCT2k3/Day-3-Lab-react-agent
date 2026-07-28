# 🛠️ Tài Liệu Mô Tả Tools — `src/tools.py`

**Đề tài 10**: Trợ Lý Tìm & Đặt Lịch Xem Nhà Trọ / Căn Hộ Cho Thuê
**Phụ trách**: Role 2 — Tool Engineer

---

## 1. Tổng quan

File `src/tools.py` khai báo **10 công cụ (tools)** cho ReAct Agent, chia thành 2 nhóm:

| Nhóm | Tools |
|---|---|
| **Lõi (bắt buộc)** | `search_listings`, `get_listing_detail`, `check_viewing_availability`, `book_viewing_appointment`, `cancel_viewing_appointment`, `list_my_appointments`, `get_landlord_contact`, `calculate_distance` |
| **Mở rộng (bonus)** | `get_neighborhood_info`, `compare_listings` |

**Nguyên tắc thiết kế chung** (áp dụng cho mọi tool):
- Luôn `return` một **chuỗi (string)** mô tả kết quả — không trả `dict`/`object` thô, để LLM đọc trực tiếp làm `Observation`.
- Không bao giờ để hàm **crash**: mọi lỗi được bắt bằng `try/except` và trả về chuỗi thông báo lỗi rõ ràng, có gợi ý sửa (ví dụ: liệt kê danh sách mã hợp lệ).
- Dữ liệu là **mock data cố định** (`LISTINGS_DB`, `AVAILABLE_SLOTS`, `APPOINTMENTS_DB`) → kết quả deterministic, không cần API key, tái lập được khi demo/chấm bài.
- Mọi tool đều có trong `TOOL_REGISTRY` (map tên → function, dùng cho Role 4 gọi trong vòng lặp ReAct) và `TOOL_SPECS` (mô tả schema, dùng cho Role 3 nhúng vào system prompt).

---

## 2. Chi tiết từng Tool

### 2.1 `search_listings`
**Mục đích**: Tìm danh sách phòng trọ/căn hộ theo tiêu chí lọc.

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `location` | str | Không | Khu vực/quận, ví dụ `"Cầu Giấy"`. Bỏ trống = không lọc. |
| `price_max` | int | Không | Giá thuê tối đa (VNĐ/tháng). |
| `property_type` | str | Không | `"phong_tro"` \| `"chung_cu_mini"` \| `"can_ho"`. |
| `bedrooms` | int | Không | Số phòng ngủ tối thiểu. |

- **Kết quả thành công**: danh sách tin đăng (mã, tên, giá, khu vực, số PN).
- **Trường hợp lỗi/rỗng**: không tìm thấy → gợi ý nới lỏng điều kiện tìm kiếm.
- **Ví dụ gọi**: `search_listings(location="Cầu Giấy", price_max=7000000)`

---

### 2.2 `get_listing_detail`
**Mục đích**: Lấy thông tin chi tiết đầy đủ của 1 tin đăng.

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `listing_id` | str | Có | Mã tin đăng, ví dụ `"PT001"`. |

- **Kết quả thành công**: diện tích, giá, số PN, tiện ích, tên chủ nhà.
- **Trường hợp lỗi**: `listing_id` không tồn tại → trả về danh sách mã hợp lệ hiện có.
- **Ví dụ gọi**: `get_listing_detail("PT001")`

---

### 2.3 `check_viewing_availability`
**Mục đích**: Kiểm tra khung giờ còn trống để xem nhà.

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `listing_id` | str | Có | Mã tin đăng cần kiểm tra. |
| `date` | str | Không | Định dạng `"YYYY-MM-DD"`. Mặc định = ngày mai nếu bỏ trống. |

- **Kết quả thành công**: danh sách khung giờ trống (đã loại bỏ giờ đã bị đặt).
- **Trường hợp lỗi**: `listing_id` không tồn tại, hoặc hết slot trống trong ngày yêu cầu.
- **Ví dụ gọi**: `check_viewing_availability("PT001", "2026-08-01")`

---

### 2.4 `book_viewing_appointment`
**Mục đích**: Đặt lịch hẹn xem nhà.

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `listing_id` | str | Có | Mã tin đăng. |
| `date` | str | Có | Ngày hẹn, `"YYYY-MM-DD"`. |
| `time` | str | Có | Giờ hẹn, phải nằm trong khung giờ còn trống. |
| `customer_name` | str | Có | Tên khách hàng. |
| `customer_phone` | str | Có | SĐT liên hệ. |

- **Kết quả thành công**: mã lịch hẹn (`appointment_id`, ví dụ `APT1001`) + lời nhắc mang CCCD.
- **Trường hợp lỗi** (đây là tool có **nhiều nhánh lỗi nhất**, phù hợp để Role 3 test Guardrail):
  - `listing_id` không tồn tại.
  - Thiếu tên hoặc số điện thoại.
  - `time` không nằm trong khung giờ hợp lệ → gợi ý các giờ đúng.
  - **Trùng lịch**: khung giờ đã có người đặt trước đó.
- **Ví dụ gọi**: `book_viewing_appointment("PT001", "2026-08-01", "09:00", "Nguyễn Văn A", "0909123456")`

---

### 2.5 `cancel_viewing_appointment`
**Mục đích**: Hủy một lịch hẹn đã đặt.

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `appointment_id` | str | Có | Mã lịch hẹn, ví dụ `"APT1001"`. |

- **Kết quả thành công**: xác nhận đã hủy.
- **Trường hợp lỗi**: mã không tồn tại, hoặc đã bị hủy từ trước.
- **Ví dụ gọi**: `cancel_viewing_appointment("APT1001")`

---

### 2.6 `list_my_appointments`
**Mục đích**: Tra cứu tất cả lịch hẹn của một khách hàng.

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `customer_phone` | str | Có | SĐT khách hàng. |

- **Kết quả thành công**: danh sách lịch hẹn (mã, tin đăng, ngày giờ, trạng thái).
- **Trường hợp lỗi/rỗng**: không có lịch hẹn nào gắn với SĐT đó.
- **Ví dụ gọi**: `list_my_appointments("0909123456")`

---

### 2.7 `get_landlord_contact`
**Mục đích**: Lấy thông tin liên hệ chủ nhà/môi giới.

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `listing_id` | str | Có | Mã tin đăng. |

- **Kết quả thành công**: tên + SĐT chủ nhà.
- **Trường hợp lỗi**: `listing_id` không tồn tại.
- **Ví dụ gọi**: `get_landlord_contact("CC002")`

---

### 2.8 `calculate_distance`
**Mục đích**: Ước tính khoảng cách từ tin đăng đến một địa điểm tham chiếu.

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `listing_id` | str | Có | Mã tin đăng. |
| `destination` | str | Có | Tên địa điểm, hỗ trợ: `"đại học bách khoa"`, `"hồ gươm"`, `"sân bay nội bài"`. |

- **Kết quả thành công**: khoảng cách ước tính (km, tính xấp xỉ theo tọa độ — chỉ mang tính minh họa, không phải khoảng cách đường thực tế).
- **Trường hợp lỗi**: `listing_id` không tồn tại, hoặc `destination` không nằm trong danh sách hỗ trợ → gợi ý các địa điểm hợp lệ.
- **Ví dụ gọi**: `calculate_distance("PT001", "đại học bách khoa")`

---

### 2.9 `get_neighborhood_info` *(mở rộng)*
**Mục đích**: Mô tả khu vực xung quanh tin đăng (an ninh, tiện ích lân cận).

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `listing_id` | str | Có | Mã tin đăng. |

- **Kết quả thành công**: đoạn mô tả khu vực (mock cố định theo từng tin đăng).
- **Trường hợp lỗi**: `listing_id` không tồn tại.
- **Ví dụ gọi**: `get_neighborhood_info("CH003")`

---

### 2.10 `compare_listings` *(mở rộng)*
**Mục đích**: So sánh nhanh 2–3 tin đăng theo giá, diện tích, số phòng ngủ.

| Tham số | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `listing_ids` | list[str] | Có | Danh sách 2–3 mã tin đăng. |

- **Kết quả thành công**: bảng so sánh dạng text.
- **Trường hợp lỗi**: ít hơn 2 mã, nhiều hơn 3 mã, hoặc có mã không tồn tại trong danh sách.
- **Ví dụ gọi**: `compare_listings(["PT001", "CC002"])`

---

## 3. Bảng tổng hợp nhanh (cho Role 3 viết Prompt)

| # | Tool | Khi nào Agent nên gọi |
|---|---|---|
| 1 | `search_listings` | Người dùng mô tả nhu cầu tìm nhà (khu vực/giá/loại hình) nhưng chưa có mã cụ thể. |
| 2 | `get_listing_detail` | Người dùng hỏi sâu về 1 tin đăng đã có mã. |
| 3 | `check_viewing_availability` | Người dùng muốn biết lịch trống trước khi đặt hẹn. |
| 4 | `book_viewing_appointment` | Người dùng đã chọn được tin đăng + ngày giờ, muốn xác nhận đặt lịch. |
| 5 | `cancel_viewing_appointment` | Người dùng muốn hủy lịch đã đặt. |
| 6 | `list_my_appointments` | Người dùng hỏi lại lịch mình đã đặt (dùng SĐT để tra). |
| 7 | `get_landlord_contact` | Người dùng muốn liên hệ trực tiếp chủ nhà. |
| 8 | `calculate_distance` | Người dùng quan tâm khoảng cách đến trường/công ty/sân bay. |
| 9 | `get_neighborhood_info` | Người dùng hỏi về an ninh/tiện ích xung quanh khu vực. |
| 10 | `compare_listings` | Người dùng phân vân giữa 2-3 lựa chọn, muốn so sánh. |

## 4. Test Case gợi ý để Role 1/Role 5 khai thác lỗi (Edge Case)

- Gọi `book_viewing_appointment` với `listing_id` không tồn tại (ví dụ `"XX999"`).
- Gọi `book_viewing_appointment` 2 lần cùng `listing_id` + `date` + `time` → kiểm tra Agent có phát hiện trùng lịch và không lặp vô hạn.
- Gọi `calculate_distance` với `destination` lạ (ví dụ `"mặt trăng"`) → kiểm tra Agent xử lý thông báo lỗi lịch sự thay vì bịa số km.
- Gọi `compare_listings` với 1 mã hoặc 4 mã → kiểm tra Agent tuân theo giới hạn 2-3 tin đăng.

---

*Tài liệu này phục vụ Mốc 2 (Docstring/Tool Specs) và làm nguồn tham chiếu cho Role 3 khi soạn `REACT_SYSTEM_PROMPT` trong `src/prompts.py`.*