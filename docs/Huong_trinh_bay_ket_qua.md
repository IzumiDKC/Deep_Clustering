# Hướng trình bày khảo sát và thực nghiệm

Dùng cùng [notebook đã có kết quả](../notebooks/demo_4_timeline_verified.ipynb).
Thời lượng gợi ý: 7–10 phút. Tập trung vào câu hỏi nghiên cứu, bằng chứng và cách diễn giải;
các bảng chi tiết theo seed để trả lời khi được hỏi.

## 1. Nêu câu hỏi và phạm vi — khoảng 1 phút

“Em khảo sát sự thay đổi của các phương pháp phân cụm sâu qua thời gian, đồng thời kiểm tra
phương pháp mới có cải thiện chất lượng và độ ổn định khi dùng cùng dữ liệu hay không.”

Danh mục hiện có **32 công trình: 31 bài phương pháp và 1 bài tổng quan; 27 hội nghị và 5 tạp chí**.
Có 16 công trình từ năm 2023. Theo **SJR best quartile năm tham chiếu 2024**, có 3 bài Q1,
1 bài Q2 và 1 bài tạp chí chưa xác minh đủ nguồn. Không gán Q tạp chí cho hội nghị.

Phân biệt mức công việc: 32 công trình đã lập danh mục, 18 tóm tắt số liệu có nguồn,
2 phiếu đọc toàn văn hoàn tất. Chưa chạy nguyên môi trường mã tác giả; thực nghiệm dùng bản chuyển thể
trên mạng chung. [Danh mục](../data/paper_tracker.csv), [nguồn Q](references/journal_rankings.json).

## 2. Giải thích tiến trình phương pháp — khoảng 2 phút

Mỗi mốc dùng một mạch: **hạn chế trước → thay đổi → kỳ vọng → bằng chứng → giới hạn**.

| Phương pháp | Thay đổi cần giải thích | Vì sao có thể giúp? | Bằng chứng và giới hạn |
|---|---|---|---|
| DEC 2016 | Học biểu diễn và tâm bằng mục tiêu gán cụm tự tạo | Đặc trưng được điều chỉnh cho phân cụm | Mốc nền; mục tiêu sai có thể được củng cố |
| IDEC 2017 | Thêm tái tạo dữ liệu khi học cụm | Hạn chế biến dạng biểu diễn | Trong bài IDEC, MNIST ACC 86,55 → 88,06%; bảng không có độ lệch chuẩn |
| DECRA 2024 | Thêm khả năng điều chỉnh biểu diễn | Tránh tái tạo quá chặt những thông tin không phục vụ cụm | Trong bảng DECRA, MNIST IDEC 88,1%, DECRA 96,4%; chưa chứng minh riêng nhánh thêm là nguyên nhân duy nhất |
| DCSS 2026 | Thêm mục tiêu cụm gọn và tách biệt | Tối ưu hình học cụm trực tiếp hơn | Chọn vì cùng họ autoencoder và có mã; bản chuyển thể nhạy độ rộng RBF |

Nguồn: [DEC](https://proceedings.mlr.press/v48/xieb16.html),
[IDEC Table 2](https://www.ijcai.org/proceedings/2017/0243.pdf),
[DECRA Table 2](https://link.springer.com/article/10.1007/s11063-024-11586-0/tables/2),
[DCSS](https://doi.org/10.1007/s10994-026-07026-w).

Các mốc thể hiện thời gian, không phải mọi bài đều kế thừa trực tiếp.
Lợi ích cơ chế là kỳ vọng; kết quả phải được đo để xác nhận.

## 3. Nêu cách so sánh — khoảng 1 phút

“Em dùng cùng bộ Digits gồm 1.797 ảnh 8×8, 64 đặc trưng và 10 lớp.
Mỗi seed học lại mạng từ đầu; bốn phương pháp nhận cùng trọng số tiền huấn luyện và tâm ban đầu.
Mỗi phương pháp có 5 seed, tổng 20 lượt chính. Mạng học tái tạo 120 epoch, học phân cụm 60 epoch,
nhóm cập nhật 128 mẫu, Adam với tốc độ học 0,001. Nhãn chỉ dùng đánh giá.”

Dữ liệu lấy qua [scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html),
nguồn gốc [UCI](https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits).
Toàn bộ X được dùng để học và phân cụm; chưa có tập chưa thấy để đo tổng quát hóa.

## 4. Đọc kết quả chung và ghép cặp — khoảng 2 phút

| Phương pháp | ACC trung bình ± độ lệch chuẩn (%) | ARI giữa seed |
|---|---:|---:|
| DEC | 74,32 ± 8,34 | 0,6504 ± 0,0631 |
| IDEC | 74,50 ± 8,07 | 0,6616 ± 0,0606 |
| DECRA | 70,40 ± 7,36 | 0,5855 ± 0,0578 |
| DCSS, σ = 1 | 51,89 ± 12,51 | 0,2018 ± 0,1313 |

[Nguồn đo tại máy này](../results/timeline_20261013/summary.csv).
Notebook có thêm NMI/ARI, thời gian ± độ lệch chuẩn và kết quả từng seed.

“IDEC có ACC trung bình cao nhất, hơn DEC khoảng 0,18 điểm phần trăm.
Nhưng khi ghép cùng seed, IDEC chỉ cao hơn ở 2 trong 5 seed; chênh lệch là 0,1781 ± 0,5708 điểm.
DEC còn nhỉnh NMI và ARI. Vì vậy em chưa kết luận IDEC tốt hơn một cách nhất quán.”

“DECRA có độ lệch chuẩn ACC nhỏ hơn, nhưng điểm trung bình và mức giống nhau giữa các phân hoạch
cũng thấp hơn. Chưa có cơ sở gọi đây là phương pháp ổn định hơn.”

ACC/NMI/ARI với nhãn càng cao càng tốt. Độ lệch chuẩn phản ánh biến động điểm;
ARI giữa seed phản ánh phân hoạch có giống nhau không. Hai khái niệm cần đọc cùng chất lượng.
Mười cặp seed dùng chung các lượt chạy nên không phải mười quan sát độc lập.

## 5. Giải thích DCSS và số liệu bổ sung — khoảng 1 phút

“Ở khởi tạo σ=1, xác suất gán cụm lớn nhất trung bình khoảng 0,1068, gần mức 0,1 của gán đều
trên 10 cụm. Em thử khởi tạo độ rộng bằng khoảng cách trong từng cụm K-means ban đầu, chỉ dùng X.
ACC đạt **73,64 ± 8,00%**, tăng khoảng **21,76 điểm phần trăm**.”

[Nguồn bổ sung](../results/dcss_width_ablation_20261013/summary.csv),
[chẩn đoán](../checks/dcss_width_diagnostics.json).
Đây là phân tích sau khi quan sát kết quả chính. Nó cho thấy độ nhạy khởi tạo trong bản chuyển thể,
chưa chứng minh DCSS gốc kém hoặc đây là lựa chọn tốt nhất. Không thay dòng chính bằng dòng bổ sung.

## 6. Đối chiếu bài báo và kết luận — khoảng 1–2 phút

Trong [BRB Table 13](https://proceedings.iclr.cc/paper_files/paper/2025/file/f91685b940d5032f0f0c247edbd72edd-Paper-Conference.pdf),
MNIST IDEC có pretrain đạt 93,16 ± 2,20%, cộng BRB đạt 94,19 ± 2,20%: tăng **1,03 điểm**,
10 seed, sai số là **SE**. Điều này hỗ trợ cải thiện trong giao thức của tác giả.
Không so trực tiếp các điểm này với Digits hoặc thay baseline bằng IDEC 2017.

“Phương pháp sau bổ sung cơ chế để giải quyết hạn chế trước đó. Tuy nhiên, trên cùng dữ liệu và mạng nhỏ,
cải thiện không tự xuất hiện ở mọi phương pháp. Kết quả hiện tại giúp đánh giá cơ chế và phát hiện độ nhạy,
chưa xác định phương pháp mạnh nhất toàn lĩnh vực 2025–2026. Em sẽ mở rộng thêm 2–3 bộ dữ liệu,
tăng seed, hoàn tất khảo sát toàn văn và đối chiếu cấu hình gốc.”

## Những cách nói cần tránh

| Dễ gây hiểu nhầm | Cách nói có căn cứ hơn |
|---|---|
| “Mô hình mới hơn nên tốt hơn.” | “Mô hình thêm cơ chế này; dưới giao thức được nêu, số liệu cho thấy…” |
| “IDEC tốt nhất.” | “IDEC có ACC trung bình cao nhất trong lượt Digits chính; hơn DEC 0,18 điểm và thắng 2/5 seed.” |
| “DECRA ổn định nhất vì std nhỏ nhất.” | “Std ACC nhỏ hơn, nhưng chất lượng và ARI giữa seed cũng thấp hơn.” |
| “DCSS kém.” | “Bản chuyển thể với σ=1 đạt thấp; đổi độ rộng giúp cải thiện, cho thấy độ nhạy khởi tạo.” |
| “Tăng 1,51%.” | “ACC tăng từ 86,55% lên 88,06%, tức tăng 1,51 điểm phần trăm.” |
| “Đã khảo sát xong 32 bài.” | “Đã lập danh mục 32 công trình; 2 phiếu toàn văn hoàn tất, 18 tóm tắt số liệu có nguồn.” |
| “Đã chứng minh thành phần thêm gây ra cải thiện.” | “Kết quả phù hợp kỳ vọng; cần thí nghiệm chỉ thay thành phần đó để kiểm tra nguyên nhân.” |
