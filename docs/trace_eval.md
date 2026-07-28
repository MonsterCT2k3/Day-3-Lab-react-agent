# 📊 BÁO CÁO GIÁM SÁT & ĐÁNH GIÁ (OBSERVABILITY TRACE LOGS)
*Dành cho Role 5: Observability & Reviewer*
*Chủ đề bài toán: Đề tài 10 - Trợ Lý Tìm & Đặt Lịch Xem Nhà Trọ / Căn Hộ Cho Thuê*
*Trạng thái: ✅ Đã hoàn thành Mốc 1 (Scoring Matrix & Định hình)*

---

## 🎯 1. BẢNG CHẤM ĐIỂM AGENTIC FIT (SCORING MATRIX)

| Tiêu chí | Điểm (1-5) | Lý do đánh giá |
| :--- | :---: | :--- |
| 🧠 **Multi-step Reasoning** | `5/5` | Cần suy luận qua chuỗi bước: Lọc danh sách phòng theo vị trí/ngân sách $\rightarrow$ Lựa chọn phòng phù hợp $\rightarrow$ Đặt lịch xem nhà. |
| 🛠️ **Tool Interaction** | `5/5` | Bắt buộc truy xuất dữ liệu nhà trọ thời gian thực (`search_apartments`) và tương tác hệ thống đặt lịch (`schedule_viewing`). |
| 🔀 **Dynamic Decision** | `4/5` | Kết quả bước trước (VD: không có phòng giá yêu cầu) sẽ quyết định hành động bước sau (gợi ý khu vực lân cận hoặc hỏi lại tiêu chí). |
| ⏳ **Long Horizon** | `4/5` | Tiến trình xử lý kéo dài 2–4 bước lặp với dữ liệu bên ngoài trước khi hoàn tất lịch hẹn. |
| **TỔNG ĐIỂM FIT** | **18/20** | **KẾT LUẬN: BÀI TOÁN RẤT NÊN DÙNG REACT AGENT!** |

---

## 🔍 2. SO SÁNH PHẢN HỒI (TEST CASE #3 - ĐỀ TÀI 10)

**Câu hỏi**: *"Tôi đang tìm phòng trọ ở Hà Nội, ngân sách dưới 3 triệu đồng/tháng. Bạn có gợi ý gì không?"*

### 🤖 Chatbot Baseline (Mốc 2):
* **Phản hồi**: *"Chào bạn! Rất vui được hỗ trợ... Tuy nhiên, để đưa ra các gợi ý chính xác nhất, tôi sẽ cần thêm thông tin từ bạn vì tôi không có quyền truy cập trực tiếp vào dữ liệu phòng trọ trống theo thời gian thực như các ứng dụng hoặc trang web chuyên dụng..."*
* **Nhận xét**: Chatbot trả lời rất thân thiện và lịch sự nhưng không thể giải quyết nhu cầu thực tế do **thiếu khả năng kết nối dữ liệu nhà trọ thời gian thực (Grounding)**.

### 🧠 ReAct Agent (Mốc 3):
* **Thought 1**: Người dùng muốn tìm phòng trọ ở Hà Nội với ngân sách dưới 3 triệu đồng/tháng. Tôi cần sử dụng công cụ `search_listings` để tìm kiếm các tin đăng phù hợp.
* **Action 1**: `search_listings("Hà Nội", 3000000, "phong_tro", None)`
* **Observation 1**: `Tìm thấy 1 kết quả: - [PT004] Phòng trọ sinh viên gần Học viện Ngân Hàng | Giá: 2,500,000 VNĐ/tháng | Khu vực: Đức Thắng, Bắc Từ Liêm, Hà Nội | 1 PN`
* **Thought 2**: Tôi đã tìm thấy một phòng trọ phù hợp với tiêu chí của người dùng. Tôi sẽ cung cấp thông tin này như một câu trả lời cuối cùng.
* **Final Answer**: *"Có, tôi tìm thấy một phòng trọ phù hợp với tiêu chí của bạn: - [PT004] Phòng trọ sinh viên gần Học viện Ngân Hàng | Giá: 2,500,000 VNĐ/tháng | Khu vực: Đức Thắng, Bắc Từ Liêm, Hà Nội | 1 PN. Bạn có muốn tìm hiểu thêm về phòng này không?"*
* **Nhận xét**: Agent hoàn thành xuất sắc nhiệm vụ trong 2 bước lặp, gọi công cụ tra cứu chính xác phòng trọ [PT004] thỏa mãn điều kiện ngân sách < 3 triệu đồng.

---

## 🛡️ 3. ĐÁNH GIÁ PHANH AN TOÀN (GUARDRAILS & SAFEGUARDS)

* **Cấu hình Guardrail**: `MAX_ITERATIONS = 3`, `TIMEOUT_SECONDS = 10`
* **Đánh giá kiểm thử Edge Cases (Test Case #8, #9, #10)**:
  * Khi gọi Tool với tham số sai hoặc mã không tồn tại (VD: mã `XX999`), Tool trả về thông báo lỗi Observation mà không gây crash chương trình (`src/tools.py`).
  * Phanh `MAX_ITERATIONS` kích hoạt ngắt lặp an toàn ngay sau 3 vòng lặp `Thought -> Action`, bảo vệ ứng dụng khỏi vòng lặp vô tận và tiết kiệm tài nguyên API.
