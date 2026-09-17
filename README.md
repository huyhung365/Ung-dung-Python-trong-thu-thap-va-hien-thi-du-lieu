# Weather Lab — GitHub Pages

Website thời tiết tiếng Việt, chạy bằng HTML/CSS/JavaScript. Giữ tìm địa điểm Việt Nam, nhập tọa độ, biểu đồ, bảng phân trang và tải CSV. Không cần Python, máy chủ riêng hoặc API key.

## Đưa web lên GitHub

1. Tạo repository Public trên GitHub, ví dụ `weather-project`.
2. Chọn **Add file → Upload files**. Tải toàn bộ nội dung thư mục này lên repository, để `index.html` nằm ngay ở thư mục gốc. Không tải file ZIP lên thay cho mã nguồn.
3. Chọn **Commit changes**.
4. Mở **Settings → Pages → Build and deployment**.
5. Ở **Source**, chọn **Deploy from a branch**; chọn nhánh **main**, thư mục **/(root)** rồi **Save**.
6. Đợi GitHub triển khai. Link website hiển thị trong Settings → Pages, thường là `https://TEN-GITHUB.github.io/weather-project/`.

Khi cập nhật các file trên nhánh đã chọn, GitHub Pages sẽ triển khai lại.

Hướng dẫn chính thức: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site

## Chạy thử

Mở `index.html` bằng trình duyệt hiện đại, có kết nối Internet. Hoặc chạy máy chủ tĩnh từ thư mục này: `python -m http.server 8000`, rồi mở `http://localhost:8000`.

## Cách hoạt động

- `weather-api.js` gọi trực tiếp Open-Meteo, kiểm tra dữ liệu, lưu đệm trong phiên tối đa 10 phút và tạo CSV từ đúng bộ dữ liệu đang hiển thị.
- `app.js` quản lý giao diện, biểu đồ, phân trang và hủy yêu cầu cũ khi thay đổi tìm kiếm.
- Đường dẫn tài nguyên tương đối nên dùng được cả website gốc lẫn website trong thư mục repository.
- CSV có UTF-8 BOM để Excel đọc tiếng Việt; giá trị thiếu để trống và thời gian xuất theo UTC kèm tên múi giờ.
- Dữ liệu quá khứ là dữ liệu mô hình, không phải đo trực tiếp. API công cộng có thể giới hạn truy cập; trang sẽ báo lỗi khi yêu cầu thất bại.
- Bản này đã chuyển phần xử lý Python sang JavaScript. Nếu bài nộp yêu cầu có Python, cần giữ riêng bản dự án Python gốc.

Nguồn: https://open-meteo.com/en/docs — địa danh: https://www.geonames.org/.
