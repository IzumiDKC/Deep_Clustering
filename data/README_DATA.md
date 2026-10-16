# Dữ liệu minh họa

Nguồn: E. Alpaydin và C. Kaynak (1998), Optical Recognition of Handwritten Digits,
UCI Machine Learning Repository. DOI: https://doi.org/10.24432/C50P49.
Trang nguồn: https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits.
Giấy phép dữ liệu: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/.

Bộ gốc UCI có 5.620 mẫu. Gói này dùng bản sao tập test 1.797 mẫu do
`sklearn.datasets.load_digits` cung cấp. Tên “test” là nguồn gốc của tập dữ liệu;
demo sử dụng toàn bộ 1.797 mẫu cho phân cụm không giám sát theo chế độ transductive.
Đây là Digits 8×8, không phải MNIST 28×28.

Tài liệu scikit-learn:
https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html.

## Tệp

- `digits_1797.npz`: `X` kích thước (1797,64), float64 đã chia 16 và nằm trong [0,1];
  `y` kích thước (1797,), int64, chỉ dùng đánh giá sau huấn luyện.
- `digits_1797.csv`: `sample_id`, 64 cột `pixel_00` đến `pixel_63` chứa giá trị gốc
  0–16, `label_evaluation_only` chứa nhãn 0–9.
- `metadata.json`: kích thước, số mẫu từng lớp, phép chuẩn hóa, nguồn, giấy phép
  và SHA-256 của NPZ.
- `paper_tracker.csv`: danh mục 32 công trình, gồm 31 bài phương pháp và 1 bài tổng quan.
  Có 27 bài hội nghị và 5 bài tạp chí; hai phiếu đọc toàn văn đã hoàn tất.
  Theo SJR best quartile năm tham chiếu 2024: 3 bài Q1, 1 bài Q2 và 1 bài tạp chí
  chưa xác minh đủ nguồn. Không gán phân hạng Q tạp chí cho hội nghị.

CSV và NPZ dùng cùng thứ tự mẫu. Có thể tạo lại ba tệp dữ liệu bằng
`python scripts/prepare_data.py`; không cần tải dữ liệu từ Internet.

K=10 được đặt trước theo giao thức benchmark. Nhãn không đi vào pretrain,
clustering, lựa chọn tham số hoặc chọn epoch. Việc tính ACC sử dụng ghép nhãn
Hungarian sau khi hoàn tất huấn luyện. NMI dùng chuẩn hóa trung bình số học.
