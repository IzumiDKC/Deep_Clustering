# Cập nhật khảo sát ngày 13/10/2026

Tracker hiện có **32 công trình: 27 hội nghị, 5 tạp chí; 16 từ 2023**. Gồm 31 bài phương pháp và 1 bài tổng quan;
hai phiếu đọc toàn văn DEC/IDEC đã hoàn tất. 31 bài phương pháp có code, 1 bài tổng quan có thư viện/tài nguyên công khai;
0 môi trường repo tác giả đã chạy. Xem [timeline mới](literature_timeline.md),
[báo cáo mới](Bao_cao_timeline_20261013.html), [tracker](../data/paper_tracker.csv).

Phân hạng chính dùng SCImago/SJR **best quartile, năm tham chiếu 2024**: Q1 = 3, Q2 = 1, Q3 = 0,
Q4 = 0, chưa xác minh = 1. Bằng chứng được lập chỉ mục từ trang SCImago; truy cập trực tiếp bị 403.
Năm tham chiếu không nhất thiết là năm công bố. Không gán Q tạp chí cho hội nghị. Riêng PRLetters,
Q2 ngành AI năm 2020/2024 được ghi riêng, không trộn vào tổng best quartile 2024.
[Chứng cứ chi tiết](references/journal_rankings.json); [paper và liên kết tải](paper_download_links.md).

Các mục bên dưới là **bản kiểm tra lịch sử ngày12/10/2026**, có8 ứng viên và25 lượt demo. Không dùng các số lịch sử làm thống kê hiện tại.

---

# Kiểm tra khảo sát và mức đáp ứng báo cáo Word

Ngày đối chiếu: **12/10/2026**. Nguồn nội bộ: Word gốc, `data/paper_tracker.csv`, code và kết quả trong gói. Hai bản Word ở thư mục cha và `docs/` có cùng SHA-256 `e726f8ceb245e2f5017e7fe6eee95f513611497699074d18cf0a7790f17162fb`; đợt kiểm tra này giữ nguyên cả hai.

**Bộ minh họa đã chạy được trên một tệp dữ liệu chung. Khảo sát toàn văn và tái hiện kết quả bài báo gốc chưa hoàn thành.** Tám dòng tracker là tám công trình đã đối chiếu định danh, nơi công bố và repo; việc kiểm tra các mục dataset/README không được tính thành một lượt đọc toàn văn có hệ thống.

## Số lượng hiện có

Số liệu được tạo lại bằng `summarize_survey.py` tại [survey_counts.json](../archive/results_verified_20261012/survey_counts.json).

| Hạng mục | Số lượng | Cách hiểu |
|---|---:|---|
| Bài được liệt kê, không trùng ID/URL | 8 | Danh sách khởi đầu |
| Định danh/năm/nơi công bố đã đối chiếu nguồn chính | 8 | Chưa đồng nghĩa đã khảo sát toàn văn |
| Bài hội nghị | 7 (87,5%) | ICML 2; IJCAI 1; ACML 1; ECCV 1; AAAI 1; ICLR 1 |
| Bài tạp chí | 1 (12,5%) | Neural Processing Letters |
| Bài từ năm 2023 trở đi | 2 | DECRA 2024; BRB 2025 |
| Đọc toàn văn và trích xuất survey hoàn tất | 0 | `full_text_reviewed=no` cho cả 8 |
| Q1 / Q2 / Q3 / Q4 đã xác minh | 0 / 0 / 0 / 0 | Chỉ đếm trong 1 bài tạp chí |
| Q chưa xác minh | 1 (100% bài tạp chí) | Không có nghĩa tạp chí nằm ngoài Q1–Q4 |
| Repo công khai đã kiểm tra truy cập và liên hệ với bài | 8 (100%) | Có code tác giả/nhóm tác giả |
| Code tác giả chạy thử thành công trong dự án | 0 | `code_smoke_tested=no` |
| Bài có `dataset_public=yes` trong tracker | 8 | Khai báo cũ; không chứng minh mọi dataset đều tải tự do |
| Tên/phạm vi benchmark đối chiếu paper hoặc repo | 8 | Không phải kiểm chứng giấy phép và tải thành công |
| Tải lại toàn bộ dữ liệu thực nghiệm bài gốc được xác nhận | 0 | `original_dataset_download_verified=no` |

Theo năm: 2016: 1; 2017: 2; 2018: 1; 2020: 1; 2021: 1; 2024: 1; 2025: 1. Word có 12 mục tài liệu tham khảo, trong đó 8 mục là bài phương pháp; 4 mục còn lại là nguồn dữ liệu/tài liệu scikit-learn và hướng dẫn phân hạng. Không cộng cả 12 thành số bài deep clustering đã khảo sát.

## Bằng chứng cho từng công trình

Các liên kết “bài” là proceedings hoặc nhà xuất bản. “Repo” là nguồn kiểm chứng công khai mã; chưa có bằng chứng thực thi code tác giả. Dataset phía dưới là phạm vi đọc được trong phần thực nghiệm/README, chưa phải hồ sơ tái hiện đầy đủ.

| ID / phương pháp | Năm, nơi công bố, loại | Nguồn bài và code | Dataset đối chiếu |
|---|---|---|---|
| P01 DEC | 2016, ICML, hội nghị | [Bài](https://proceedings.mlr.press/v48/xieb16.html), [PDF §4.1](https://proceedings.mlr.press/v48/xieb16.pdf), [repo tác giả](https://github.com/piiswrong/dec) | MNIST 70.000; STL-10 13.000 mẫu có nhãn, dùng HOG + đặc trưng màu và tập không nhãn khi pretrain; REUTERS-10K 10.000; REUTERS sau lọc 685.071 |
| P02 IDEC | 2017, IJCAI, hội nghị | [Bài](https://www.ijcai.org/proceedings/2017/243), [PDF §4.1](https://www.ijcai.org/proceedings/2017/0243.pdf), [repo tác giả](https://github.com/XifengGuo/IDEC) | MNIST 70.000, USPS 9.298, REUTERS-10K 10.000 |
| P03 DCN | 2017, ICML, hội nghị | [Bài](https://proceedings.mlr.press/v70/yang17b.html), [PDF §5.2](https://proceedings.mlr.press/v70/yang17b/yang17b.pdf), [repo tác giả cập nhật DCN-New](https://github.com/boyangumn/DCN-New) | RCV1-v2: 365.968 tài liệu đơn nhãn thuộc 20 chủ đề, tạo nhóm 4/8/12/16/20; 20Newsgroups 18.846; MNIST raw và MNIST tiền xử lý, mỗi bản 70.000 |
| P04 DEC-DA | 2018, ACML, hội nghị | [Bài](https://proceedings.mlr.press/v95/guo18b.html), [repo tác giả](https://github.com/XifengGuo/DEC-DA) | MNIST, MNIST-test, USPS, Fashion-MNIST theo README |
| P05 SCAN | 2020, ECCV, hội nghị | [Bài](https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/1057_ECCV_2020_paper.php), [repo tác giả](https://github.com/wvangansbeke/Unsupervised-Classification) | CIFAR10, CIFAR100-20, STL10, ImageNet; repo hướng dẫn tải riêng ImageNet |
| P06 CC | 2021, AAAI, hội nghị | [Bài](https://ojs.aaai.org/index.php/AAAI/article/view/17037), [repo tác giả đang dùng](https://github.com/Yunfan-Li/Contrastive-Clustering), [repo nhóm được bài dẫn](https://github.com/XLearning-SCU/2021-AAAI-CC) | CIFAR-10, CIFAR-100, STL-10, Tiny-ImageNet, ImageNet-10, ImageNet-dogs theo README |
| P07 DECRA | 2024, Neural Processing Letters 56:127, tạp chí | [Bài và §4.1/availability](https://link.springer.com/article/10.1007/s11063-024-11586-0), [repo được bài dẫn](https://github.com/lml-mengli/DECRA) | MNIST 70.000; Fashion-MNIST 70.000; REUTERS-10K 10.000; MNIST-test 10.000; USPS 9.298; COIL20 1.440 |
| P08 BRB | 2025, ICLR, hội nghị | [Bài](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f91685b940d5032f0f0c247edbd72edd-Abstract-Conference.html), [repo tác giả](https://github.com/Probabilistic-and-Interactive-ML/breaking-the-reclustering-barrier) | Repo hỗ trợ MNIST, FashionMNIST, KMNIST, USPS, GTSRB, OPTDIGITS, CIFAR10, CIFAR100-20; đây là danh sách hỗ trợ repo, chưa xác nhận từng benchmark đều có trong bảng thực nghiệm chính |

P06: URL nhóm XLearning-SCU do trang AAAI dẫn là fork từ repo Yunfan-Li đang lưu trong tracker, nên không đếm thành hai bài/code độc lập. Dù nền tảng AAAI dùng phần mềm xuất bản có mục “About the Journal”, công trình này thuộc technical track của hội nghị AAAI-21; vẫn đếm là hội nghị. Các thông tin này thể hiện trên [trang AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/17037) và [repo nhóm](https://github.com/XLearning-SCU/2021-AAAI-CC).

P07: phần mô tả MNIST-test của nhà xuất bản có nhầm chữ “REUTERS”; bảng này giữ tên benchmark MNIST-test. NMI trong bài DECRA dùng chuẩn hóa bằng `max(H_true,H_pred)`; demo dùng trung bình số học. Khi tái hiện cần đồng nhất công thức trước khi so trực tiếp số NMI. [Nguồn bài, §4.1–4.2](https://link.springer.com/article/10.1007/s11063-024-11586-0).

## Vì sao Q của bài tạp chí vẫn chưa điền

Đã xác minh Neural Processing Letters là nơi công bố của DECRA, năm 2024, trên [Springer](https://link.springer.com/article/10.1007/s11063-024-11586-0). Trang publisher không cung cấp Q theo ngành/năm. Truy cập [bản ghi SCImago](https://www.scimagojr.com/journalsearch.php?q=24806&tip=sid&clean=0) và [danh sách ngành Artificial Intelligence năm 2024](https://www.scimagojr.com/journalrank.php?category=1702&year=2024) nhận HTTP 403 trong đợt kiểm tra này, nên chưa đọc được bằng chứng phân hạng trực tiếp.

Tracker để trống `quartile`, `ranking_system`, `ranking_year`, `ranking_category`, `ranking_source`, với `quartile_verified=no`; lưu lý do trong `quartile_verification_note`. Khi có chứng cứ cần điền đồng thời hệ thống (ví dụ SJR hoặc JCR), năm, ngành, URL/export nguồn và trạng thái xác minh. Không lấy Q theo hệ thống/ngành khác rồi coi là một số Q chung. Hội nghị không nằm trong mẫu số Q của tạp chí.

## Dữ liệu chung và kết quả đã có

Tệp chung [digits_1797.npz](../data/digits_1797.npz) có 1.797 mẫu, 64 đặc trưng (ảnh 8×8), 10 lớp; `X = pixel / 16` và `y` chỉ dùng đánh giá. SHA-256 của NPZ đối chiếu đúng metadata: `3460276fd9ea7f0dc75aa5e0720ad8c0f91055d41b6a9b0d82552d808c09fa30`. Đây là bản Digits do scikit-learn phân phối, lấy từ tập test UCI; tập UCI đầy đủ có 5.620 mẫu. [Tài liệu load_digits](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html), [nguồn UCI và CC BY 4.0](https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits).

Năm cấu hình dùng toàn bộ cùng tệp NPZ, seed 0–4, 120 epoch pretrain và 60 epoch clustering. Đã chạy lại 25 lượt tại [archive/results_verified_20261012](../archive/results_verified_20261012/summary.csv). [verification.json](../archive/results_verified_20261012/verification.json) xác nhận metric tính lại từ dự đoán, 50 cặp seed và mean/sample std; metric của 25 lượt trùng bộ kết quả kèm sẵn. Thời gian chạy Windows khác môi trường đã tạo Word nên bảng thời gian Word là số tham chiếu của môi trường cũ.

| Cấu hình | ACC (%) | NMI (%) | ARI (%) |
|---|---:|---:|---:|
| AE + KMeans | 69,26 ± 6,43 | 65,44 ± 3,75 | 54,98 ± 5,18 |
| DEC | 74,32 ± 8,34 | 73,65 ± 4,88 | 62,70 ± 8,04 |
| IDEC | 74,50 ± 8,07 | 73,53 ± 4,66 | 62,49 ± 8,02 |
| DCN | 65,65 ± 4,92 | 62,39 ± 5,04 | 51,19 ± 5,45 |
| IDEC + BRB | 74,22 ± 6,37 | 71,50 ± 3,25 | 61,82 ± 5,47 |

Các bảng này là kết quả implementation NumPy độc lập và giản lược. AE + KMeans là baseline; IDEC + BRB là một cấu hình gắn cơ chế BRB lên IDEC. Không có năm repo tác giả đã chạy thành công và không có năm kết quả paper đã tái hiện chỉ từ bảng này. Chênh lệch ACC của IDEC, DEC và IDEC + BRB nhỏ hơn biến động giữa seed, chưa đủ để kết luận ưu thế.

## Đối chiếu mục tiêu trong Word

| Yêu cầu/phạm vi Word | Bằng chứng hiện có | Trạng thái |
|---|---|---|
| 30 công trình không trùng, đọc toàn văn | 8 ứng viên, 0 hồ sơ đọc toàn văn hoàn tất | Chưa đạt |
| Ít nhất 20 bài nghiên cứu phương pháp | Có 8 bài phương pháp khởi đầu | Chưa đạt |
| Ít nhất 10 bài từ 2023 trở đi | 2 bài | Chưa đạt |
| Phân tích sâu 8–10 bài | Word diễn giải cơ chế các cấu hình; chưa có 8–10 phiếu trích xuất full-text | Chưa đạt |
| Thống kê tạp chí/hội nghị/năm | Đủ số lượng và nguồn cho 8 ứng viên | Đạt trong danh sách hiện tại |
| Thống kê Q1/Q2/Q3/Q4 theo hệ thống/năm/ngành | Có mẫu số 1 journal; Q chưa xác minh 1 | Đã ghi trung thực phần thiếu; chưa hoàn tất phân hạng |
| Code public và code đã chạy riêng biệt | 8 repo public đã đối chiếu; 0 original smoke test | Đã tách số liệu, thực thi original code chưa đạt |
| Dataset, số mẫu, preprocessing, kiến trúc, metric, số lần chạy cho từng bài | Đã bổ sung danh sách dataset/nguồn; các mục còn lại chưa trích xuất đầy đủ cho cả 8 | Đạt một phần |
| Minh họa 5 cấu hình × 1 dataset × 5 seed | 25 lượt Digits đã chạy lại, kiểm chứng artifact | Đạt |
| Báo cáo 6 cấu hình × 3 dataset × 5 seed = 90 lượt | Hiện 5 cấu hình × 1 dataset × 5 seed | Chưa đạt; mở rộng dataset là giai đoạn sau theo yêu cầu hiện tại |
| Tái hiện IDEC trên MNIST và USPS | Chưa chạy code/cấu hình bài gốc trên hai dataset | Chưa đạt |
| Cách trình bày kết quả | Word có mean/std, ổn định, thời gian, hình, hướng dẫn; kết quả mới có đầy đủ CSV/log/dự đoán | Đạt cho demo; cần cập nhật thời gian khi báo cáo môi trường mới |

Để chuyển thành survey hoàn tất, mỗi bài cần phiếu đọc có đóng góp, quan hệ với phương pháp trước, giới hạn, dữ liệu thực dùng, preprocessing, kiến trúc, loss, metric, số lần chạy và số liệu đối chiếu. Chỉ đổi `full_text_reviewed=yes` khi đã hoàn thành phiếu này. Giữ quy trình cùng một tệp và seed cho mọi cấu hình khi mở rộng sang dataset thứ hai/thứ ba; tách rõ kết quả benchmark chung khỏi tái hiện đúng cấu hình paper.

## Cách kiểm tra và cập nhật thống kê

```powershell
.venv\Scripts\python.exe scripts/summarize_survey.py --output archive/results_verified_20261012/survey_counts.json
```

Script không cần pandas, giữ các key cũ để báo cáo tương thích và bổ sung count/percentage cho bài liệt kê, metadata, code đã đối chiếu, phạm vi dataset, bài gần đây và full-text. Q chỉ được đưa vào count khi có đủ evidence và `quartile_verified=yes`; nếu chỉ nhập `Q2` mà thiếu evidence, vẫn tính là chưa xác minh. Đã kiểm tra hành vi này, trường hợp hội nghị có Q không bị đếm và trường hợp không có bài tạp chí không chia cho 0.
