# Lựa chọn theo timeline và giới hạn kết luận — 13/10/2026

Đề tài: **Đánh giá hiệu năng và độ ổn định của các phương pháp phân cụm sâu**.
Bài target được xác nhận là IDEC, IJCAI2017, từ PDF người dùng chia sẻ.

| Mốc | Cơ chế cần đánh giá | Nguồn công bố | Vai trò |
|---|---|---|---|
| DEC2016 | Học encoder/tâm bằng KL và target tự làm sắc | [ICML](https://proceedings.mlr.press/v48/xieb16.html) | Baseline |
| IDEC2017 | Giữ decoder và thêm reconstruction | [IJCAI](https://www.ijcai.org/proceedings/2017/243) | Target, đối chiếu cùng seed |
| DECRA2024 | Adaptive/residual biểu diễn | [Neural Processing Letters](https://link.springer.com/article/10.1007/s11063-024-11586-0) | Mốc AE đời sau |
| DCSS2026 | Soft silhouette + entropy, RBF gán cụm | [Machine Learning](https://link.springer.com/article/10.1007/s10994-026-07026-w) | Ứng viên2026 phù hợp họ AE |

Mũi tên thể hiện thời gian và thay đổi cơ chế; không khẳng định tất cả là quan hệ kế thừa trực tiếp.
Mỗi bài có code tác giả công khai trong [tracker](../data/paper_tracker.csv). Lần chạy này dùng
bản chuyển thể NumPy trên backbone chung, chưa chạy nguyên môi trường các repo tác giả.

## Vì sao chưa chốt BRB hoặc một phương pháp là mạnh nhất

BRB là plug-in cho phương pháp dựa trên tâm. Theo yêu cầu cập nhật, giữ BRB ở bảng
paper-reported, không buộc phải chạy nó như phương pháp thứ tư. [ICLR2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f91685b940d5032f0f0c247edbd72edd-Abstract-Conference.html)
và Table13 được dẫn riêng trong [literature_context.json](literature_context.json).

| Ứng viên gần đây | Mục tiêu / khả năng so sánh | Trạng thái hiện tại |
|---|---|---|
| BRB2025 | Reset + recluster, gắn DEC/IDEC/DCN | Lấy số liệu paper theo protocol; không mặc định SOTA |
| LFSS2025 | Learning sample stability | [ICML](https://proceedings.mlr.press/v267/li25am.html), [code](https://github.com/LZX-001/LFSS); chưa chạy repo |
| DCBoost2025 | Plug-in lân cận hỗ trợ self-supervision | [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2025/hash/14c11b0ddbae4593c566ea158df642be-Abstract-Conference.html), [code](https://github.com/l-h-y168/DCBoost); chưa chạy repo |
| CDC2025 | Clustering và calibration | [ICLR](https://proceedings.iclr.cc/paper_files/paper/2025/hash/ffbe1a03c35d611e0fc8362b316a9237-Abstract-Conference.html); calibration ECE khác ACC |
| SANE2026 | DACHI/DSS, phân bổ mẫu | [ICLR](https://proceedings.iclr.cc/paper_files/paper/2026/hash/63ef323523f3be8b58ed9277cc747485-Abstract-Conference.html), [code](https://github.com/notoaudrey/Samples-Are-Not-Equal); bản IDEC-inspired là tùy chọn, chưa chạy ở lượt chính |
| DCSS2026 | Cùng họ AE, bài so trực tiếp DEC/IDEC/DECRA | Được chọn chạy cơ chế trên Digits vì phù hợp câu hỏi, chưa được xác nhận tốt nhất2026 |

Không gộp các số ACC trên datasets/backbones/pretraining khác nhau thành một bảng xếp hạng.
Không dùng điểm paper so trực tiếp điểm Digits1797. Một bộ data giúp sàng lọc pipeline và
độ nhạy; kết luận tổng quan cần nhiều dataset, seed, ngân sách và cấu hình nguyên gốc.

## Kết quả đo trên cùng tệp Digits

20 lượt chính: DEC/IDEC/DECRA/DCSS × seeds0–4; pretrain120epoch, clustering60epoch,
batch128, Adam0,001; K10. `y` chỉ đánh giá. [summary](../results/timeline_20261013/summary.csv),
[config](../results/timeline_20261013/config.json), [kiểm chứng](../results/timeline_20261013/verification.json).

| Bản chuyển thể | ACC mean±sample std (%) | Pairwise ARI mean |
|---|---:|---:|
| DEC | 74,32±8,34 | 0,650 |
| IDEC | 74,50±8,07 | 0,662 |
| DECRA theo code | 70,40±7,36 | 0,585 |
| DCSS theo code, sigma1 | 51,89±12,51 | 0,202 |
| DCSS bổ sung, sigma RMS(X) | 73,65±8,00 | 0,654 |

Dòng cuối là ablation sau khi xem kết quả chính, không thay thiết lập ban đầu. Chỉ đổi
sigma theo khoảng cách X tới tâm K-means; không dùng y để khởi tạo hoặc grid-search theo
ACC. Nó cho thấy tác động của scale latent khi thay tanh/BatchNorm bằng latent tuyến tính.
[Code ablation](../scripts/run_dcss_calibration.py), [diagnostics](../checks/dcss_width_diagnostics.json).

IDEC có mean ACC/pairwise ARI cao nhất ở lượt chính, nhưng chỉ hơn DEC0,18điểm%.
DECRA có stdACC thấp hơn nhưng mean/pairwiseARI cũng thấp hơn; không thể gọi ổn định nhất
chỉ từ một cột std. Không có bằng chứng rằng năm mới tự động tốt hơn trong bản chuyển thể này.

## Mức hoàn thành survey

Tracker có 32 công trình không trùng: 27 hội nghị, 5 tạp chí; 16 bài từ 2023 trở đi.
Gồm 31 bài phương pháp và 1 bài tổng quan. 31 liên kết mã phương pháp và 1 thư viện/tập tài nguyên
tổng quan công khai đã đối chiếu; 0 môi trường repo tác giả chạy hoàn chỉnh.
2 phiếu đọc toàn văn hoàn tất là DEC/IDEC. DECRA/DCSS đã đối chiếu sâu cơ chế và code,
nhưng chưa đánh dấu đọc toàn văn hoàn tất khi còn thiếu trích xuất bảng gốc đầy đủ.

Theo SJR **best quartile của tạp chí, năm tham chiếu 2024**: Q1 = 3 (TPAMI, Pattern Recognition Letters,
ACM Computing Surveys); Q2 = 1 (Neural Processing Letters); Q3 = 0; Q4 = 0; chưa xác minh = 1
(Machine Learning). Nguồn là nội dung SCImago được lập chỉ mục; truy cập trực tiếp bị 403.
Năm tham chiếu khác năm xuất bản của một số bài. Riêng Pattern Recognition Letters có Q2 ngành AI
năm 2020 và 2024, khác với best quartile Q1 năm 2024. Không trộn hai quy ước vào tổng.
Xem [chứng cứ nguồn/năm/scope](references/journal_rankings.json).
Các trường dataset-public/benchmark-name/download được đếm riêng, tránh nhầm biết tên
dataset với đã tải hoặc xác minh quyền truy cập toàn bộ nguồn.

32 metadata không đồng nghĩa 32 bài đã đọc xong. Mẫu ưu tiên public code nên tỷ lệ 100% code/tài nguyên
không đại diện toàn lĩnh vực. Xem [báo cáo](Bao_cao_timeline_20261013.html) để đọc từng
trường nguồn, số liệu được trích xuất và các mục chưa đủ chứng cứ.

Hai công trình bổ sung là [DKM, PRLetters 2020](https://doi.org/10.1016/j.patrec.2020.07.028),
giúp đối chiếu tối ưu đồng thời và biến động do khởi tạo, và
[bài tổng quan ACM Computing Surveys](https://doi.org/10.1145/3689036), online 2024, issue 2025,
giúp phân loại quan hệ giữa học biểu diễn và phân cụm. DKM ở phần tài liệu, không có lượt huấn luyện
mới trong bảng bốn phương pháp. [Liên kết tải và bản PDF đã lưu](paper_download_links.md).
