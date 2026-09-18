# Weather Lab — Ứng dụng Python thu thập và hiển thị dữ liệu thời tiết

Weather Lab phục vụ bài tập ứng dụng AI hỗ trợ lập trình Python: lấy dữ liệu thời tiết mở theo tọa độ, hiển thị trên website, xuất CSV và chia sẻ cho người dùng khác.

**Website Python đang hoạt động:** [Weather Lab trên Render](https://weather-lab-huyhung-python.onrender.com/).

## Hai phiên bản trong repository

| Nhánh | Vai trò | Nơi chạy |
| --- | --- | --- |
| [`python-backend`](https://github.com/huyhung365/Ung-dung-Python-trong-thu-thap-va-hien-thi-du-lieu/tree/python-backend) | Bản Python được trình bày trong báo cáo hiện tại | Render hoặc máy cá nhân/LAN |
| `main` | Bản HTML/CSS/JavaScript tĩnh trước đây | GitHub Pages |

GitHub lưu mã nguồn. Render chạy `app.py`. GitHub Pages chỉ phục vụ bản tĩnh và không thực thi Python. Muốn chạy hoặc nộp mã Python, hãy chọn nhánh `python-backend`.

## Chức năng và yêu cầu bài tập

- Thu thập nhiệt độ không khí ở độ cao 2 m (`temperature_2m`, °C), độ ẩm tương đối ở độ cao 2 m (`relative_humidity_2m`, %) và bức xạ sóng ngắn (`shortwave_radiation`, W/m²).
- Nhập vĩ độ từ −90 đến 90 và kinh độ từ −180 đến 180; có thể tìm địa điểm Việt Nam rồi chọn kết quả để điền tọa độ.
- Chọn 0–92 ngày quá khứ và 0–16 ngày dự báo. Số ngày dự báo tính cả hôm nay theo múi giờ địa điểm; tổng hai giá trị phải lớn hơn 0.
- Hiển thị ba biểu đồ, số dòng dữ liệu, nhiệt độ/độ ẩm trung bình, bức xạ lớn nhất và bảng theo giờ với 48 dòng mỗi trang.
- Tải đúng bộ dữ liệu đang hiển thị dưới dạng CSV.
- Chia sẻ trong cùng mạng LAN/Wi-Fi hoặc qua đường dẫn Render trên Internet.

Dữ liệu lấy từ [Open-Meteo Forecast API](https://open-meteo.com/en/docs), không phải số liệu giả lập. Dữ liệu quá khứ là dữ liệu mô hình, không mặc nhiên là đo đạc tại trạm. Bức xạ là trung bình trong giờ trước đó. Tọa độ điểm lưới nguồn có thể khác tọa độ yêu cầu; kết quả không đại diện cho trung bình toàn tỉnh/thành phố.

## Python và JavaScript làm gì

**Python** dùng thư viện chuẩn để phục vụ website, tìm địa điểm, gọi nguồn thời tiết, kiểm tra đầu vào, chuẩn hóa dữ liệu, phân loại quá khứ/dự báo, lưu snapshot và tạo CSV.

**JavaScript** nhận thao tác, hiển thị biểu đồ SVG và bảng, tính các chỉ số hiển thị, phân trang và khởi tạo tải file. Khi máy chủ bị giới hạn lượt gọi thời tiết, trình duyệt còn làm nhiệm vụ chuyển dữ liệu dự phòng về Python.

### Luồng thông thường

1. Trình duyệt gửi tọa độ và số ngày đến `GET /api/weather`.
2. Python kiểm tra tham số, dùng cache nếu còn hiệu lực hoặc gọi Open-Meteo.
3. Python kiểm tra cấu trúc, giữ timestamp UTC và giá trị thiếu, tạo snapshot có `id`.
4. JavaScript hiển thị kết quả. Nút CSV gọi `GET /api/export?id=...`; Python tạo file từ snapshot đó, không gọi lại nguồn thời tiết.

### Luồng dự phòng khi Render bị giới hạn lượt gọi

Nếu Open-Meteo trả HTTP 429, Python trả lỗi 502 có thông báo giới hạn. JavaScript nhận diện trường hợp này, gọi trực tiếp `https://api.open-meteo.com` từ trình duyệt rồi gửi JSON và tham số về `POST /api/import`.

Python tiếp tục kiểm tra, chuẩn hóa và lưu snapshot để xuất CSV qua cùng `/api/export`. Header CSP cho phép kết nối tới đúng địa chỉ Open-Meteo. Trường `source` ghi rõ `browser transport; Python processing` để phân biệt nguồn vận chuyển dữ liệu. Snapshot nhập từ trình duyệt không được đưa vào cache dùng chung cho truy vấn máy chủ.

Cơ chế này chỉ dự phòng cho lỗi giới hạn lượt gọi thời tiết, không bảo đảm xử lý mọi lỗi mạng hoặc lỗi tìm địa điểm. Nếu cả hai đường truy cập đều không hoạt động, website báo lỗi thay vì tạo dữ liệu thay thế.

## Chạy Python trên máy và chia sẻ nội bộ

Cài Python 3.10 trở lên; Visual Studio Code là tùy chọn. Lấy đúng nhánh:

```bash
git clone --branch python-backend --single-branch https://github.com/huyhung365/Ung-dung-Python-trong-thu-thap-va-hien-thi-du-lieu.git weather-lab
cd weather-lab
python app.py
```

Mở `http://localhost:8000`. Ứng dụng không cần thư viện Python bên thứ ba. Nếu tải ZIP từ GitHub, chuyển sang nhánh `python-backend` trước khi chọn Download ZIP, giải nén rồi chạy trong thư mục chứa `app.py`.

Để các thiết bị cùng mạng truy cập:

```bash
python app.py --lan
```

Dùng địa chỉ IPv4 được in trong terminal, ví dụ `http://192.168.1.10:8000`. Máy chạy Python phải tiếp tục bật, các thiết bị phải có đường kết nối trong LAN và tường lửa phải cho phép cổng sử dụng trên mạng tin cậy. Máy chủ cần Internet để gọi nguồn dữ liệu. Có thể đổi cổng bằng `--port 8001`.

## Triển khai và cập nhật Render

| Thiết lập | Giá trị |
| --- | --- |
| Loại dịch vụ | Python Web Service |
| Branch | `python-backend` |
| Build Command | `python -m pip install -r requirements.txt` |
| Start Command | `python app.py --lan --port $PORT` |
| Health Check Path | `/` |

`render.yaml` chứa cấu hình tương ứng. Các file giao diện trong nhánh GitHub nằm cùng thư mục với `app.py`; máy chủ cũng hỗ trợ thư mục `static/` trong bản đóng gói cục bộ.

Sau khi cập nhật mã trên GitHub, kiểm tra commit đang chạy ở Render. Nếu Auto-Deploy chưa bật hoặc dịch vụ vẫn chạy mã cũ, chọn **Manual Deploy → Deploy latest commit** và đợi **Live**. Sau đó tải lại website; `Ctrl + F5` giúp lấy lại tài nguyên mới. Trạng thái Live xác nhận dịch vụ đã chạy, nhưng vẫn cần thử lấy dữ liệu và tải CSV để kiểm tra chức năng.

## Vì sao dùng CSV

CSV phù hợp vì dữ liệu thời tiết có dạng bảng: mỗi dòng tương ứng một giờ, mỗi cột là một đại lượng hoặc thông tin đi kèm. Định dạng văn bản này nhỏ, dễ trao đổi và mở bằng Excel, Google Sheets, Python, MATLAB, R hoặc Power BI. CSV không lưu biểu đồ, định dạng giao diện hay nhiều worksheet.

Python xuất UTF-8 có BOM để thuận tiện mở bằng Excel. File có các cột:

```text
time_utc, timezone, period, temperature_c,
relative_humidity_percent, shortwave_radiation_w_m2,
requested_latitude, requested_longitude, grid_latitude,
grid_longitude, source, fetched_at_utc
```

Giá trị thiếu để trống trong CSV, không đổi thành 0. `period` là `past_model` hoặc `forecast`; giao diện hiển thị giờ địa phương còn CSV giữ thời gian UTC và tên múi giờ.

## Cache và giới hạn

- Cache truy vấn máy chủ có hiệu lực tối đa 10 phút. Snapshot CSV hết hạn sau 1 giờ hoặc có thể bị loại sớm khi vượt giới hạn 64 snapshot.
- Snapshot dự phòng vẫn lưu trong Python để tải CSV, nhưng không được tái sử dụng làm cache truy vấn máy chủ.
- Cache và snapshot nằm trong RAM; khởi động lại/triển khai lại sẽ xóa dữ liệu này. Nếu phiên CSV hết hạn, lấy dữ liệu lại.
- Ứng dụng cần Internet và phụ thuộc khả năng phục vụ của Open-Meteo. Nếu dịch vụ Render đang ngủ, lần mở đầu có thể phải chờ khởi động.
- Đây là ứng dụng học tập/demo, chưa có tài khoản, cơ sở dữ liệu bền vững hoặc cơ chế chia sẻ snapshot giữa nhiều tiến trình.

## Kiểm thử và kết quả xác minh

Trong nhánh Python:

```bash
python -m unittest discover -s tests -v
```

Kiểm thử bao gồm giới hạn đầu vào, dữ liệu thiếu, timestamp, cache, API, nhập dữ liệu dự phòng, CSP và CSV.

Ngày 18/09/2026, bản Render sau sửa đã được kiểm tra bằng dữ liệu Open-Meteo thật: truy vấn Hà Nội (21.0285, 105.8542), 7 ngày quá khứ và 3 ngày dự báo trả 240 dòng; dữ liệu đi qua luồng dự phòng, được Python xử lý và xuất CSV gồm 240 dòng dữ liệu cộng một dòng tiêu đề. Mã JavaScript và CSP trên website đã được đối chiếu với bản sửa. Kết quả này xác minh luồng lấy dữ liệu và xuất CSV; không phải kiểm thử mọi địa điểm hoặc mọi thiết bị.

## Tài liệu tham khảo

- [Open-Meteo Forecast API](https://open-meteo.com/en/docs)
- [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api)
- [Triển khai trên Render](https://render.com/docs/deploys)
- [Python standard library](https://docs.python.org/3/library/)

AI được sử dụng để hỗ trợ xây dựng, rà soát và sửa ứng dụng; kết quả phải được đối chiếu với mã nguồn, kiểm thử và dữ liệu thực tế.
