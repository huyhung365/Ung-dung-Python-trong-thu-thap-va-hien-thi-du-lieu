# Ung-dung-Python-trong-thu-thap-va-hien-thi-du-lieu
Thu thập dữ liệu thời tiết từ các trang web mở, gồm: nhiệt độ, độ ẩm, cường độ bức xạ mặt trời Hiển thị dữ liệu dưới dạng website, cho phép nhập tọa độ điểm cần lấy dữ liệu, cho phép chọn số ngày dữ liệu quá khứ và số ngày của dữ liệu dự báo. Cho phép tải về file .csv (cần làm rõ tại sao sử dụng định dạng .csv)


## Website chạy khi máy tác giả tắt

GitHub Pages phục vụ website trong thư mục `docs`. Python chạy trên trình duyệt người xem bằng Pyodide 314.0.7, tải từ CDN jsDelivr. Người xem cần Internet; lần đầu tải công cụ Python có thể lâu hơn các lần sau.

**Người thực hiện:** NGUYEN HUY HUNG — Đại học Bách khoa Hà Nội.

### Bật website

1. Vào **Settings → Pages** của repository này.
2. Chọn **Deploy from a branch**, nhánh **main**, thư mục **/docs**, rồi **Save**.
3. Đợi GitHub báo xuất bản thành công và dùng đường dẫn được hiển thị tại đó.

### Mã nguồn

- `docs/weather.py`: Python lấy ba đại lượng từ Open-Meteo, kiểm tra tọa độ, chuẩn hóa và xuất CSV.
- `docs/python-bridge.js`: khởi động Python bằng Pyodide và kết nối giao diện.
- `docs/index.html`, `docs/style.css`, `docs/app.js`: giao diện, biểu đồ, bảng và tìm tỉnh/thành phố.
- `docs/logo_hust.jpg`: logo trường.

Python không chạy như một HTTP server trên GitHub Pages. Để thử trên VS Code: chạy `py -m http.server 8000` tại thư mục gốc rồi mở `http://localhost:8000/docs/`.

### Chức năng và cách kiểm tra

- Nhập tọa độ hoặc tìm tỉnh/thành phố tại Việt Nam.
- Chọn 0–92 ngày quá khứ và 0–16 ngày dự báo; dự báo tính cả hôm nay.
- Xem nhiệt độ (°C), độ ẩm (%) và bức xạ mặt trời (W/m²).
- Tải CSV rồi mở trong Excel, Python hoặc MATLAB. CSV phù hợp vì dữ liệu dạng bảng, nhẹ, dễ trao đổi và phân tích; không lưu biểu đồ hay định dạng màu sắc.
- Thử mở đường dẫn trên điện thoại bằng Wi-Fi khác hoặc 4G/5G.

Dữ liệu quá khứ là dữ liệu mô hình lưu trữ, không phải phép đo cảm biến tại chỗ. AI đã hỗ trợ lập trình và kiểm tra mã. Sinh viên cần tự chạy thử và bổ sung minh chứng. Bản GitHub Pages chia sẻ qua Internet; minh chứng LAN có thể dùng bản `app.py --lan` của dự án ban đầu.

### Tài liệu

- https://open-meteo.com/en/docs
- https://pyodide.org/en/stable/usage/quickstart.html
- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
