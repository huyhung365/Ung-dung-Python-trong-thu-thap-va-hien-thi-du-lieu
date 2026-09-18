# Weather Lab bằng Python

Bản này giữ giao diện đã duyệt và chuyển việc tìm địa điểm, thu thập dữ liệu Open-Meteo, kiểm tra dữ liệu, phân loại quá khứ/dự báo, lưu đệm và tạo CSV về máy chủ Python trong `app.py`.

JavaScript vẫn cần để nhận thao tác, vẽ biểu đồ, tính các chỉ số hiển thị và phân trang. Trình duyệt gọi `/api/locations`, `/api/weather` và `/api/export`; không gọi Open-Meteo trực tiếp.

## Chạy trên máy

Cài Python 3.10 trở lên. Mở terminal tại thư mục này rồi chạy:

```sh
python app.py
```

Mở http://localhost:8000. Trên Windows có thể chạy `start_windows.bat`.

Chia sẻ trong cùng mạng LAN: `python app.py --lan`. Thiết bị khác dùng địa chỉ IP được in trong terminal. Máy chủ cần Internet để lấy dữ liệu thời tiết.

## Chạy online trên Render

Đưa nội dung thư mục này lên một nhánh hoặc repository dành cho bản Python. Tạo Web Service Python trên Render từ repository đó:

- Build Command: `python -m pip install -r requirements.txt`
- Start Command: `python app.py --lan --port $PORT`
- Health Check Path: `/`

File `render.yaml` cũng có cấu hình Blueprint tương ứng. Kiểm tra gói dịch vụ trong giao diện Render trước khi tạo. Bản này chưa được triển khai chỉ bằng việc tải mã nguồn.

GitHub lưu mã nguồn; Render chạy tiến trình Python. Không dùng GitHub Pages để chạy `app.py`.

Tài liệu: https://render.com/docs/web-services

## Kiểm tra

```sh
python -m unittest discover -s tests -v
```

Đây là máy chủ Python standard library phục vụ đồ án/demo. Cache và phiên xuất CSV nằm trong bộ nhớ của một tiến trình; khởi động lại sẽ xóa chúng. Nếu mở rộng cho lượng truy cập lớn, cần máy chủ ứng dụng và lưu trữ phù hợp.
