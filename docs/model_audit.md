# Kiểm tra mô hình và quy trình thực nghiệm

Ngày kiểm tra: **12/10/2026**. Phạm vi: `src/models.py`, `src/evaluation.py`,
`checks/check_gradients.py` và luồng chạy trong `run_demo.py`.

**Cập nhật 13/10/2026:** phần 1–6 bảo lưu audit của demo trước đó có DCN/BRB.
Thực nghiệm bốn giai đoạn mới dùng DEC (2016), IDEC (2017),
DECRA_code_adapted (2024) và DCSS_code_adapted (2026); xem phần 7–8.
Bảng kết quả ngày 12/10 ở phần 5 không phải kết quả của bộ bốn mới.

Code hiện tại là **bản minh họa NumPy được viết độc lập** cho AE + K-means,
DEC, IDEC, DCN và IDEC + BRB. Các đạo hàm đã qua kiểm tra số; quy trình chạy
dùng chung dữ liệu và điểm xuất phát giữa các phương pháp trong cùng seed.
Chưa thể gọi đây là tái hiện đầy đủ thực nghiệm của các paper: repo tác giả
chưa được chạy, kiến trúc, dữ liệu, pretraining và lịch cập nhật có khác biệt.

## 1. Cơ chế được triển khai

| Cấu hình | Hoạt động trong code | Giới hạn cần ghi khi báo cáo |
| --- | --- | --- |
| AE + K-means | Học autoencoder bằng reconstruction MSE; chạy K-means trên latent embedding; giữ nguyên autoencoder sau pretrain. | Baseline hai giai đoạn, dùng cùng checkpoint và khởi tạo K-means với các cấu hình khác. |
| DEC | Student-t với alpha = 1; tính target P từ Q trên toàn bộ X; tối ưu KL(P‖Q), encoder và tâm cụm; decoder không được cập nhật khi fine-tune. | Giữ cơ chế DEC, dùng mạng nhỏ và Adam; dừng sau số epoch cố định. |
| IDEC | Cùng Student-t, P và KL với DEC; thêm reconstruction MSE; cập nhật encoder, decoder và tâm cụm. | Giá trị gamma = 0,1 có nghĩa theo cách chia trung bình loss của demo; cần đối chiếu scaling khi chuyển repo. |
| DCN | Gán cụm cứng; tối ưu MSE + trọng số × khoảng cách bình phương tới tâm cụm; cập nhật tâm bằng trung bình toàn bộ embedding sau mỗi epoch. | Đây là biến thể xen kẽ theo epoch; không triển khai bước cập nhật tâm online của DCN gốc. |
| IDEC + BRB demo | Giữ 80% tham số encoder, thêm 20% từ khởi tạo ngẫu nhiên mới; chạy lại K-means; xóa trạng thái Adam của tâm cụm; tính lại P. | Reset cả latent layer cuối; đây là một khác biệt quan trọng với cấu hình BRB paper. |

DEC gốc định nghĩa Student-t, target P, KL và gradient ở mục 3.1; pretraining
stacked denoising autoencoder và tiêu chí dừng dựa vào thay đổi gán cụm có
trong paper. Demo pretrain autoencoder sạch từ đầu và chạy đủ ngân sách epoch.
Nguồn: [DEC, ICML 2016](https://proceedings.mlr.press/v48/xieb16.pdf).

IDEC kết hợp reconstruction với clustering loss và cập nhật P từ toàn bộ
embedding thay vì từ riêng minibatch. Paper dùng mạng d–500–500–2000–10,
pretraining denoising, lịch P theo iteration và điều kiện dừng; demo dùng
d–64–32–10, lịch P theo epoch và đầu ra sigmoid. Những thay đổi này ngăn việc
so sánh trực tiếp số liệu demo với bảng paper.
Nguồn: [IDEC, IJCAI 2017](https://www.ijcai.org/proceedings/2017/0243.pdf).

DCN gốc xen kẽ cập nhật mạng, assignment và tâm cụm với tốc độ cập nhật tâm
phụ thuộc số mẫu đã gán. Demo giữ assignment trong một epoch rồi cập nhật
tâm từ toàn bộ embedding. Hai lịch tối ưu không tương đương.
Nguồn: [DCN, ICML 2017, mục 4.2 và Algorithm 1](https://proceedings.mlr.press/v70/yang17b/yang17b.pdf).

BRB paper kết hợp soft reset, reclustering và reset momentum của tâm cụm.
Phần Implementation details nêu tránh reset embedding layer cuối để giảm
nhiễu quá lớn. Demo reset W0, W1 **và W2**, dùng khởi tạo Gaussian của
autoencoder; do đó chỉ minh họa cơ chế BRB, chưa tái hiện cấu hình tác giả.
Nguồn: [BRB, ICLR 2025, trang 5 và Appendix A](https://proceedings.iclr.cc/paper_files/paper/2025/file/f91685b940d5032f0f0c247edbd72edd-Paper-Conference.pdf).

## 2. Đạo hàm và định nghĩa loss

Với N mẫu, D đặc trưng và z là embedding, loss trong **code của dự án** là:

- Reconstruction: `mean((reconstruction - X)^2)`, chia cho N × D.
- DEC: `mean_i sum_j P_ij log(P_ij / Q_ij)`, chia cho N.
- IDEC: reconstruction + gamma × KL; mặc định gamma = 0,1.
- DCN: reconstruction + 0,01 × `mean_i ||z_i - center[label_i]||^2`.

Trong cập nhật KL, P được giữ cố định. Hệ số gradient theo từng cặp mẫu–tâm
là `2 * (P - Q) / (1 + squared_distance) / batch_size`; dấu gradient encoder
và tâm cụm đối nhau theo vector chênh lệch. Khi fine-tune IDEC, gradient tại
latent là tổng từ decoder và gamma × gradient clustering. Các phép tính này
đã được kiểm tra bằng sai phân hữu hạn, không chỉ đọc công thức.

Các cột `clustering` và `total` giữa DEC/IDEC/DCN dùng định nghĩa khác nhau,
nên không dùng độ lớn loss để xếp hạng mô hình. Với DEC, reconstruction trong
trace chỉ là giá trị chẩn đoán của decoder được giữ lại; nó không tham gia
tối ưu. KL trong trace dùng P gần nhất đã được cập nhật, nên khi P được đổi,
loss có thể tăng dù vòng huấn luyện hoạt động đúng.

## 3. Nhãn, dữ liệu và tính công bằng của so sánh

`pretrain`, `train_dec` và `train_dcn` không nhận ground-truth y. Huấn luyện,
target P và reclustering chỉ dùng X. Runner chỉ sử dụng y khi tính metric,
lưu nhãn để xem kết quả và tô màu/ghép nhãn biểu đồ. K = 10 được khai báo
trong protocol, không suy ra từ y trong hàm huấn luyện. Biết K từ benchmark
cần được ghi rõ, vì ứng dụng dữ liệu chưa biết số nhóm có bài toán khác.

Trong mỗi seed, runner pretrain một mạng duy nhất, chạy K-means khởi tạo một
lần, rồi dùng `pretrained.clone()` và `init_centers.copy()` cho từng phương
pháp. AE + K-means sử dụng luôn nhãn khởi tạo đó. Tất cả cùng X và cùng thứ
tự mẫu; checkpoint khởi tạo và SHA-256 của X được lưu để kiểm chứng. Thay
seed sẽ huấn luyện lại từ đầu. Thời gian standalone gồm pretraining, K-means
khởi tạo và fitting; không gồm vẽ hình, ghi file hay đánh giá.

Các cấu hình dùng cùng số epoch fine-tune, batch size và learning rate;
điều đó kiểm soát một phần ngân sách, nhưng chưa có nghĩa chi phí tính toán
tương đương hoặc siêu tham số của từng mô hình đã được tối ưu công bằng.
BRB có thêm reclustering và tiêu thụ các số ngẫu nhiên cho reset, nên thứ tự
minibatch sau reset có thể khác IDEC thường. Đây là một điều kiện cần lưu ý
nếu muốn làm ablation kiểm soát hoàn toàn thứ tự minibatch.

Demo huấn luyện và đánh giá trên toàn bộ cùng một tập X theo protocol
**transductive clustering**. Không có test set chưa thấy để đo khả năng tổng
quát hóa. Cũng chưa có validation protocol hoặc tìm kiếm siêu tham số độc
lập. Không được dùng y để chọn epoch/seed tốt nhất rồi chỉ báo lần đó: kết
quả chính hiện báo trung bình và sample std của năm seed; hình đại diện dùng
seed đầu tiên đã khai báo trước.

## 4. Đánh giá và hai lỗi đã sửa

ACC dùng Hungarian matching một–một giữa cluster ID và class label; NMI và
ARI dùng partition gốc, không phụ thuộc hoán vị tên cụm. Hungarian ở đây là
thao tác **đánh giá sau huấn luyện**, không phải sử dụng y để huấn luyện.
Với số cụm khác số lớp, các cụm không ghép được phải đóng góp 0 vào ACC.

Hai sửa đổi đã hoàn thành:

1. **`src/evaluation.py`: tránh xung đột sentinel -1.** Trước đây cụm chưa
   được ghép nhận -1; nếu dữ liệu mới có nhãn thật -1, các mẫu đó có thể bị
   tính đúng sai. Hiện sentinel được chọn ngoài tập nhãn thật, đồng thời
   đầu vào phải là các vector nhãn nguyên, không rỗng và cùng chiều dài.
   Với ví dụ một lớp thật -1 và hai cụm bằng nhau, ACC đúng là 0,5; code cũ
   trả 1,0. Digits có nhãn 0–9 nên sửa này không đổi các metric Digits.
2. **`src/models.py`: log DCN sau cập nhật tâm.** Sau khi tính tâm mới, code
   tính lại nearest-center assignment trước khi ghi distortion. Nhờ vậy
   trace cuối epoch khớp objective của partition hiện tại và prediction trả
   về. Sửa đổi chỉ ảnh hưởng số loss ghi log; assignment cho bước huấn luyện
   epoch kế tiếp vốn đã được tính lại nên không đổi quỹ đạo tham số.

## 5. Bằng chứng kiểm tra chạy trên máy hiện tại

Lệnh chạy từ thư mục dự án:

```powershell
py -3.14 checks/check_gradients.py --output checks/verification_local_models.json
```

Kết quả: **PASS 216 phép kiểm tra đạo hàm**, sai số tương đối lớn nhất
**9,6427742763 × 10⁻⁹**. Môi trường ghi trong JSON: Python 3.14.2,
NumPy 2.5.1. Ngưỡng kiểm tra là 2 × 10⁻⁴; epsilon sai phân hữu hạn là 10⁻⁵.

| Nhóm đạo hàm | Số kiểm tra |
| --- | ---: |
| DEC, latent embedding | 15 |
| DEC, tâm cụm | 9 |
| IDEC, trọng số/bias encoder và decoder | 96 |
| DCN, trọng số/bias encoder và decoder với assignment cố định | 96 |
| **Tổng** | **216** |

Kiểm tra hành vi còn xác nhận: metric sau hoán vị nhãn; nhãn âm và cụm dư;
số cụm ít hơn số lớp; đầu vào metric không hợp lệ; nội suy BRB chỉ thay
encoder; reset Adam của tâm giữ nguyên moment mạng; decoder DEC không đổi;
BRB reset đúng epoch 3/5 khi interval = 2 và reset moment tâm hai lần;
distortion DCN cuối epoch khớp nearest-center partition trả về.

Artifact: [verification_local_models.json](../checks/verification_local_models.json).
Các kiểm tra này xác nhận công thức và các hành vi được triển khai, chưa
chứng minh tương đương toàn bộ thuật toán/repo tác giả và chưa chứng minh
thứ hạng mô hình trên nhiều dữ liệu.

Lần chạy chính trên máy hiện tại dùng năm seed 0–4 và năm cấu hình, cùng
1.797 mẫu Digits. Kết quả trong
[summary.csv](../archive/results_verified_20261012/summary.csv):

| Cấu hình | ACC trung bình ± sample std (%) | NMI trung bình (%) | ARI trung bình (%) |
| --- | ---: | ---: | ---: |
| AE + K-means | 69,26 ± 6,43 | 65,44 | 54,98 |
| DEC | 74,32 ± 8,34 | 73,65 | 62,70 |
| IDEC | 74,50 ± 8,07 | 73,53 | 62,49 |
| DCN demo | 65,65 ± 4,92 | 62,39 | 51,19 |
| IDEC + BRB demo | 74,22 ± 6,37 | 71,50 | 61,82 |

Trong cấu hình này, IDEC có ACC trung bình cao nhất nhưng chênh lệch với
DEC/IDEC + BRB nhỏ so với biến động giữa seed. Chưa có kiểm định thống kê
hoặc nhiều bộ dữ liệu để kết luận IDEC tốt hơn, hoặc BRB không có tác dụng.
ARI giữa các seed đo độ giống partition; 10 cặp từ 5 lần chạy dùng chung
các lần chạy và không phải 10 quan sát độc lập.

## 6. Điều kiện để gọi là tái hiện paper

Giữ demo để giải thích cơ chế và thử pipeline trên một file data. Khi chuyển
sang tái hiện kết quả công bố, cần chạy repo tác giả ở commit được ghi lại,
lưu environment/command/config; dùng đúng nguồn dữ liệu, preprocessing,
split, kiến trúc, pretraining, augmentation, loss scaling và lịch dừng. Báo
bảng paper cạnh kết quả tái chạy, số seed và sai khác protocol, thay vì so
điểm Digits với MNIST/USPS trong paper.

Với BRB cần kiểm soát các lớp được reset, nhất là embedding layer cuối;
với DCN cần triển khai hoặc sử dụng đúng cập nhật tâm online. Nếu mục tiêu
là so sánh thống nhất trên 2–3 bộ data, có thể tiếp tục dùng code chung này
nhưng phải ghi tên cấu hình là bản minh họa/biến thể và cố định protocol
trước khi xem metric. Mỗi file mới cần X hai chiều hữu hạn trong [0,1], y
nguyên chỉ phục vụ đánh giá, cùng thứ tự mẫu cho mọi mô hình, và K được
khai báo rõ.

## 7. DECRA: kiểm tra bổ sung ngày 13/10/2026

DECRA (Neural Processing Letters, 2024; DOI 10.1007/s11063-024-11586-0)
có code công khai MIT. Có bất nhất: paper Eq4–5 dùng `z_hat=z+H(z)`;
repo dùng `z_hat=Linear(z)` và hai đường decode. Paper nêu TensorFlow1.15,
repo dùng PyTorch. Nguồn: [paper](https://doi.org/10.1007/s11063-024-11586-0),
[code tác giả](https://github.com/lml-mengli/DECRA/blob/main/decra.py).

`src/decra.py` mang tên **DECRA_code_adapted**: chuyển cơ chế repo sang
backbone chung, thêm `W_residual` và `b_residual` cho affine latent→latent.
Encoder gốc vẫn tạo z để clustering; hai đường dùng cùng decoder. Tổng loss
mặc định là `2*MSE(decode(z),X)+0.6*MSE(decode(z_hat),decode(z))+0.1*KLmean`.
KLmean chia tổng KL cho N×K; IDEC của demo chia N, nên gamma=0,1 không có
cùng hiệu lực. Đường decode(z) trong consistency **không detach**: gradient
đi qua cả hai đường và cộng vào decoder chung. Các hệ số trên giữ theo
fine-tuning source, không chọn sau khi xem metric Digits.

Để kiểm soát so sánh, phiên bản này dùng lại pretrained checkpoint, tâm
K-means và lịch chạy chung; không thực hiện pretraining residual riêng.
Adaptive layer được khởi tạo uniform±1/sqrt(latent_dim) bằng RNG riêng.
Mạng d–64–32–10, sigmoid output, shuffle minibatch và fixed epochs của demo
khác pipeline tác giả. Repo cần checkpoint `ae_mnist.pkl` khi vào train;
không được suy diễn từ code public thành đã tái hiện thành công.

Lệnh kiểm tra:

```powershell
.venv\Scripts\python.exe checks/check_decra.py --output checks/verification_decra.json
```

**PASS 117 gradient checks** (backbone 96, adaptive 12, centers 9), sai số
tương đối lớn nhất **3,161×10⁻⁷**. Kiểm tra đối chiếu scalar loss được viết
độc lập từ các phép toán, kiểm tra hai decoder branches không detach,
forward của decoder dùng chung, backbone không đổi khi thêm adaptive layer,
và huấn luyện lặp lại cùng seed cho kết quả giống nhau. Artifact:
[verification_decra.json](../checks/verification_decra.json).

Snapshot source được lưu tại `docs/references/author_sources/DECRA/` cùng LICENSE;
đây là tài liệu đối chiếu, chưa phải môi trường repo tác giả đã chạy.

## 8. DCSS: cơ chế năm 2026 và kiểm tra bổ sung

DCSS được đăng Machine Learning ngày 31/03/2026,
DOI 10.1007/s10994-026-07026-w; repo công khai MIT. Paper kết hợp
reconstruction, soft silhouette và entropy, dùng RBF→softmax để gán cụm.
Paper Eq13 có chia distance sum cho membership mass, nhưng Objectives.py
repo không chia. Paper §5.3 ghi T=20; source mặc định chia logits cho 0,25.
Nguồn: [paper](https://doi.org/10.1007/s10994-026-07026-w),
[repo](https://github.com/gvardakas/Soft-Silhouette).

`src/dcss.py` dùng tên **DCSS_code_adapted**, mặc định theo source:

- Gaussian RBF: `phi_ij=exp(-||z_i-center_j||^2/exp(2*log_sigma_j))`.
- `Q=softmax(phi/0.25)`. Tâm được lấy từ khởi tạo chung; thêm `log_sigmas`
  học được, ban đầu bằng 0, tương ứng sigma=1.
- Soft silhouette từ Euclidean pairwise distance của embedding trong batch,
  `a=D@Q`, `b=min(a của các cụm khác)`, `s=(b-a)/max(a,b)`;
  score là trung bình `sum(Q*s)` theo mẫu.
- Tổng loss: `MSE + 0.01*(1-soft_silhouette) + 0.01*mean_entropy_bits`.

Đây là việc chuyển objective/RBF theo source vào mạng chung, chưa chạy
nguyên môi trường tác giả. Mạng nhỏ của demo dùng ReLU, latent tuyến tính
và sigmoid output; không dùng BatchNorm, latent tanh hoặc CNN của source.
Các hệ số được cố định từ source trước khi xem kết quả. Tuy chọn cùng
backbone và pretrain giúp kiểm soát so sánh, kết quả không thể gọi là số
paper đã tái hiện hoặc phủ nhận hiệu quả phương pháp nguyên gốc.

`distance_normalization='paper'` là biến thể đối chiếu có chia cho
`sum(Q)-Q_i`, có đạo hàm được kiểm tra riêng. Main benchmark dùng `'source'`
để giữ nguyên cơ chế public code đã chọn, không tự pha hai công thức. Điểm
khác biệt này phải được giữ trong báo cáo tái hiện.

Đạo hàm thủ công đi qua **cả Q và khoảng cách pairwise**, qua RBF tới
embedding, tâm cụm và log_sigma; không detach embedding. Min/max được tính
theo từng miền trơn như autograd. Khi khoảng cách/denominator bằng 0,
phiên bản NumPy có epsilon protection và gradient distance bằng 0. Đây là
thay đổi ổn định số được nêu rõ. Batch cuối chỉ có 1 mẫu được gộp vào batch
trước để silhouette tính được và mọi mẫu vẫn xuất hiện đúng một lần.

Loss trace cuối epoch được tính lại trên các batch đánh giá cố định của
tham số đã cập nhật, rồi lấy trung bình theo số mẫu. Cột
`loss_scope='fixed_evaluation_minibatches'` phân biệt với loss trên toàn bộ
dataset của DEC/IDEC. Không dùng total loss này để xếp hạng giữa phương
pháp hoặc gọi nó là silhouette đầy đủ của toàn bộ Digits.

Lệnh kiểm tra:

```powershell
.venv\Scripts\python.exe checks/check_dcss.py --output checks/verification_dcss.json
```

**PASS 210 gradient checks**, sai số tương đối lớn nhất **5,303×10⁻⁶**:
source silhouette 49, paper silhouette 49, network 96, log_sigmas 4, centers 12.
Kiểm tra forward đối chiếu literal mask/view/reverse của Objectives.py với
2/3/4/5/10 cụm; kiểm tra toàn bộ đường gradient, zero distances, singleton
batch, deterministic training, prediction đúng Q và trace đúng loss được
tính lại. Artifact: [verification_dcss.json](../checks/verification_dcss.json).

Snapshot source và LICENSE được lưu tại `docs/references/author_sources/DCSS/`; các
`sha256.json` trong hai snapshot DECRA/DCSS xác định nội dung đã đọc.
