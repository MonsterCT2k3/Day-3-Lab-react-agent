LISTINGS_DB = {
    "PT001": {
        "listing_id": "PT001",
        "title": "Phòng trọ khép kín gần Đại học Bách Khoa",
        "property_type": "phong_tro",
        "location": "Hai Bà Trưng, Hà Nội",
        "price": 3200000,
        "area_m2": 20,
        "bedrooms": 1,
        "amenities": ["wifi", "gác lửng", "chỗ để xe", "an ninh 24/7"],
        "landlord_name": "Cô Lan",
        "landlord_phone": "0912345678",
        "lat": 21.0055,
        "lng": 105.8430,
    },
    "CC002": {
        "listing_id": "CC002",
        "title": "Chung cư mini 1 phòng ngủ khu Cầu Giấy",
        "property_type": "chung_cu_mini",
        "location": "Cầu Giấy, Hà Nội",
        "price": 6500000,
        "area_m2": 35,
        "bedrooms": 1,
        "amenities": ["thang máy", "điều hòa", "máy giặt chung", "bảo vệ"],
        "landlord_name": "Anh Tuấn",
        "landlord_phone": "0987654321",
        "lat": 21.0333,
        "lng": 105.7900,
    },
    "CH003": {
        "listing_id": "CH003",
        "title": "Căn hộ 2 phòng ngủ full nội thất Nam Từ Liêm",
        "property_type": "can_ho",
        "location": "Nam Từ Liêm, Hà Nội",
        "price": 9800000,
        "area_m2": 65,
        "bedrooms": 2,
        "amenities": ["hồ bơi", "gym", "hầm để xe", "ban công"],
        "landlord_name": "Chị Hoa",
        "landlord_phone": "0977111222",
        "lat": 21.0180,
        "lng": 105.7650,
    },
    "PT004": {
        "listing_id": "PT004",
        "title": "Phòng trọ sinh viên gần Học viện Ngân Hàng",
        "property_type": "phong_tro",
        "location": "Đức Thắng, Bắc Từ Liêm, Hà Nội",
        "price": 2500000,
        "area_m2": 16,
        "bedrooms": 1,
        "amenities": ["wifi", "tủ quần áo", "chỗ để xe"],
        "landlord_name": "Chú Bình",
        "landlord_phone": "0966333444",
        "lat": 21.0500,
        "lng": 105.7800,
    },
}

# Lịch xem nhà còn trống theo listing_id -> danh sách khung giờ mẫu
AVAILABLE_SLOTS = {
    "PT001": ["09:00", "14:00", "16:30"],
    "CC002": ["10:00", "15:00"],
    "CH003": ["09:30", "13:00", "17:00"],
    "PT004": ["08:30", "11:00", "14:30"],
}

# Bộ nhớ tạm cho các lịch hẹn đã đặt (dict: appointment_id -> info)
APPOINTMENTS_DB = {}
_appointment_counter = 1000

# Địa điểm tham chiếu để tính khoảng cách (mock, không dùng API bản đồ thật)
REFERENCE_POINTS = {
    "đại học bách khoa": (21.0053, 105.8434),
    "hồ gươm": (21.0285, 105.8542),
    "sân bay nội bài": (21.2212, 105.8072),
}