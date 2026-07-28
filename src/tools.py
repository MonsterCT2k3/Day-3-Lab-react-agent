"""
src/tools.py
Role 2: Tool Engineer
Đề tài 10: Trợ Lý Tìm & Đặt Lịch Xem Nhà Trọ / Căn Hộ Cho Thuê

Nguyên tắc bắt buộc (theo docs/CODELAB.md):
- Mỗi hàm tool KHÔNG được crash khi gặp lỗi -> luôn return một string
  mô tả lỗi rõ ràng để Agent đọc được (LLM sẽ dùng chuỗi này làm Observation).
- Dữ liệu là MOCK DATA cố định (deterministic) -> không cần gọi API thật,
  không cần API key, kết quả luôn tái lập được khi demo/chấm bài.
- Mỗi hàm có docstring chuẩn (mô tả, tham số, ví dụ) để Role 3 dùng viết
  System Prompt và để LLM hiểu khi nào nên gọi tool nào.
"""

from datetime import datetime, timedelta
import random

from src.mock_db import *


# ============================================================
# 1. TOOL: search_listings
# ============================================================
def search_listings(location: str = "", price_max: int = None,
                     property_type: str = "", bedrooms: int = None) -> str:
    """
    Tìm kiếm danh sách phòng trọ / căn hộ cho thuê theo tiêu chí lọc.

    Args:
        location (str): Khu vực/quận cần tìm, ví dụ "Cầu Giấy". Để trống nếu không lọc.
        price_max (int): Giá thuê tối đa (VNĐ/tháng). None nếu không giới hạn.
        property_type (str): Loại hình - "phong_tro" | "chung_cu_mini" | "can_ho". Để trống nếu không lọc.
        bedrooms (int): Số phòng ngủ tối thiểu. None nếu không lọc.

    Returns:
        str: Danh sách các tin đăng phù hợp (listing_id, tên, giá, khu vực),
             hoặc thông báo "Không tìm thấy..." nếu không có kết quả phù hợp.

    Ví dụ:
        search_listings(location="Cầu Giấy", price_max=7000000)
    """
    try:
        results = []
        for item in LISTINGS_DB.values():
            if location and location.lower() not in item["location"].lower():
                continue
            if price_max is not None and item["price"] > price_max:
                continue
            if property_type and item["property_type"] != property_type:
                continue
            if bedrooms is not None and item["bedrooms"] < bedrooms:
                continue
            results.append(item)

        if not results:
            return ("Không tìm thấy tin đăng nào phù hợp với tiêu chí đã cho. "
                    "Hãy thử nới lỏng điều kiện (giá cao hơn hoặc khu vực khác).")

        lines = [f"Tìm thấy {len(results)} kết quả:"]
        for r in results:
            lines.append(
                f"- [{r['listing_id']}] {r['title']} | Giá: {r['price']:,} VNĐ/tháng "
                f"| Khu vực: {r['location']} | {r['bedrooms']} PN"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Lỗi khi tìm kiếm tin đăng: {str(e)}"


# ============================================================
# 2. TOOL: get_listing_detail
# ============================================================
def get_listing_detail(listing_id: str) -> str:
    """
    Lấy thông tin chi tiết của một tin đăng nhà trọ/căn hộ.

    Args:
        listing_id (str): Mã tin đăng, ví dụ "PT001".

    Returns:
        str: Thông tin chi tiết (diện tích, giá, tiện ích...) hoặc thông báo lỗi
             nếu listing_id không tồn tại.

    Ví dụ:
        get_listing_detail("PT001")
    """
    try:
        item = LISTINGS_DB.get(listing_id)
        if not item:
            valid_ids = ", ".join(LISTINGS_DB.keys())
            return (f"Không tìm thấy tin đăng với mã '{listing_id}'. "
                    f"Các mã hợp lệ hiện có: {valid_ids}")

        amenities = ", ".join(item["amenities"])
        return (
            f"Chi tiết tin đăng [{item['listing_id']}]: {item['title']}\n"
            f"- Loại hình: {item['property_type']}\n"
            f"- Khu vực: {item['location']}\n"
            f"- Giá thuê: {item['price']:,} VNĐ/tháng\n"
            f"- Diện tích: {item['area_m2']} m2, {item['bedrooms']} phòng ngủ\n"
            f"- Tiện ích: {amenities}\n"
            f"- Chủ nhà: {item['landlord_name']}"
        )
    except Exception as e:
        return f"Lỗi khi lấy chi tiết tin đăng: {str(e)}"


# ============================================================
# 3. TOOL: check_viewing_availability
# ============================================================
def check_viewing_availability(listing_id: str, date: str = "") -> str:
    """
    Kiểm tra các khung giờ còn trống để xem nhà cho một tin đăng.

    Args:
        listing_id (str): Mã tin đăng cần kiểm tra lịch.
        date (str): Ngày muốn xem, định dạng "YYYY-MM-DD". Nếu để trống,
                    mặc định kiểm tra cho ngày mai.

    Returns:
        str: Danh sách khung giờ trống, hoặc thông báo lỗi nếu listing
             không tồn tại hoặc không còn slot trống.

    Ví dụ:
        check_viewing_availability("PT001", "2026-08-01")
    """
    try:
        if listing_id not in LISTINGS_DB:
            return f"Không tìm thấy tin đăng với mã '{listing_id}' để kiểm tra lịch xem nhà."

        if not date:
            date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        slots = AVAILABLE_SLOTS.get(listing_id, [])
        # Loại bỏ các slot đã bị đặt (trong ngày được yêu cầu)
        booked = {
            a["time"] for a in APPOINTMENTS_DB.values()
            if a["listing_id"] == listing_id and a["date"] == date
            and a["status"] == "confirmed"
        }
        free_slots = [s for s in slots if s not in booked]

        if not free_slots:
            return (f"Rất tiếc, tin đăng [{listing_id}] không còn khung giờ trống "
                     f"cho ngày {date}. Vui lòng chọn ngày khác.")

        return (f"Tin đăng [{listing_id}] còn trống các khung giờ ngày {date}: "
                f"{', '.join(free_slots)}")
    except Exception as e:
        return f"Lỗi khi kiểm tra lịch xem nhà: {str(e)}"


# ============================================================
# 4. TOOL: book_viewing_appointment
# ============================================================
def book_viewing_appointment(listing_id: str, date: str, time: str,
                              customer_name: str, customer_phone: str) -> str:
    """
    Đặt lịch hẹn xem nhà cho một tin đăng cụ thể.

    Args:
        listing_id (str): Mã tin đăng.
        date (str): Ngày hẹn xem, định dạng "YYYY-MM-DD".
        time (str): Giờ hẹn xem, ví dụ "09:00". Phải nằm trong khung giờ còn trống.
        customer_name (str): Tên khách hàng đặt lịch.
        customer_phone (str): Số điện thoại liên hệ của khách hàng.

    Returns:
        str: Xác nhận đặt lịch thành công kèm mã lịch hẹn (appointment_id),
             hoặc thông báo lỗi nếu thông tin không hợp lệ / trùng lịch.

    Ví dụ:
        book_viewing_appointment("PT001", "2026-08-01", "09:00", "Nguyễn Văn A", "0909123456")
    """
    global _appointment_counter
    try:
        if listing_id not in LISTINGS_DB:
            return f"Không thể đặt lịch: mã tin đăng '{listing_id}' không tồn tại."

        if not customer_name or not customer_phone:
            return "Không thể đặt lịch: thiếu tên hoặc số điện thoại khách hàng."

        valid_slots = AVAILABLE_SLOTS.get(listing_id, [])
        if time not in valid_slots:
            return (f"Khung giờ '{time}' không hợp lệ cho tin đăng [{listing_id}]. "
                    f"Các khung giờ hợp lệ: {', '.join(valid_slots)}")

        # Kiểm tra trùng lịch
        for a in APPOINTMENTS_DB.values():
            if (a["listing_id"] == listing_id and a["date"] == date
                    and a["time"] == time and a["status"] == "confirmed"):
                return (f"Khung giờ {time} ngày {date} cho tin đăng [{listing_id}] "
                        f"đã có người đặt. Vui lòng chọn khung giờ khác.")

        _appointment_counter += 1
        appointment_id = f"APT{_appointment_counter}"
        APPOINTMENTS_DB[appointment_id] = {
            "appointment_id": appointment_id,
            "listing_id": listing_id,
            "date": date,
            "time": time,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "status": "confirmed",
        }

        listing_title = LISTINGS_DB[listing_id]["title"]
        return (f"Đặt lịch thành công! Mã lịch hẹn: {appointment_id}. "
                f"Xem nhà '{listing_title}' vào lúc {time} ngày {date}. "
                f"Vui lòng đến đúng giờ và mang theo CCCD.")
    except Exception as e:
        return f"Lỗi khi đặt lịch xem nhà: {str(e)}"


# ============================================================
# 5. TOOL: cancel_viewing_appointment
# ============================================================
def cancel_viewing_appointment(appointment_id: str) -> str:
    """
    Hủy một lịch hẹn xem nhà đã đặt trước đó.

    Args:
        appointment_id (str): Mã lịch hẹn cần hủy, ví dụ "APT1001".

    Returns:
        str: Thông báo hủy thành công, hoặc lỗi nếu mã lịch hẹn không tồn tại
             / đã bị hủy trước đó.

    Ví dụ:
        cancel_viewing_appointment("APT1001")
    """
    try:
        appt = APPOINTMENTS_DB.get(appointment_id)
        if not appt:
            return f"Không tìm thấy lịch hẹn với mã '{appointment_id}'."

        if appt["status"] == "cancelled":
            return f"Lịch hẹn '{appointment_id}' đã được hủy trước đó rồi."

        appt["status"] = "cancelled"
        return f"Đã hủy thành công lịch hẹn '{appointment_id}'."
    except Exception as e:
        return f"Lỗi khi hủy lịch hẹn: {str(e)}"


# ============================================================
# 6. TOOL: list_my_appointments
# ============================================================
def list_my_appointments(customer_phone: str) -> str:
    """
    Tra cứu toàn bộ lịch hẹn xem nhà theo số điện thoại khách hàng.

    Args:
        customer_phone (str): Số điện thoại của khách hàng.

    Returns:
        str: Danh sách các lịch hẹn (mã, tin đăng, ngày giờ, trạng thái),
             hoặc thông báo nếu không tìm thấy lịch hẹn nào.

    Ví dụ:
        list_my_appointments("0909123456")
    """
    try:
        my_appts = [a for a in APPOINTMENTS_DB.values()
                    if a["customer_phone"] == customer_phone]
        if not my_appts:
            return f"Không tìm thấy lịch hẹn nào gắn với số điện thoại '{customer_phone}'."

        lines = [f"Danh sách lịch hẹn của SĐT {customer_phone}:"]
        for a in my_appts:
            title = LISTINGS_DB.get(a["listing_id"], {}).get("title", a["listing_id"])
            lines.append(
                f"- [{a['appointment_id']}] {title} | {a['date']} {a['time']} "
                f"| Trạng thái: {a['status']}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Lỗi khi tra cứu lịch hẹn: {str(e)}"


# ============================================================
# 7. TOOL: get_landlord_contact
# ============================================================
def get_landlord_contact(listing_id: str) -> str:
    """
    Lấy thông tin liên hệ của chủ nhà/môi giới cho một tin đăng.

    Args:
        listing_id (str): Mã tin đăng.

    Returns:
        str: Tên và số điện thoại chủ nhà, hoặc lỗi nếu không tìm thấy tin đăng.

    Ví dụ:
        get_landlord_contact("CC002")
    """
    try:
        item = LISTINGS_DB.get(listing_id)
        if not item:
            return f"Không tìm thấy tin đăng với mã '{listing_id}'."
        return (f"Liên hệ chủ nhà tin đăng [{listing_id}]: {item['landlord_name']} "
                f"- SĐT: {item['landlord_phone']}")
    except Exception as e:
        return f"Lỗi khi lấy thông tin liên hệ chủ nhà: {str(e)}"


# ============================================================
# 8. TOOL: calculate_distance
# ============================================================
def calculate_distance(listing_id: str, destination: str) -> str:
    """
    Ước tính khoảng cách đường chim bay từ một tin đăng đến một địa điểm tham chiếu.

    Args:
        listing_id (str): Mã tin đăng.
        destination (str): Tên địa điểm đích, ví dụ "đại học bách khoa", "hồ gươm",
                            "sân bay nội bài" (không phân biệt hoa/thường).

    Returns:
        str: Khoảng cách ước tính (km), hoặc lỗi nếu listing/địa điểm không hợp lệ.

    Ví dụ:
        calculate_distance("PT001", "đại học bách khoa")
    """
    try:
        item = LISTINGS_DB.get(listing_id)
        if not item:
            return f"Không tìm thấy tin đăng với mã '{listing_id}'."

        key = destination.strip().lower()
        dest_coords = REFERENCE_POINTS.get(key)
        if not dest_coords:
            valid = ", ".join(REFERENCE_POINTS.keys())
            return (f"Không hỗ trợ tính khoảng cách tới '{destination}'. "
                    f"Các địa điểm tham chiếu hỗ trợ: {valid}")

        # Công thức khoảng cách Euclid xấp xỉ trên tọa độ (đơn giản hoá cho mock data)
        lat1, lng1 = item["lat"], item["lng"]
        lat2, lng2 = dest_coords
        # 1 độ vĩ/kinh ~ 111 km (xấp xỉ, đủ dùng cho demo)
        dist_km = round((((lat1 - lat2) ** 2 + (lng1 - lng2) ** 2) ** 0.5) * 111, 1)

        return (f"Khoảng cách ước tính từ tin đăng [{listing_id}] đến "
                f"'{destination}' là khoảng {dist_km} km.")
    except Exception as e:
        return f"Lỗi khi tính khoảng cách: {str(e)}"


# ============================================================
# 9. TOOL (mở rộng): get_neighborhood_info
# ============================================================
def get_neighborhood_info(listing_id: str) -> str:
    """
    Cung cấp thông tin mô tả khu vực xung quanh một tin đăng (an ninh, tiện ích lân cận).

    Args:
        listing_id (str): Mã tin đăng.

    Returns:
        str: Mô tả khu vực (mock), hoặc lỗi nếu tin đăng không tồn tại.

    Ví dụ:
        get_neighborhood_info("CH003")
    """
    try:
        item = LISTINGS_DB.get(listing_id)
        if not item:
            return f"Không tìm thấy tin đăng với mã '{listing_id}'."

        # Mock mô tả cố định để demo, tránh phụ thuộc API bản đồ thật
        mock_notes = {
            "PT001": "Gần chợ sinh viên, nhiều quán ăn bình dân, an ninh khá tốt, có camera hẻm.",
            "CC002": "Gần trung tâm thương mại, đường lớn dễ đi, hơi ồn vào giờ cao điểm.",
            "CH003": "Khu dân cư mới, yên tĩnh, gần trường học và công viên, an ninh tốt.",
            "PT004": "Gần trường đại học, nhiều dịch vụ photocopy/tạp hóa, phù hợp sinh viên.",
        }
        note = mock_notes.get(listing_id, "Chưa có dữ liệu mô tả khu vực cho tin đăng này.")
        return f"Thông tin khu vực quanh tin đăng [{listing_id}] ({item['location']}): {note}"
    except Exception as e:
        return f"Lỗi khi lấy thông tin khu vực: {str(e)}"


# ============================================================
# 10. TOOL (mở rộng): compare_listings
# ============================================================
def compare_listings(listing_ids: list) -> str:
    """
    So sánh nhanh 2-3 tin đăng theo giá, diện tích và số phòng ngủ.

    Args:
        listing_ids (list[str]): Danh sách 2-3 mã tin đăng cần so sánh.

    Returns:
        str: Bảng so sánh dạng text, hoặc lỗi nếu danh sách không hợp lệ.

    Ví dụ:
        compare_listings(["PT001", "CC002"])
    """
    try:
        if not listing_ids or len(listing_ids) < 2:
            return "Cần ít nhất 2 mã tin đăng để so sánh."
        if len(listing_ids) > 3:
            return "Chỉ hỗ trợ so sánh tối đa 3 tin đăng cùng lúc."

        rows = []
        missing = []
        for lid in listing_ids:
            item = LISTINGS_DB.get(lid)
            if not item:
                missing.append(lid)
                continue
            rows.append(
                f"[{lid}] {item['title']} | Giá: {item['price']:,} VNĐ "
                f"| DT: {item['area_m2']}m2 | PN: {item['bedrooms']}"
            )

        if missing:
            return f"Không tìm thấy các mã tin đăng sau: {', '.join(missing)}."

        return "So sánh các tin đăng:\n" + "\n".join(rows)
    except Exception as e:
        return f"Lỗi khi so sánh tin đăng: {str(e)}"


# ============================================================
# 11. TOOL REGISTRY - dùng cho Role 3 (prompts.py) & Role 4 (app.py)
# ============================================================
# Mỗi entry mô tả tool theo dạng function-calling schema đơn giản,
# để LLM biết tên tool, mô tả và tham số cần truyền khi sinh Action.

TOOL_REGISTRY = {
    "search_listings": search_listings,
    "get_listing_detail": get_listing_detail,
    "check_viewing_availability": check_viewing_availability,
    "book_viewing_appointment": book_viewing_appointment,
    "cancel_viewing_appointment": cancel_viewing_appointment,
    "list_my_appointments": list_my_appointments,
    "get_landlord_contact": get_landlord_contact,
    "calculate_distance": calculate_distance,
    "get_neighborhood_info": get_neighborhood_info,
    "compare_listings": compare_listings,
}

TOOL_SPECS = [
    {
        "name": "search_listings",
        "description": "Tìm phòng trọ/căn hộ theo khu vực, giá tối đa, loại hình, số phòng ngủ.",
        "parameters": ["location", "price_max", "property_type", "bedrooms"],
    },
    {
        "name": "get_listing_detail",
        "description": "Lấy thông tin chi tiết đầy đủ của 1 tin đăng theo listing_id.",
        "parameters": ["listing_id"],
    },
    {
        "name": "check_viewing_availability",
        "description": "Kiểm tra khung giờ còn trống để xem nhà của 1 tin đăng theo ngày.",
        "parameters": ["listing_id", "date"],
    },
    {
        "name": "book_viewing_appointment",
        "description": "Đặt lịch hẹn xem nhà cho 1 tin đăng vào ngày giờ cụ thể.",
        "parameters": ["listing_id", "date", "time", "customer_name", "customer_phone"],
    },
    {
        "name": "cancel_viewing_appointment",
        "description": "Hủy lịch hẹn xem nhà đã đặt trước đó theo appointment_id.",
        "parameters": ["appointment_id"],
    },
    {
        "name": "list_my_appointments",
        "description": "Tra cứu tất cả lịch hẹn xem nhà của khách theo số điện thoại.",
        "parameters": ["customer_phone"],
    },
    {
        "name": "get_landlord_contact",
        "description": "Lấy thông tin liên hệ chủ nhà/môi giới của 1 tin đăng.",
        "parameters": ["listing_id"],
    },
    {
        "name": "calculate_distance",
        "description": "Ước tính khoảng cách từ 1 tin đăng đến 1 địa điểm tham chiếu.",
        "parameters": ["listing_id", "destination"],
    },
    {
        "name": "get_neighborhood_info",
        "description": "Lấy thông tin mô tả khu vực xung quanh 1 tin đăng.",
        "parameters": ["listing_id"],
    },
    {
        "name": "compare_listings",
        "description": "So sánh 2-3 tin đăng theo giá, diện tích, số phòng ngủ.",
        "parameters": ["listing_ids"],
    },
]


# ============================================================
# 12. SELF-TEST - chạy trực tiếp file này để kiểm tra nhanh
# ============================================================
if __name__ == "__main__":
    print("=== TEST search_listings ===")
    print(search_listings(location="Hà Nội", price_max=7000000))
    print("\n=== TEST get_listing_detail (hợp lệ) ===")
    print(get_listing_detail("PT001"))
    print("\n=== TEST get_listing_detail (lỗi - mã không tồn tại) ===")
    print(get_listing_detail("XX999"))
    print("\n=== TEST check_viewing_availability ===")
    print(check_viewing_availability("PT001", "2026-08-01"))
    print("\n=== TEST book_viewing_appointment (hợp lệ) ===")
    print(book_viewing_appointment("PT001", "2026-08-01", "09:00", "Nguyễn Văn A", "0909123456"))
    print("\n=== TEST book_viewing_appointment (trùng lịch) ===")
    print(book_viewing_appointment("PT001", "2026-08-01", "09:00", "Trần Thị B", "0909999888"))
    print("\n=== TEST book_viewing_appointment (giờ không hợp lệ) ===")
    print(book_viewing_appointment("PT001", "2026-08-01", "23:00", "Trần Thị B", "0909999888"))
    print("\n=== TEST list_my_appointments ===")
    print(list_my_appointments("0909123456"))
    print("\n=== TEST cancel_viewing_appointment ===")
    print(cancel_viewing_appointment("APT1001"))
    print("\n=== TEST get_landlord_contact ===")
    print(get_landlord_contact("CC002"))
    print("\n=== TEST calculate_distance ===")
    print(calculate_distance("PT001", "đại học bách khoa"))
    print("\n=== TEST get_neighborhood_info ===")
    print(get_neighborhood_info("CH003"))
    print("\n=== TEST compare_listings ===")
    print(compare_listings(["PT001", "CC002", "CH003"]))
    print("\n=== TEST compare_listings (lỗi - thiếu mã) ===")
    print(compare_listings(["PT001"]))