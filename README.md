# Weather Lab

Ứng dụng Python thu thập và hiển thị dữ liệu thời tiết theo tọa độ.

## Mục tiêu

Ứng dụng đáp ứng các yêu cầu chính của bài tập:

- Thu thập nhiệt độ, độ ẩm tương đối và cường độ bức xạ mặt trời từ nguồn dữ liệu mở Open-Meteo.
- Cho phép nhập vĩ độ, kinh độ, số ngày dữ liệu quá khứ và số ngày dự báo.
- Hiển thị dữ liệu trên website bằng biểu đồ, số liệu tổng hợp và bảng dữ liệu theo giờ.
- Cho phép tải toàn bộ bộ dữ liệu đang hiển thị dưới dạng file `.csv`.
- Cho phép chia sẻ website trong cùng mạng LAN/Wi-Fi để nhiều người dùng cùng truy cập.

## Công nghệ

- Python standard library: máy chủ HTTP, gọi API, kiểm tra dữ liệu, cache và tạo CSV.
- HTML/CSS/JavaScript: giao diện, biểu đồ SVG, phân trang và thao tác tải file.
- Open-Meteo Forecast API: dữ liệu thời tiết theo giờ.
- Open-Meteo Geocoding API: tìm địa điểm Việt Nam và điền tọa độ.
- Git/GitHub: lưu trữ và quản lý mã nguồn.

## Chạy bản Python trên máy

Cài Python 3.10 trở lên và mở terminal trong thư mục chứa `app.py`:

```bash
python app.py
```

Mở `http://localhost:8000`.

Để chia sẻ nội bộ cho người dùng cùng mạng LAN hoặc Wi-Fi:

```bash
python app.py --lan
```

Dùng địa chỉ IP và cổng được in trong terminal, ví dụ `http://192.168.1.10:8000`. Máy chạy Python phải tiếp tục bật và có Internet để gọi Open-Meteo.

## CSV được dùng để làm gì?

CSV phù hợp với dữ liệu thời tiết vì dữ liệu có dạng bảng: mỗi dòng là một thời điểm và các cột là nhiệt độ, độ ẩm, bức xạ cùng thông tin nguồn. File nhỏ, dễ chia sẻ và mở được bằng Excel, Google Sheets, Python, MATLAB, R hoặc Power BI. CSV giữ dữ liệu và đơn vị nhưng không giữ biểu đồ hay định dạng giao diện.

## Phiên bản trực tuyến

GitHub Pages chỉ chạy được file tĩnh HTML/CSS/JavaScript, nên không chạy `app.py`. Bản Python được triển khai như một Web Service trên Render:

- Website Python: https://weather-lab-huyhung-python.onrender.com/
- Nhánh mã nguồn: `python-backend`
- Build command: `python -m pip install -r requirements.txt`
- Start command: `python app.py --lan --port $PORT`

Bản Render phù hợp để chia sẻ qua Internet. Bản chạy `--lan` phù hợp để chia sẻ nội bộ trong cùng mạng.

## Kiểm thử

```bash
python -m unittest discover -s tests -v
```

Các kiểm thử bao gồm kiểm tra giới hạn tọa độ và số ngày, dữ liệu thiếu, mốc ngày theo múi giờ, cache, API route và CSV.
