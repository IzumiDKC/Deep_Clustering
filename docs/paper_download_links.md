# Paper, mã nguồn, dữ liệu và bằng chứng phân hạng — 13/10/2026

Danh mục có 32 công trình: 31 bài phương pháp và 1 bài tổng quan, gồm 27 bài hội nghị và 5 bài tạp chí.
Hai bài mới được bổ sung ở cuối bảng. Các bài dưới đây phục vụ lựa chọn timeline và lý giải kết quả;
toàn bộ 32 bài cùng nguồn riêng nằm trong [paper_tracker.csv](../data/paper_tracker.csv).
Chỉ DEC/IDEC đã hoàn tất phiếu đọc toàn văn. Kiểm tra metadata, code hoặc một bảng kết quả chưa được
tính thành đọc toàn văn hoàn tất.

| Công trình / vai trò | Trang công bố | PDF để tải | Mã tác giả / tài nguyên |
|---|---|---|---|
| DEC, ICML 2016 — baseline | [PMLR](https://proceedings.mlr.press/v48/xieb16.html) | [PDF chính thức](https://proceedings.mlr.press/v48/xieb16.pdf) | [piiswrong/dec](https://github.com/piiswrong/dec) |
| IDEC, IJCAI 2017 — bài target | [IJCAI](https://www.ijcai.org/proceedings/2017/243) | [PDF chính thức](https://www.ijcai.org/proceedings/2017/0243.pdf) | [XifengGuo/IDEC](https://github.com/XifengGuo/IDEC) |
| DECRA, Neural Processing Letters 2024 — nhánh residual/adaptive | [Springer / DOI](https://doi.org/10.1007/s11063-024-11586-0) | [PDF publisher](https://link.springer.com/content/pdf/10.1007/s11063-024-11586-0.pdf) | [lml-mengli/DECRA](https://github.com/lml-mengli/DECRA) |
| BRB, ICLR 2025 — đối chiếu số liệu, phương pháp còn có thể thay | [ICLR](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f91685b940d5032f0f0c247edbd72edd-Abstract-Conference.html) | [PDF chính thức](https://proceedings.iclr.cc/paper_files/paper/2025/file/f91685b940d5032f0f0c247edbd72edd-Paper-Conference.pdf) | [Breaking the Reclustering Barrier](https://github.com/Probabilistic-and-Interactive-ML/breaking-the-reclustering-barrier) |
| DCSS, Machine Learning 2026 — ứng viên cùng họ AE | [Springer / DOI](https://link.springer.com/article/10.1007/s10994-026-07026-w) | [PDF publisher](https://link.springer.com/content/pdf/10.1007/s10994-026-07026-w.pdf) | [gvardakas/Soft-Silhouette](https://github.com/gvardakas/Soft-Silhouette) |
| DKM, Pattern Recognition Letters 2020 — bổ sung so sánh tối ưu và khởi tạo | [DOI / journal](https://doi.org/10.1016/j.patrec.2020.07.028) | [Preprint tác giả](https://arxiv.org/pdf/1806.10069); [bản đã lưu](references/survey_papers/DKM_2020_preprint.pdf) | [MaziarMF/deep-k-means](https://github.com/MaziarMF/deep-k-means) |
| A Comprehensive Survey on Deep Clustering, ACM Computing Surveys — bổ sung tổng quan | [DOI](https://doi.org/10.1145/3689036) | [Bản tác giả](https://mn.cs.tsinghua.edu.cn/xinwang/PDF/papers/2024_A%20Comprehensive%20Survey%20on%20Deep%20Clustering%20Taxonomy%20Challenges%20and%20Future%20Directions.pdf); [bản đã lưu](references/survey_papers/DeepClusteringSurvey_ACM_2025_authorcopy.pdf) | [Danh mục tác giả](https://github.com/zhoushengisnoob/DeepClustering); [OpenDeepClustering](https://github.com/zhoushengisnoob/OpenDeepClustering) |

DKM có preprint 2018 và bản journal 2020; chỉ tính một công trình. Số liệu mới trích xuất cho DKM
lấy từ Table 2 của preprint v2: MNIST, DKMp ACC 84,0 ± 2,2%; IDECp 85,7 ± 2,4%; 10 lần chạy.
Tác giả chọn siêu tham số bằng nhãn của 10% validation và báo cáo phần 90% còn lại;
cấu hình này khác demo Digits. Chưa đối chiếu Table 2 với bản journal cuối cùng, chưa chạy DKM tại máy này.

DECRA có số liệu trực tiếp từ [Table 2](https://link.springer.com/article/10.1007/s11063-024-11586-0/tables/2):
MNIST, ACC của DEC 84,7%, IDEC 88,1%, DECRA 96,4%; [Table 3](https://link.springer.com/article/10.1007/s11063-024-11586-0/tables/3)
cho NMI lần lượt 79,1%, 86,7%, 91,7%. Các bảng không có cột std/SE và dùng NMI chuẩn hóa bằng maximum entropy.
Không dùng chúng làm số đo độ ổn định của demo Digits. [Bản ghi trích xuất](references/decra_reported_results.json).

Bài ACM online 2024, issue 57(3), Article 69, tháng 3/2025; tracker dùng năm issue 2025,
không đếm preprint thành bài thứ hai. Đây là bài tổng quan, cung cấp cách phân loại theo tương tác
giữa học biểu diễn và phân cụm, danh mục benchmark, metric và thư viện, không phải thuật toán thứ năm
trong bảng thực nghiệm. [Bản ghi của đồng tác giả tại Macquarie](https://researchers.mq.edu.au/en/publications/a-comprehensive-survey-on-deep-clustering-taxonomy-challenges-and/).

## Q để đưa vào báo cáo

Bảng chính dùng cùng hệ thống **SCImago/SJR, năm tham chiếu 2024, best quartile của tạp chí**.
Đây là phân hạng tốt nhất trong các ngành của tạp chí, không phải Q riêng từng bài hay Q ở mọi năm xuất bản.
Không gán Q1–Q4 của tạp chí cho bài hội nghị. Không trộn JCR, CiteScore và SJR.

| Công trình trong tracker | Năm bài | Tạp chí | SJR best quartile 2024 | Nguồn SCImago |
|---|---:|---|---|---|
| P07 DECRA | 2024 | Neural Processing Letters | Q2 | [Danh sách 2024](https://www.scimagojr.com/journalrank.php?country=NL&min=1&min_type=cd&ord=desc&order=titem&page=11&total_size=2130) |
| P17 ProPos | 2023 | IEEE TPAMI | Q1 | [Danh sách 2024](https://www.scimagojr.com/journalrank.php?country=Northern+America&ord=desc&order=tc&page=2&total_size=5171&wos=true) |
| P21 DCSS | 2026 | Machine Learning | Chưa xác minh đủ nguồn chính | [Bản ghi cần kiểm tra](https://www.scimagojr.com/journalsearch.php?q=24775&tip=sid) |
| P31 DKM | 2020 | Pattern Recognition Letters | Q1 | [Hồ sơ và bảng ngành/năm](https://www.scimagojr.com/journalsearch.php/journalsearch.php?q=24825&tip=sid) |
| P32 Survey-ACM | 2025 | ACM Computing Surveys | Q1 | [Danh sách 2024](https://www.scimagojr.com/journalrank.php?country=OECD&page=12&total_size=24095) |

Tổng trên 5 bài tạp chí: **Q1 = 3 (60%), Q2 = 1 (20%), Q3 = 0, Q4 = 0, chưa xác minh = 1 (20%)**.
Nguồn dùng được là nội dung chính chủ SCImago đã được lập chỉ mục; truy cập trực tiếp hiện bị 403/bot_blocked.
Đã lưu số liệu, năm, scope và giới hạn truy cập tại [journal_rankings.json](references/journal_rankings.json).
Đây là năm tham chiếu có bằng chứng đồng nhất, không được gọi là phân hạng mới nhất 2026.

Ví dụ cần giải thích khi báo cáo: Pattern Recognition Letters năm 2024 có **best quartile Q1**,
nhưng riêng ngành **Artificial Intelligence là Q2**; ngành Computer Vision and Pattern Recognition là Q1.
Ở năm công bố DKM 2020, ngành AI cũng Q2. Các dòng này được lưu riêng, không cộng lại vào tổng Q ở trên.

## Nguồn data và cách chạy

Thực nghiệm hiện dùng [digits_1797.npz](../data/digits_1797.npz), được tạo bằng
[scikit-learn load_digits](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html),
nguồn gốc [UCI Optical Recognition of Handwritten Digits](https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits).
Bản scikit-learn có 1.797 ảnh 8×8, 64 đặc trưng, 10 lớp; khác bộ UCI đầy đủ 5.620 mẫu.
Pixel chia 16 để vào [0,1]. Nhãn chỉ tính ACC/NMI/ARI, không đưa vào loss hoặc khởi tạo RBF.
[Metadata, hash và giấy phép](../data/README_DATA.md).

Mọi phương pháp đọc cùng tệp, cùng thứ tự 1.797 mẫu, 5 seed 0–4, cùng autoencoder và khởi tạo
K-means trong từng seed: pretrain 120 epoch, clustering 60 epoch, batch 128, Adam 0,001.
Chạy trong PowerShell tại thư mục Deep_Clustering_Demo:

```powershell
.\.venv\Scripts\python.exe -B run_demo.py --methods DEC IDEC DECRA DCSS --seeds 0 1 2 3 4 --output results\lan_sau
.\.venv\Scripts\python.exe -B checks\verify_experiment.py --results results\lan_sau
```

[Notebook có code/output](../notebooks/demo_4_timeline_verified.ipynb),
[giải thích từng bước và ưu/nhược điểm](experimental_explanation.md),
[20 lượt kết quả chính](../results/timeline_20261013/summary.csv).
Đây là các bản chuyển thể NumPy trên kiến trúc chung; chưa chạy nguyên môi trường repo tác giả,
chưa thể dùng để tuyên bố mô hình mạnh nhất toàn lĩnh vực năm 2025/2026.

## Đưa vào thư mục Drive

Google Drive chưa được kết nối trong phiên làm việc, nên chưa tải tệp lên
[thư mục bạn cung cấp](https://drive.google.com/drive/folders/1K6GxxIWpCuRcmSWB7_aBLXS8kS1BSaQ3).
Bạn có thể tải hai PDF đã lưu ở bảng trên và đưa vào thư mục này; báo cáo Word/HTML và toàn bộ
liên kết nguồn đã sẵn trong dự án. Hai PDF bổ sung có hash trong
[survey_additions_20261013.json](references/survey_additions_20261013.json).
