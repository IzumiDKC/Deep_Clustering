# Đánh giá hiệu năng và độ ổn định của các phương pháp phân cụm sâu

## Bản hiện tại — 13/10/2026

Mở [báo cáo HTML mới](docs/Bao_cao_timeline_20261013.html),
[bản Word mới](docs/Bao_cao_timeline_20261013.docx) hoặc
[notebook bốn phương pháp đã thực thi](notebooks/demo_4_timeline_verified.ipynb).

Đã chạy **DEC2016 → IDEC2017 → DECRA2024 → DCSS2026** trên cùng tệp Digits1797,
seeds0–4, tổng20 lượt trong `results_timeline_20261013`. BRB2025 giữ ở phần số liệu
tài liệu. Đây là các bản chuyển thể NumPy trên backbone chung; chưa chạy nguyên
môi trường repo tác giả và chưa xác lập phương pháp tốt nhất toàn lĩnh vực2025/2026.

| Bản chuyển thể | ACC mean ± sample std (%) | Pairwise ARI |
|---|---:|---:|
| DEC | 74,32 ± 8,34 | 0,650 |
| IDEC | 74,50 ± 8,07 | 0,662 |
| DECRA theo code | 70,40 ± 7,36 | 0,585 |
| DCSS theo code, sigma1 | 51,89 ± 12,51 | 0,202 |
| DCSS bổ sung, sigma RMS(X) | 73,65 ± 8,00 | 0,654 |

Dòng cuối là5 lượt ablation riêng **sau khi xem kết quả chính**, chỉ đổi độ rộng RBF
từ khoảng cách X tới tâm K-means; không dùng y, không tìm kiếm theo ACC và không
thay kết quả chính. Chi tiết tại [timeline](docs/literature_timeline.md) và
[model audit](docs/model_audit.md). IDEC chỉ hơn DEC0,18điểm% ACC; chưa đủ bằng chứng
để kết luận cải thiện rõ. DECRA có std nhỏ hơn nhưng mean/agreement cũng thấp hơn.

Tracker30 bài:27 hội nghị,3 tạp chí,15 từ2023.30repo public;2phiếu full-text DEC/IDEC
hoàn tất;0repo tác giả đã chạy; Q của3journal chưa xác minh.30metadata không đồng
nghĩa30bài đã đọc xong; mẫu ưu tiên code public không đại diện toàn lĩnh vực.

Mặc định runner hiện chọn4 phương pháp mới. Chạy lại bằng interpreter đã có:

```powershell
.\.venv\Scripts\python.exe checks\check_decra.py
.\.venv\Scripts\python.exe checks\check_dcss.py
.\.venv\Scripts\python.exe run_demo.py --methods DEC IDEC DECRA DCSS --data data\digits_1797.npz --seeds 0 1 2 3 4 --output results_lan_sau
.\.venv\Scripts\python.exe checks\verify_experiment.py --results results_lan_sau
.\.venv\Scripts\python.exe summarize_survey.py --output results_lan_sau\survey_counts.json
.\.venv\Scripts\python.exe build_review_report.py --results results_lan_sau --name Bao_cao_lan_sau
```

216 gradient nền,117 DECRA,210 DCSS đã kiểm tra. Verification xác nhận20 lượt chính,
40cặp seed, cùng X/hash code học, metric từ prediction và prediction từ checkpoint.
Code bổ sung: `src/decra.py`, `src/dcss.py`; nguồn và giới hạn: `src/method_registry.py`.
Để lặp lại ablation từ checkpoint cùng data:

```powershell
.\.venv\Scripts\python.exe checks\run_dcss_calibration.py --source results_lan_sau --output results_ablation_lan_sau
.\.venv\Scripts\python.exe checks\verify_experiment.py --results results_ablation_lan_sau
```

Kết quả lịch sử và Word nguồn được giữ. Phần dưới là tài liệu demo ngày12/10/2026;
các con số8bài/25lượt thuộc lần lịch sử. Nếu chạy5cấu hình cũ, truyền rõ
`--methods AE_KMeans DEC IDEC DCN IDEC_BRB`. SANE-inspired là tùy chọn, không thuộc
lượt chính và không phải implementation gốc SANE.

---

# Tài liệu lịch sử: minh họa năm cấu hình

## Bản đã kiểm tra trên máy Windows ngày 12/10/2026

Mở `docs/Bao_cao_kiem_tra_va_thuc_nghiem.html` để xem bảng khảo sát, cơ chế,
biểu đồ, loss theo epoch và kết quả chạy lại. Bản Word tương ứng ở
`docs/Bao_cao_kiem_tra_va_thuc_nghiem.docx`. Word ban đầu được giữ nguyên.
Kết quả chạy tại máy nằm trong `results_verified_20261012`, tách khỏi `results`
tham chiếu đi kèm. `verification.json` kiểm tra lại metric từ dự đoán và dự đoán
từ trọng số đã lưu; `checks/verification_local_models.json` kiểm tra 216 gradient.

Notebook `notebooks/demo_5_algorithms_verified.ipynb` đã chạy tất cả các ô và
lưu output để xem ngay. Nó trình bày soft assignment Q, target P, biểu đồ loss,
kết quả và tracker. Notebook gốc mặc định xem lần chạy đã kiểm chứng; đổi
`RUN_NEW_EXPERIMENT = True` để chạy lại. Nếu cần môi trường notebook, cài
`requirements_notebook.txt`; không cần cài các thư viện này để chạy demo CLI.

Tracker hiện có **8 bài: 7 hội nghị, 1 tạp chí**, chưa hoàn thành mục tiêu 30 bài
đọc toàn văn trong Word. Q của bài tạp chí còn chưa xác minh; thống kê Q1–Q4 bằng
0 hiện tại không có nghĩa bài đó không thuộc các Q này. Repo công khai và repo
đã chạy thành công được thống kê riêng. Xem `docs/survey_audit.md` và
`docs/model_audit.md` để biết bằng chứng và giới hạn.

Máy này dùng launcher `py -3.14`; lệnh `python` trỏ tới shortcut Microsoft Store.
Môi trường `.venv` đã chuẩn bị và các phiên bản chạy thực tế được ghi trong
`results_verified_20261012/environment.json` và `requirements_verified.txt`.
Chạy lại bằng lệnh sau trong thư mục dự án, chọn thư mục output mới:

```powershell
.\.venv\Scripts\python.exe run_demo.py --data data/digits_1797.npz --seeds 0 1 2 3 4 --output results_chay_lai
.\.venv\Scripts\python.exe checks/verify_experiment.py --results results_chay_lai
.\.venv\Scripts\python.exe summarize_survey.py --output results_chay_lai/survey_counts.json
.\.venv\Scripts\python.exe build_review_report.py --results results_chay_lai
```

Nếu cài lại từ đầu trên Windows: `py -3 -m venv .venv`, rồi
`.\.venv\Scripts\python.exe -m pip install -r requirements_report.txt`.
`run_windows.bat` tự tìm launcher, tạo venv và kiểm tra gradient trước khi chạy.

**AE + K-means, DEC, IDEC, DCN và IDEC + BRB** trên bộ Digits 1.797 ảnh 8×8.
Dữ liệu có sẵn trong gói; chạy bằng CPU, không cần CUDA hoặc PyTorch.
Các hàm mạng, backpropagation, Adam và clustering loss được viết bằng NumPy
để dễ đọc và thay đổi.

Đây là bản minh họa độc lập, giữ cơ chế chính của các phương pháp nhưng dùng
mạng nhỏ, lịch cập nhật và dữ liệu khác bài gốc. Kết quả không được gọi là tái hiện
đầy đủ paper hoặc bằng chứng về SOTA. DCN dùng cập nhật tâm cụm theo toàn bộ dữ liệu;
BRB minh họa reset toàn encoder, reclustering và reset trạng thái Adam của tâm cụm.

## Chạy trên Windows

1. Cài Python 3.11 hoặc 3.12 và chọn **Add Python to PATH**.
2. Giải nén toàn bộ gói ZIP. Mở terminal trong thư mục `Deep_Clustering_Demo`.
3. Chạy:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run_demo.py --seeds 0 1 2 3 4 --output results_may_toi
```

Có thể bấm đúp `run_windows.bat` để cài thư viện vào Python hiện tại và chạy.
Lần cài thư viện đầu tiên cần mạng. Sau đó, dữ liệu và demo chạy không cần mạng.
Thời gian phụ thuộc CPU; số giây trong gói là đo trên môi trường đã chạy, không phải
cam kết cho máy khác.

## Chạy trên Linux hoặc macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_demo.py --seeds 0 1 2 3 4 --output results_may_toi
```

Lệnh chung nếu đã có môi trường phù hợp:

```bash
python run_demo.py
```

Kết quả mặc định nằm trong `results_local`. Chương trình giữ kết quả cũ và yêu cầu
đổi `--output` nếu thư mục đã có `summary.csv`.

## Thử nhanh hoặc chọn bốn phương pháp

```bash
python run_demo.py --seeds 0 --pretrain-epochs 30 --cluster-epochs 20 --output results_nhanh
python run_demo.py --methods AE_KMeans DEC IDEC DCN --seeds 0 1 2 3 4 --output results_4_phuong_phap
```

Với chỉ một seed, độ lệch chuẩn và pairwise ARI chưa tính được; CSV ghi NaN
hoặc ô trống. Các kết quả chạy nhanh khác cấu hình 25 lượt chạy đi kèm.

## Tệp kết quả

- `results/summary.csv`: kết quả tham chiếu đã chạy, mean và sample std, năm seed.
- `results/runs.csv`: ACC, NMI, ARI, thời gian và số cụm không rỗng từng lần chạy.
- `results/pairwise_ari.csv`: 10 cặp seed cho mỗi phương pháp, tổng cộng 50 dòng.
- `results/predictions/`: cluster label của từng mẫu trong 25 lần chạy.
- `results/traces/`: loss theo epoch. Các cột loss giữa phương pháp có định nghĩa
  khác nhau, không dùng giá trị total loss để xếp hạng phương pháp.
- `results/models/`: tham số của autoencoder và tâm cụm. `W0`–`W5` là trọng số,
  `b0`–`b5` là bias; file pretrained không có centers.
- `results/config.json`, `environment.json`: cấu hình và phiên bản thư viện.
- `performance.png`, `stability.png`, `embeddings.png`, `confusion_matrices.png`,
  `sample_images.png`: biểu đồ và ảnh từ kết quả thực tế.

Trong lần chạy mới có thêm `loss_curves.png` và `models/initialization_seed*.npz`.
Mọi dòng `runs.csv` có cùng `sha256_training_X`, chứng minh cùng dữ liệu học.
Thời gian standalone mới cộng pretrain, K-means khởi tạo chung và fitting riêng.
AE + K-means sử dụng kết quả khởi tạo chung; các phương pháp khác đều được cộng
chi phí khởi tạo này. Quy tắc thời gian mới khác quy tắc của kết quả tham chiếu cũ.

ACC, NMI và ARI trong CSV dùng thang 0–1. Biểu đồ hiệu năng và bảng Word đổi sang
phần trăm. Pairwise ARI giữ thang gốc. Sample std dùng ddof=1.
Mười cặp seed có dùng chung lần chạy; không được xem là mười quan sát độc lập
khi suy luận thống kê.

## Cấu hình mặc định

- Encoder: 64 → 64 → 32 → 10; decoder đối xứng.
- ReLU ở hidden layers, latent tuyến tính, đầu ra sigmoid.
- MSE trung bình trên tất cả pixel; pretrain 120 epoch.
- Clustering 60 epoch, batch size 128, Adam learning rate 0.001.
- K=10, K-means n_init=20; Student-t alpha=1.
- DEC tối ưu KL; IDEC tối ưu MSE + gamma×KL với gamma=0.1.
- DCN tối ưu MSE + 0.01×mean squared distance đến tâm cụm.
- IDEC + BRB giữ 80% tham số encoder khi reset; reset trước epoch 21 và 41.
- Cập nhật target P trên toàn bộ dữ liệu mỗi 5 epoch, không tính riêng từng batch.
- Các phương pháp cùng seed dùng chung mạng pretrain và tâm cụm ban đầu.
- Mỗi seed huấn luyện lại từ đầu; nhãn y chỉ đi vào đánh giá sau huấn luyện.

## Kiểm tra code và thống kê survey

```bash
python checks/check_gradients.py
python summarize_survey.py
```

Kiểm tra gradient sử dụng sai phân hữu hạn cho DEC, tâm cụm và mạng IDEC;
đồng thời kiểm tra metric sau hoán vị nhãn cụm và phép nội suy BRB.
`survey_counts.json` phản ánh danh sách khởi đầu tám bài, gồm một bài tạp chí
và bảy bài hội nghị. Các Q chưa xác minh được giữ là unknown; không gán Q4.
Các repo gốc trong tracker chưa được chạy thử bởi gói này.

## Đọc code theo thứ tự

1. `prepare_data.py`: nguồn dữ liệu và chuẩn hóa.
2. `src/models.py`: Autoencoder → pretrain → assignments → target_distribution
   → kl_loss_and_gradients → train_dec → train_dcn.
3. `src/evaluation.py`: Hungarian ACC, NMI, ARI.
4. `run_demo.py`: chạy nhiều seed, ghi log, tính pairwise ARI và vẽ hình.

Notebook `notebooks/demo_5_algorithms.ipynb` có các ô chạy và xem kết quả.
Trong Colab, giải nén ZIP vào `/content` rồi mở notebook; không cần GPU.

## Phát triển thành thực nghiệm báo cáo

Để mở rộng sang dữ liệu thứ hai hoặc thứ ba, mỗi bộ lưu riêng một `.npz` gồm
`X` dạng `(N,D)` đã chuẩn hóa về `[0,1]` và `y` dạng `(N,)` là nhãn số nguyên
chỉ dùng đánh giá. Đặt `--clusters` theo benchmark trước khi chạy và dùng cùng
tệp, preprocessing, seed và tham số cho mọi cấu hình trong một lần chạy:

```powershell
.\.venv\Scripts\python.exe run_demo.py --data data/bo_du_lieu_2.npz --dataset-name "Dataset 2" --clusters 10 --seeds 0 1 2 3 4 --output results_dataset_2
```

Biểu đồ dùng lớp thực tế của dữ liệu, không cố định 10 nhãn Digits. Chỉ tệp Digits
kèm sẵn được vẽ thành ảnh 8×8. Nếu dữ liệu không phải ảnh, cần xem lại kiến trúc
và loss trước khi diễn giải các phương pháp ảnh. Chưa chạy thêm bộ dữ liệu nào.

Giữ bộ này để giải thích cơ chế và kiểm tra luồng. Khi tái hiện IDEC,
chuyển sang MNIST/USPS, dùng preprocessing, pretraining và cấu hình của tác giả,
đối chiếu bảng paper gốc. Khi so sánh nhiều hướng nghiên cứu, ghi rõ kiến trúc,
dữ liệu pretrain, augmentation và ngân sách tính toán; có thể chia nhóm so sánh.
Tập Digits được dùng transductive trong demo, nên kết quả không đo khả năng
tổng quát hóa trên một test set chưa thấy.

Các phương pháp trong gói là lựa chọn để chạy thử. Danh sách thực nghiệm cuối
cùng của survey vẫn được chọn sau khi hoàn thành khảo sát 30 bài.

## Tài liệu gốc

- DEC ICML 2016: https://proceedings.mlr.press/v48/xieb16.html
- IDEC IJCAI 2017: https://www.ijcai.org/proceedings/2017/243
- DCN ICML 2017: https://proceedings.mlr.press/v70/yang17b.html
- BRB ICLR 2025: https://proceedings.iclr.cc/paper_files/paper/2025/hash/f91685b940d5032f0f0c247edbd72edd-Abstract-Conference.html
- Digits: https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html

Mã NumPy và tài liệu hướng dẫn trong gói là phần minh họa được viết độc lập.
Dữ liệu được phân phối theo CC BY 4.0 và có ghi nguồn trong `data/README_DATA.md`.
