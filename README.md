# Đánh giá hiệu năng và độ ổn định của các phương pháp phân cụm sâu

Mở [báo cáo HTML](docs/Bao_cao_timeline_20261013.html),
[bản Word](docs/Bao_cao_timeline_20261013.docx) hoặc
[notebook có code và output](notebooks/demo_4_timeline_verified.ipynb).

Notebook đã giải thích thuật ngữ, hiển thị cấu hình, kết quả có độ lệch chuẩn,
so sánh cùng seed và bảng số liệu gốc IDEC/DECRA/BRB. Tham khảo
[hướng trình bày 7–10 phút](docs/Huong_trinh_bay_ket_qua.md).

Báo cáo được viết theo bố cục tiểu luận: tóm tắt, tổng quan, phương pháp khảo sát,
phân tích thuật toán, thực nghiệm và kết luận; có mục lục, danh mục bảng/hình và
tài liệu tham khảo đánh số. Word dùng Times New Roman 13, giãn dòng 1,5.
Log và hướng dẫn thực thi được lưu ngoài nội dung báo cáo học thuật.

Thực nghiệm chính: **DEC → IDEC → DECRA → DCSS**, cùng tệp Digits 1.797 mẫu,
5 seed, tổng 20 lượt. BRB giữ ở phần đối chiếu tài liệu. Code là bản chuyển thể
NumPy trên backbone chung; chưa chạy nguyên môi trường repo tác giả.

## Thư mục đã sắp xếp

| Thư mục | Nội dung |
|---|---|
| `src/` | Code mô hình, loss và metric |
| `scripts/` | Chuẩn bị data, thống kê survey, tạo báo cáo/notebook, chạy ablation |
| `data/` | Tệp NPZ chung, CSV xem dữ liệu, metadata và tracker 32 bài |
| `results/timeline_20261013/` | 20 lượt chính: metric, dự đoán, checkpoint, trace, biểu đồ |
| `results/dcss_width_ablation_20261013/` | 5 lượt đối chiếu độ rộng RBF, giữ riêng |
| `results/windows_22976/` | 20 lượt chạy lại ngày 16/10, đã kiểm chứng; điểm chất lượng trùng bộ chính, thời gian được đo riêng |
| `docs/` | Báo cáo mới, timeline và ghi chú kiểm tra |
| `docs/references/` | PDF/text bài báo và snapshot mã tác giả |
| `docs/reading_notes/` | Phiếu đọc toàn văn |
| `docs/original/` | Word nguồn, giữ nguyên nội dung |
| `notebooks/` | Notebook bốn phương pháp đã thực thi |
| `checks/` | Kiểm tra gradient, metric, checkpoint và bằng chứng kiểm tra |
| `requirements/` | Thư viện cho báo cáo/notebook và phiên bản đã chạy |
| `archive/` | Kết quả, báo cáo, notebook cũ và nhật ký dọn thư mục |
| `.venv/` | Môi trường Python tại máy, không đưa lên GitHub |

Cache trình duyệt/Python, ảnh preview tạm và các lượt smoke/live đã được dọn.
Hai bản Word giống hệt đã được gộp thành một bản trong `docs/original/`.
Nhật ký chuyển/xóa: [cleanup_20261013.json](archive/cleanup_20261013.json).
Code và config lúc huấn luyện được giữ trong `archive/source_snapshots/`,
để kiểm chứng hash sau khi thay đường dẫn. Số liệu và trọng số không thay đổi.

## Kết quả hiện có

| Bản chuyển thể | ACC mean ± sample std (%) | Pairwise ARI mean |
|---|---:|---:|
| DEC | 74,32 ± 8,34 | 0,650 |
| IDEC | 74,50 ± 8,07 | 0,662 |
| DECRA theo code | 70,40 ± 7,36 | 0,585 |
| DCSS theo code, sigma=1 | 51,89 ± 12,51 | 0,202 |
| DCSS bổ sung, sigma=RMS(X) | 73,64 ± 8,00 | 0,654 |

Dòng cuối là phép đối chiếu sau lượt chính, không dùng y để chọn độ rộng hoặc
tìm kiếm theo ACC. Xem [timeline khảo sát](docs/literature_timeline.md) và
[model audit](docs/model_audit.md) để hiểu khác biệt với code/paper gốc.
IDEC chỉ hơn DEC 0,18 điểm phần trăm; chưa đủ căn cứ chốt SOTA 2025–2026.

Tracker có **32 công trình: 27 hội nghị, 5 tạp chí; 16 từ năm 2023**.
Trong đó có 31 bài phương pháp và 1 bài tổng quan. Hai phiếu đọc toàn văn DEC/IDEC hoàn tất.
Theo **SJR best quartile, năm tham chiếu 2024**: Q1 = 3, Q2 = 1, Q3 = 0, Q4 = 0;
1 tạp chí chưa xác minh. Đây là phân hạng tạp chí theo năm tham chiếu, không phải Q riêng từng bài
hoặc Q tại mọi năm công bố. Nguồn SCImago được lập chỉ mục; truy cập trực tiếp hiện bị 403.
31 bài phương pháp có code và 1 bài tổng quan có thư viện/tài nguyên công khai; chưa chạy môi trường repo tác giả.
Xem [liên kết tải paper/code/data và phân hạng](docs/paper_download_links.md),
[chứng cứ Q](docs/references/journal_rankings.json),
[giải thích hoạt động thực nghiệm](docs/experimental_explanation.md).

## Chạy lại trên Windows

Nếu tải dự án từ GitHub lần đầu:

```powershell
git clone https://github.com/IzumiDKC/Deep_Clustering.git
cd Deep_Clustering
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements\notebook.txt
```

Dùng `.venv/Scripts/python.exe` đã có tại máy. Chỉ chạy thực nghiệm cần `requirements.txt`;
xuất Word dùng `requirements/report.txt`, notebook dùng `requirements/notebook.txt`.
Lệnh `-B` tránh sinh thêm cache Python. Luôn chọn thư mục output mới.

```powershell
.\.venv\Scripts\python.exe -B run_demo.py --methods DEC IDEC DECRA DCSS --seeds 0 1 2 3 4 --output results\lan_sau
.\.venv\Scripts\python.exe -B checks\verify_experiment.py --results results\lan_sau
.\.venv\Scripts\python.exe -B scripts\summarize_survey.py --output results\lan_sau\survey_counts.json
.\.venv\Scripts\python.exe -B scripts\build_review_report.py --results results\lan_sau --name Bao_cao_lan_sau
```

`run_windows.bat` đặt output trong `results/`. Mặc định runner chọn bốn
phương pháp mới. Muốn chạy cấu hình cũ, truyền rõ
`--methods AE_KMeans DEC IDEC DCN IDEC_BRB`.

Kiểm tra và tái tạo notebook từ kết quả đã có:

```powershell
.\.venv\Scripts\python.exe -B checks\check_gradients.py
.\.venv\Scripts\python.exe -B checks\check_decra.py
.\.venv\Scripts\python.exe -B checks\check_dcss.py
.\.venv\Scripts\python.exe -B scripts\build_timeline_notebook.py --execute
```

Chạy lại ablation hoặc dữ liệu khác:

```powershell
.\.venv\Scripts\python.exe -B scripts\run_dcss_calibration.py --source results\lan_sau --output results\ablation_lan_sau
.\.venv\Scripts\python.exe -B run_demo.py --data data\dataset_2.npz --dataset-name "Dataset 2" --clusters 10 --seeds 0 1 2 3 4 --output results\dataset_2
```

Dataset mới cần X hữu hạn dạng (N,D) trong [0,1] và y nguyên dạng (N,), chỉ
đánh giá. Đặt K trước khi chạy; mọi phương pháp nhận cùng X và thứ tự mẫu.
Chưa chạy dataset thứ hai/thứ ba. Nguồn và giấy phép Digits:
[README_DATA](data/README_DATA.md). Nguồn paper/code/data/Q:
[paper_tracker.csv](data/paper_tracker.csv).
