"""Build an academic Vietnamese deep-clustering survey from verified research data.

Exports DOCX, Markdown and HTML; operational logs remain in experiment artifacts.
The original documents and measured training outputs are not modified.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import json
import math
import os
import re
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=7))
NAME = "Bao_cao_kiem_tra_va_thuc_nghiem"
NAMES = {"AE_KMeans": "AE + K-means", "IDEC_BRB": "IDEC + BRB (demo)",
         "DECRA": "DECRA (adaptation)", "SANE_IDEC": "IDEC + SANE (adaptation)", "DCSS": "DCSS (adaptation)"}
PAPERS = {
    "DEC": {"year": 2016, "paper_url": "https://proceedings.mlr.press/v48/xieb16.html",
            "code_url": "https://github.com/piiswrong/dec", "venue": "ICML"},
    "IDEC": {"year": 2017, "paper_url": "https://www.ijcai.org/proceedings/2017/243",
             "code_url": "https://github.com/XifengGuo/IDEC", "venue": "IJCAI"},
    "DECRA": {"year": 2024, "paper_url": "https://doi.org/10.1007/s11063-024-11586-0",
              "code_url": "https://github.com/lml-mengli/DECRA", "venue": "Neural Processing Letters"},
    "SANE_IDEC": {"year": 2026,
                  "paper_url": "https://proceedings.iclr.cc/paper_files/paper/2026/hash/63ef323523f3be8b58ed9277cc747485-Abstract-Conference.html",
                  "code_url": "https://github.com/notoaudrey/Samples-Are-Not-Equal", "venue": "ICLR"},
    "DCSS": {"year": 2026, "paper_url": "https://link.springer.com/article/10.1007/s10994-026-07026-w",
             "code_url": "https://github.com/gvardakas/Soft-Silhouette", "venue": "Machine Learning"},
}
YES = {"yes", "true", "1", "passed", "pass"}


def load_json(path: Path, required: bool = False) -> dict:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Thiếu tệp bắt buộc: {path}")
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_csv(path: Path, required: bool = False) -> list[dict[str, str]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Thiếu tệp bắt buộc: {path}")
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def yes(value: Any) -> bool:
    return str(value).lower().strip() in YES


def verified_quartile(row: dict) -> str:
    quartile = row.get("quartile", "").strip().upper()
    complete = all(row.get(key, "").strip() for key in
                   ["ranking_system", "ranking_year", "ranking_category", "ranking_source"])
    return quartile if quartile in {"Q1", "Q2", "Q3", "Q4"} and yes(row.get("quartile_verified")) and complete else "unknown"


def number(value: Any, digits: int = 2, scale: float = 1) -> str:
    try:
        value = float(value) * scale
        if not math.isfinite(value):
            return "chưa tính"
        return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except (TypeError, ValueError):
        return "chưa có"


def ms(row: dict, metric: str, scale: float = 100, digits: int = 2) -> str:
    return f"{number(row.get(metric + '_mean'), digits, scale)} ± {number(row.get(metric + '_std'), digits, scale)}"


def display_method(method: str) -> str:
    return NAMES.get(method, method)


def link(label: str, target: str) -> str:
    return f"[{label}]({target})" if target else label


class Report:
    """One semantic document used by all three output formats."""

    def __init__(self):
        self.blocks: list[dict] = []

    def title(self, text: str):
        self.blocks.append({"kind": "title", "text": text})

    def subtitle(self, text: str):
        self.blocks.append({"kind": "subtitle", "text": text})

    def contents(self, title: str, entries: list[str]):
        self.blocks.append({"kind": "contents", "title": title, "entries": entries})

    def caption(self, text: str):
        self.blocks.append({"kind": "caption", "text": text})

    def equation(self, text: str):
        match = re.search(r'\((\d+\.\d+)\)$', text)
        self.blocks.append({"kind": "equation", "text": text[:match.start()].strip() if match else text.strip(),
                            "number": '('+match[1]+')' if match else ''})

    def heading(self, text: str, level: int = 1):
        self.blocks.append({"kind": "heading", "text": text, "level": level})

    def p(self, text: str):
        self.blocks.append({"kind": "p", "text": text})

    def table(self, headers: list[str], rows: list[list[Any]], widths: list[float] | None = None):
        self.blocks.append({"kind": "table", "headers": headers,
                            "rows": [[str(x) for x in row] for row in rows], "widths": widths})

    def image(self, path: Path, caption: str):
        if path.exists():
            self.blocks.append({"kind": "image", "path": path, "caption": caption})

    def code(self, text: str, language: str = "text"):
        if not re.fullmatch(r"[A-Za-z0-9_+-]+", language):
            raise ValueError("Invalid code block language")
        self.blocks.append({"kind": "code", "text": text, "language": language})

    def details(self, title: str, text: str):
        self.blocks.append({"kind": "details", "title": title, "text": text})


def draw_timeline(registry: dict, methods: list[str], path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axis = plt.subplots(figsize=(10, 2.1), constrained_layout=True)
    axis.set_xlim(-.65, len(methods) - .35)
    axis.set_ylim(-.3, .8)
    axis.axis("off")
    for index, method in enumerate(methods):
        label = "SANE-inspired\nIDEC" if method == "SANE_IDEC" else method
        axis.text(index, .25, str(registry[method]["year"]) + "\n" + label,
                  ha="center", va="center", color="white", fontsize=12,
                  bbox={"boxstyle": "round,pad=0.65", "facecolor": "#174d69", "edgecolor": "none"})
        if index + 1 < len(methods):
            axis.annotate("", xy=(index + .68, .25), xytext=(index + .32, .25),
                          arrowprops={"arrowstyle": "->", "color": "#6b8393", "linewidth": 1.7})
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_report(out: Path, docs: Path, original_word: Path, report_name: str = NAME) -> Report:
    """Academic narrative: literature evidence and controlled adaptations are distinct."""
    import statistics

    tracker = load_csv(ROOT / "data/paper_tracker.csv", True)
    counts = load_json(out / "survey_counts.json", True)
    config = load_json(out / "config.json", True)
    runs = load_csv(out / "runs.csv", True)
    summary = load_csv(out / "summary.csv", True)
    literature = load_json(docs / "literature_context.json", True)
    metadata = load_json(ROOT / "data/metadata.json", True)
    ranking = load_json(docs / "references/journal_rankings.json", True)
    bibliography = {r['method']:r for r in load_json(docs / 'references/bibliography.json', True)['records']}
    verification = load_json(out / "verification.json", True)
    methods = list(config["methods"])
    seeds = list(config["seeds"])
    if methods != ["DEC", "IDEC", "DECRA", "DCSS"]:
        raise ValueError("This survey compares DEC/IDEC/DECRA/DCSS; select the four-method results.")
    expected = {(m, str(s)) for m in methods for s in seeds}
    if {(r["method"], r["seed"]) for r in runs} != expected or len(runs) != len(expected):
        raise ValueError("Incomplete or duplicated method/seed results.")
    if len(tracker) != counts["total_papers_in_tracker"]:
        raise ValueError("Survey counts do not match the literature catalog.")
    if verification.get("status") != "passed" or not verification.get("same_training_data_all_methods"):
        raise ValueError("Verify the common-data experiment before generating the survey.")
    data = Path(config["data"])
    data = data if data.is_absolute() else ROOT / data
    if hashlib.sha256(data.read_bytes()).hexdigest() != config["sha256_data"]:
        raise ValueError("The dataset differs from the measured experiment.")
    scores = {r["method"]: r for r in summary}
    papers = {r["method"]: r for r in tracker}
    refnum = {r["method"]: int(r["paper_id"].removeprefix("P")) for r in tracker}
    cite = lambda *names: " " .join(f"[{refnum[n]}]" for n in names)
    n = len(tracker)
    journals = [r for r in tracker if r["publication_type"] == "journal"]
    abbreviations = {"IEEE Transactions on Pattern Analysis and Machine Intelligence": "IEEE TPAMI",
                     "Neural Processing Letters": "Neural Processing Letters", "ACM Computing Surveys": "ACM CS"}
    doc = Report()

    def table(no: str, title: str, headers: list[str], rows: list[list[Any]], widths=None):
        doc.caption(f"Bảng {no}. {title}")
        doc.table(headers, rows, widths)

    def figure(no: str, title: str, path: Path):
        doc.image(path, f"Hình {no}. {title}")

    doc.title("ĐÁNH GIÁ HIỆU NĂNG VÀ ĐỘ ỔN ĐỊNH\nCỦA CÁC PHƯƠNG PHÁP PHÂN CỤM SÂU")
    doc.subtitle("BÀI KHẢO SÁT VÀ THỰC NGHIỆM SO SÁNH\nPhạm vi tài liệu: 2016–2026")
    doc.heading("TÓM TẮT")
    doc.p(f"Phân cụm sâu kết hợp học biểu diễn với tối ưu cấu trúc cụm để xử lý dữ liệu có chiều cao. "
          f"Bài khảo sát tổng hợp danh mục {n} công trình trong giai đoạn 2016–2026, gồm "
          f"{counts['publication_types']['conference']} bài hội nghị và {len(journals)} bài tạp chí, "
          "phân tích sự chuyển dịch từ tự huấn luyện dựa trên tâm đến bảo toàn cấu trúc, biến đổi biểu diễn "
          "và các cơ chế chú trọng độ ổn định. Bốn phương pháp DEC, IDEC, DECRA và DCSS được lựa chọn "
          "để thực nghiệm trên cùng bộ Digits gồm 1.797 mẫu, cùng kiến trúc autoencoder nền và năm seed. "
          "Thiết kế này tạo 20 lượt chạy chính, đánh giá đồng thời chất lượng, biến động giữa seed, "
          "mức đồng thuận của phân hoạch và chi phí tính toán.")
    doc.p(f"IDEC đạt ACC trung bình {number(scores['IDEC']['acc_mean'], 2, 100)}%, "
          f"cao hơn DEC {number((float(scores['IDEC']['acc_mean'])-float(scores['DEC']['acc_mean']))*100)} "
          "điểm phần trăm, trong khi DEC nhỉnh hơn ở NMI và ARI. DECRA có độ lệch chuẩn ACC nhỏ hơn "
          "nhưng chất lượng trung bình và mức đồng thuận phân hoạch thấp hơn. DCSS nhạy với độ rộng RBF "
          "khi chuyển sang embedding tuyến tính; thực nghiệm bổ sung sử dụng khởi tạo độ rộng theo dữ liệu "
          "cho thấy tác động lớn của yếu tố này. Kết quả cho thấy mốc công bố mới hơn không tự đảm bảo "
          "hiệu năng hoặc độ ổn định tốt hơn dưới một giao thức chung. Các triển khai là bản chuyển thể "
          "cơ chế, vì vậy kết luận giới hạn trong cấu hình và dữ liệu đã thực nghiệm, chưa xác định "
          "phương pháp mạnh nhất toàn lĩnh vực năm 2025–2026.")
    doc.p("Từ khóa: phân cụm sâu; học biểu diễn; autoencoder; hiệu năng; độ ổn định; DEC; IDEC; DECRA; DCSS.")

    doc.heading("CHƯƠNG I. TỔNG QUAN")
    doc.heading("1.1. Bối cảnh và động cơ nghiên cứu", 2)
    doc.p("Phân cụm là bài toán phân chia các đối tượng thành các nhóm dựa trên cấu trúc tương đồng, "
          "không sử dụng nhãn lớp để huấn luyện. Trên dữ liệu ảnh, văn bản hoặc dữ liệu có nhiều đặc trưng, "
          "khoảng cách trong không gian đầu vào có thể không phản ánh rõ cấu trúc cần phân nhóm. "
          "Các phương pháp phân cụm sâu học một biểu diễn gọn hơn, đồng thời điều chỉnh biểu diễn đó "
          "theo mục tiêu phân cụm. Quan hệ giữa học biểu diễn và phân cụm là trục phân loại quan trọng "
          "trong các tổng quan gần đây. " + cite("Survey-ACM"))
    doc.p("Các công trình thường báo cáo cải thiện điểm số trên những benchmark khác nhau, sử dụng "
          "kiến trúc, tiền huấn luyện và ngân sách tối ưu khác nhau. Một điểm ACC cao hơn có thể đến "
          "từ thay đổi phương pháp, nhưng cũng có thể đến từ đặc trưng tốt hơn, khởi tạo thuận lợi hoặc "
          "giao thức đánh giá khác. Do đó, khảo sát theo thời gian cần gắn tiến bộ về cơ chế với điều kiện "
          "tạo ra kết quả, thay vì sắp xếp các điểm công bố thành một thứ hạng chung.")
    doc.p("Độ ổn định là vấn đề riêng bên cạnh chất lượng trung bình. Một mô hình có thể đạt kết quả "
          "cao ở một lần chạy nhưng tạo các phân hoạch rất khác nhau khi đổi seed. Ngược lại, một mô hình "
          "có điểm số ít biến động vẫn có thể ổn định quanh một lời giải kém. Báo cáo vì vậy xem xét "
          "đồng thời chất lượng phân cụm, độ lệch chuẩn và mức đồng thuận giữa các phân hoạch.")
    doc.heading("1.2. Câu hỏi nghiên cứu", 2)
    doc.p("Câu hỏi thứ nhất là các hướng phân cụm sâu đã thay đổi cơ chế học như thế nào từ DEC/IDEC "
          "đến các công trình gần đây. Câu hỏi thứ hai là những cơ chế mới có cải thiện chất lượng và "
          "độ ổn định khi dùng cùng dữ liệu và điểm khởi tạo hay không. Câu hỏi thứ ba là mức độ nhạy "
          "với tham số và điều kiện triển khai có ảnh hưởng như thế nào đến lựa chọn phương pháp. "
          "Câu hỏi cuối cùng là bằng chứng hiện có đã đủ để xác định một phương pháp tốt nhất "
          "trong giai đoạn 2025–2026 hay chưa.")
    doc.heading("1.3. Mục tiêu, phạm vi và đóng góp", 2)
    doc.p("Nghiên cứu xây dựng danh mục tài liệu có định danh và nguồn, thống kê loại công bố, "
          "năm, phân hạng tạp chí, khả năng truy cập mã nguồn và dữ liệu; phân tích các phương pháp "
          "theo cơ chế; và thực hiện một so sánh có kiểm soát trên một bộ dữ liệu. Bài IDEC năm 2017 "
          "là tài liệu tham chiếu chính, còn DEC đóng vai trò phương pháp nền. DECRA và DCSS đại diện "
          "cho hai thay đổi cơ chế trong họ autoencoder. BRB và các ứng viên khác được giữ trong "
          "phần khảo sát để đối chiếu và cân nhắc việc mở rộng. " + cite("DEC", "IDEC", "DECRA", "DCSS", "BRB"))
    doc.p("Phạm vi thực nghiệm hiện giới hạn ở phân cụm đơn góc nhìn trên Digits và các bản chuyển thể "
          "dùng chung kiến trúc nhỏ. Khảo sát thư mục bao phủ cả một số hướng thị giác, sinh, không gian "
          "con và dữ liệu mất cân bằng để cung cấp bối cảnh, nhưng các hướng này không được đưa vào "
          "bảng chạy chung nếu cần đầu vào hoặc điều kiện huấn luyện khác. Kết quả tái hiện đúng kiến "
          "trúc và môi trường tác giả là một cấp bằng chứng khác với thực nghiệm chuyển thể trong báo cáo.")
    doc.heading("1.4. Khái niệm hiệu năng và độ ổn định", 2)
    doc.p("Hiệu năng được xem xét qua ACC, NMI, ARI và thời gian xử lý. ACC đo mức trùng khớp nhãn "
          "sau khi giải bài toán ghép nhãn cụm; NMI đo lượng thông tin chung giữa phân hoạch dự đoán "
          "và nhãn tham chiếu; ARI đo mức đồng thuận cặp đối tượng sau hiệu chỉnh ngẫu nhiên. "
          "Trong báo cáo, ACC/NMI/ARI được nhân 100 để trình bày theo phần trăm, còn ARI giữa seed "
          "giữ thang đo gốc.")
    doc.p("Độ ổn định có hai biểu hiện được đo: biến động điểm số giữa các seed và mức đồng thuận "
          "giữa các phân hoạch. Khả năng chịu nhiễu, thay đổi số cụm hoặc dịch chuyển phân phối là "
          "những khía cạnh khác của độ ổn định; chúng chưa được suy ra từ thí nghiệm đổi seed hiện tại.")

    doc.heading("CHƯƠNG II. PHƯƠNG PHÁP VÀ KẾT QUẢ KHẢO SÁT")
    doc.heading("2.1. Nguồn tài liệu và tiêu chí lựa chọn", 2)
    doc.p("Nguồn khảo sát bao gồm tài liệu tham chiếu được cung cấp, trang proceedings của hội nghị, "
          "trang nhà xuất bản, bản thảo công khai của tác giả và kho mã nguồn liên quan. Danh mục được "
          "mở rộng quanh các từ khóa deep clustering, deep embedded clustering, reconstruction, "
          "sample stability và reclustering. Các bản preprint và bản xuất bản của cùng công trình "
          "được đối chiếu để chỉ tính một lần; năm trong thống kê ưu tiên năm issue/proceedings đã xác minh.")
    doc.p("Việc lựa chọn có chủ đích, ưu tiên công trình phù hợp với câu hỏi về hiệu năng/độ ổn định "
          "và có mã nguồn công khai. Đây chưa phải một tổng quan hệ thống với truy vấn cơ sở dữ liệu "
          "và lưu đồ sàng lọc đầy đủ. Do đó, tần suất công bố và tỷ lệ mã nguồn trong danh mục chỉ "
          "mô tả mẫu khảo sát này, không ước lượng tỷ lệ tương ứng của toàn bộ lĩnh vực.")
    doc.p("Hồ sơ mỗi công trình ghi nhận phương pháp, năm, nơi công bố, loại tài liệu, nguồn mã, "
          "benchmark, số liệu đã trích xuất và trạng thái đọc toàn văn. Xác minh metadata, đọc một "
          "bảng hoặc kiểm tra README không được coi là hoàn tất đọc toàn văn. Tại thời điểm tổng hợp, "
          f"có {counts['full_text_reviews_completed']} phiếu đọc toàn văn hoàn tất cho DEC/IDEC và "
          f"{counts['paper_reported_numeric_summaries']} tóm tắt số liệu có nguồn; các hồ sơ còn lại "
          "chưa hoàn tất mọi trường thực nghiệm. Giới hạn này được giữ rõ khi diễn giải kết quả khảo sát.")
    doc.heading("2.2. Thống kê danh mục công trình", 2)
    table("2.1", "Quy mô và mức trích xuất của danh mục khảo sát", ["Hạng mục", "Số lượng", "Phạm vi diễn giải"], [
        ["Tổng công trình không trùng", n, "31 bài phương pháp và 1 bài tổng quan"],
        ["Bài hội nghị", counts['publication_types']['conference'], "84,4% danh mục"],
        ["Bài tạp chí", len(journals), "15,6% danh mục; mẫu số dùng thống kê Q"],
        ["Công trình từ năm 2023", counts['papers_from_2023_onward'], "50% danh mục"],
        ["Mã phương pháp công khai", counts['public_code_method_papers'], "Có nguồn mã; chưa đồng nghĩa đã chạy môi trường tác giả"],
        ["Bài tổng quan có thư viện/tài nguyên", counts['public_resources_survey_papers'], "Tách khỏi số thuật toán được thực nghiệm"],
        ["Phạm vi/tên benchmark đã đối chiếu", counts['dataset_scope_verified'], "Xác nhận tên/phạm vi, chưa xác minh toàn bộ link tải"],
        ["Dữ liệu công khai theo hồ sơ", counts['public_dataset_papers'], "Khai báo có nguồn; khác việc tải đủ dữ liệu bài gốc"],
        ["Tóm tắt số liệu có nguồn", counts['paper_reported_numeric_summaries'], "Có thể từ bảng, abstract hoặc README; không phải bảng đã tái hiện"],
        ["Phiếu đọc toàn văn hoàn tất", counts['full_text_reviews_completed'], "DEC và IDEC"],
        ["Môi trường mã tác giả đã chạy", counts['original_code_smoke_tested'], "Thực nghiệm báo cáo dùng bản chuyển thể độc lập"],
    ], [2.1, .75, 3.35])
    table("2.2", "Phân bố công trình theo năm công bố", ["Năm", "Số công trình"],
          [[year, value] for year, value in counts['papers_by_year'].items()], [2.0, 4.2])
    doc.p("Danh mục bao phủ các mốc sớm về embedding và phân cụm dựa trên tâm, các hướng tự giám sát "
          "thị giác, và các công trình gần đây về độ tin cậy, mẫu ổn định, reclustering và hình học cụm. "
          "Phân bố theo năm chịu ảnh hưởng của tiêu chí chọn mẫu; số lượng trong từng năm không được "
          "sử dụng như một chỉ báo về tốc độ tăng trưởng chung của lĩnh vực.")
    doc.heading("2.3. Phân hạng tạp chí và chất lượng nguồn", 2)
    doc.p("Báo cáo dùng SCImago/SJR best quartile với cùng năm tham chiếu 2024 để giữ thống nhất "
          "trong thống kê. Best quartile là phân hạng tốt nhất của tạp chí trên các ngành được xếp hạng; "
          "không phải đánh giá chất lượng riêng của từng bài. Năm tham chiếu khác năm xuất bản của "
          "một số công trình, vì vậy các giá trị dưới đây không được gọi là Q tại mọi năm công bố "
          "hoặc phân hạng mới nhất năm 2026. Hội nghị không được gán Q1–Q4 của tạp chí. [35]")
    table("2.3", "Phân hạng các tạp chí theo SJR best quartile 2024", ["Công trình", "Năm bài", "Tạp chí", "Q tham chiếu"],
          [[f"{r['method']} [{refnum[r['method']]}]", r['year'], abbreviations.get(r['venue'], r['venue']),
            verified_quartile(r).replace("unknown", "Chưa xác minh")] for r in journals], [1.3, .65, 2.65, 1.6])
    table("2.4", "Tổng hợp phân hạng trên năm bài tạp chí", ["Nhóm", "Số bài", "Tỷ lệ trên bài tạp chí"],
          [[q, counts['journal_quartiles'][q], number(counts['journal_quartile_percent'][q], 1)+"%"] for q in ['Q1','Q2','Q3','Q4']] +
          [["Chưa xác minh", counts['journal_quartile_unknown'], "20,0%"]], [2.0, 1.0, 3.2])
    doc.p("Bằng chứng phân hạng gồm nội dung được lập chỉ mục trên trang chính chủ SCImago; truy cập "
          "trực tiếp trong đợt tra cứu bị hạn chế. Machine Learning được giữ ở nhóm chưa xác minh đủ "
          "nguồn chính thay vì suy ra Q từ uy tín tạp chí. Riêng Pattern Recognition Letters có "
          "best quartile Q1 năm 2024 nhưng ngành Artificial Intelligence là Q2 trong cả năm 2020 "
          "và 2024. Hai cách xét này không được trộn vào cùng một tổng. Q3/Q4 bằng 0 là không có "
          "bài được ghi nhận trong các nhóm đó của mẫu hiện tại, không phản ánh toàn bộ lĩnh vực. [35]")
    doc.p("Mức uy tín của nơi công bố hỗ trợ lựa chọn tài liệu, nhưng không thay thế đánh giá phương "
          "pháp. Khả năng kiểm tra mã, giao thức đánh giá, số lần chạy và mức báo cáo sai số cũng là "
          "các yếu tố cần xem xét khi dùng số liệu để lập luận về hiệu năng hoặc độ ổn định.")
    doc.heading("2.4. Các hướng phương pháp trong danh mục", 2)
    groups = [
        ("Autoencoder và tối ưu cụm", ['DEC','IDEC','DCN','DEC-DA','DECRA','DCEC','DECCS','DCSS','DKM'],
         "Điều chỉnh embedding bằng loss cụm, tái tạo, nhất quán hoặc hình học cụm; phù hợp trục thực nghiệm chung."),
        ("Nhãn giả, prototype và cập nhật trực tuyến", ['DeepCluster','DPAC','CA','ProPos','SwAV'],
         "Tạo mục tiêu học từ cấu trúc cụm/prototype; hiệu quả phụ thuộc đặc trưng, nhãn giả và tiền huấn luyện."),
        ("Nhất quán, tương phản và độ ổn định", ['SCAN','CC','BRB','IIC','NNM','DivClust','LFSS','DCBoost','SANE','CDC'],
         "Khai thác lân cận, các bản biến đổi dữ liệu, mẫu tin cậy, reset hoặc calibration; khái niệm ổn định khác nhau giữa các bài."),
        ("Mục tiêu và chế độ bổ sung", ['VaDE','JULE','PRCut','P2OT','CPP','IDC','DSCNet'],
         "Mô hình sinh, phân cấp, graph cut, mất cân bằng, đặc trưng ngoài, giải thích và không gian con; cần protocol riêng."),
    ]
    assert sum(len(g[1]) for g in groups) == 31
    table("2.5", "Phân nhóm cơ chế phục vụ phân tích trong báo cáo", ["Nhóm", "Công trình", "Đặc trưng"],
          [[title, "; ".join(f"{name} [{refnum[name]}]" for name in names), detail] for title,names,detail in groups], [1.3, 2.0, 2.9])
    doc.p("Bốn nhóm là cách tổ chức của báo cáo nhằm trả lời câu hỏi thực nghiệm, không phải các lớp "
          "loại trừ lẫn nhau hoặc bản sao nguyên văn taxonomy của bài tổng quan ACM. Một công trình "
          "có thể đồng thời sử dụng prototype, tự giám sát và lựa chọn mẫu; ở đây nó được xếp theo "
          "cơ chế nổi bật nhất đối với mục tiêu phân tích. Bài tổng quan ACM cung cấp bối cảnh về "
          "cách tương tác giữa mô-đun biểu diễn và mô-đun phân cụm. " + cite("Survey-ACM"))
    doc.heading("2.5. Tiến trình nghiên cứu và các khoảng trống", 2)
    doc.p("Giai đoạn 2016–2018 chú trọng học embedding và mục tiêu cụm đồng thời. DEC làm sắc phân "
          "phối gán cụm, IDEC bổ sung reconstruction, còn DCN hướng mục tiêu về không gian "
          "phù hợp K-means. DKM có preprint năm 2018 và bản journal năm 2020, tiếp tục hướng "
          "tối ưu đồng thời này. DCEC mở rộng biểu diễn ảnh bằng convolution; DEC-DA khai thác tăng cường "
          "dữ liệu. Những thay đổi này mở rộng khả năng học nhưng vẫn chịu ảnh hưởng của chất lượng "
          "tiền huấn luyện và khởi tạo. " + cite("DEC","IDEC","DCN","DKM","DCEC","DEC-DA"))
    doc.p("Trong giai đoạn 2019–2024, nhiều hướng sử dụng thông tin nhất quán, tương phản, lân cận "
          "hoặc prototype. IIC tối ưu thông tin chung; SCAN kết hợp lân cận với tự gán nhãn; CC học "
          "tương phản ở mức đối tượng và cụm. Các hướng như ProPos, DPAC và DECCS tiếp tục điều "
          "chỉnh biểu diễn hoặc quan hệ cụm. DECRA vẫn theo họ autoencoder nhưng bổ sung khả năng "
          "biến đổi embedding thay vì chỉ giữ reconstruction đầu vào. " + cite("IIC","SCAN","CC","ProPos","DPAC","DECCS","DECRA"))
    doc.p("Các công trình 2025–2026 chú ý rõ hơn đến hạn chế của tự huấn luyện và sự không đồng đều "
          "giữa các mẫu. BRB can thiệp quá trình tối ưu bằng reset và reclustering; LFSS dùng ổn định "
          "mẫu; DCBoost bổ sung tự giám sát dựa trên lân cận; SANE kết hợp khởi tạo theo mật độ và "
          "lựa chọn mẫu động. CDC chú trọng calibration của xác suất, còn DCSS tối ưu trực tiếp "
          "tính gọn và tách biệt của cụm. Các mục tiêu này liên quan nhưng không đồng nghĩa: "
          "ECE thấp hơn, tốc độ nhanh hơn và ACC cao hơn là ba kết quả khác nhau. " + cite("BRB","LFSS","DCBoost","SANE","CDC","DCSS"))
    doc.p("Khoảng trống cần xử lý là việc so sánh các cơ chế dưới cùng điều kiện, báo cáo cả biến "
          "động giữa seed và tính nhất quán của phân hoạch, và kiểm tra độ nhạy khi chuyển kiến trúc. "
          "Các điểm số trong tài liệu cung cấp bối cảnh, còn thực nghiệm Chương IV xem xét một "
          "phần khoảng trống này với giao thức chung.")

    doc.heading("CHƯƠNG III. PHÂN TÍCH CÁC PHƯƠNG PHÁP TIÊU BIỂU")
    doc.heading("3.1. Khung biểu diễn và phân cụm chung", 2)
    doc.p("Gọi X = {xᵢ} là tập dữ liệu, fθ là encoder, gψ là decoder, zᵢ = fθ(xᵢ) là biểu diễn "
          "và μⱼ là tâm cụm thứ j. Autoencoder học tái tạo x̂ᵢ = gψ(zᵢ), trong khi thành phần phân "
          "cụm tác động đến zᵢ và/hoặc μⱼ. Reconstruction bảo toàn thông tin đầu vào; loss phân "
          "cụm tạo áp lực để biểu diễn phù hợp cấu trúc phân nhóm. Hai mục tiêu có thể hỗ trợ nhau "
          "hoặc xung đột khi thông tin cần tái tạo không phải thông tin hữu ích cho phân cụm.")
    doc.equation("E = (1/ND) ∑ᵢ ∑ᵈ (xᵢᵈ − x̂ᵢᵈ)²                                      (3.1)")
    doc.p("Trong (3.1), N là số mẫu và D là số đặc trưng. Các hệ số trong loss cần được hiểu cùng "
          "quy ước chuẩn hóa; cùng một hệ số số học nhưng khác mẫu số N hoặc NK tạo trọng số "
          "hiệu dụng khác nhau. Đây là điểm cần giữ rõ khi đối chiếu mô tả bài báo với mã công khai.")
    doc.heading("3.2. DEC: tự huấn luyện dựa trên phân phối mục tiêu", 2)
    doc.p("DEC khởi tạo encoder từ autoencoder, khởi tạo tâm trong embedding, sau đó tối ưu encoder "
          "và tâm bằng phân phối gán mềm Student-t. Phân phối mục tiêu P được xây dựng từ Q để "
          "tăng trọng số các gán có độ tin cậy cao và điều chỉnh tần suất cụm. Loss KL hướng Q "
          "đến P. Decoder không tiếp tục được dùng để ràng buộc biểu diễn trong giai đoạn phân cụm. " + cite("DEC"))
    doc.equation("qᵢⱼ = (1 + ‖zᵢ − μⱼ‖²)⁻¹ / ∑ₖ (1 + ‖zᵢ − μₖ‖²)⁻¹                  (3.2)")
    doc.equation("fⱼ = ∑ᵢ qᵢⱼ ;  pᵢⱼ = (qᵢⱼ²/fⱼ) / ∑ₖ(qᵢₖ²/fₖ)                              (3.3)")
    doc.equation("Kₙ = (1/N) ∑ᵢ ∑ⱼ pᵢⱼ ln(pᵢⱼ/qᵢⱼ) ;  LDEC = Kₙ                           (3.4)")
    doc.p("DEC là mốc nền phù hợp vì cơ chế gán mềm và tự làm sắc đơn giản, dễ phân tích ảnh hưởng "
          "của khởi tạo. Điểm yếu là mục tiêu tự tạo không đảm bảo phản ánh đúng lớp ngữ nghĩa. "
          "Nếu khởi tạo kém, quá trình làm sắc có thể củng cố một cấu trúc chưa tốt hoặc làm "
          "biến dạng embedding theo các gán sai.")
    doc.heading("3.3. IDEC: bảo toàn cấu trúc bằng reconstruction", 2)
    doc.p("IDEC giữ decoder khi tối ưu phân cụm và bổ sung lỗi tái tạo. Thiết kế này nhằm hạn chế "
          "việc loss phân cụm làm mất cấu trúc có ích của biểu diễn. Trong triển khai chung, "
          "loss được viết dưới dạng E + γKₙ, với γ = 0,1; cách ghi hệ số có thể khác khi bài gốc "
          "đổi thứ tự hoặc chuẩn hóa hai thành phần. " + cite("IDEC"))
    doc.equation("LIDEC = E + γKₙ ;  γ = 0,1 trong thực nghiệm                                 (3.5)")
    doc.p("IDEC được chọn vì là bài target và tạo một đối chiếu trực tiếp với DEC: cùng gán mềm "
          "và mục tiêu tự huấn luyện, bổ sung reconstruction khi phân cụm. Ưu điểm dự kiến là "
          "hạn chế biến dạng; điểm đánh đổi là thông tin tái tạo có thể chứa nhiễu hoặc đặc trưng "
          "không liên quan đến cụm. Lợi ích thực tế phụ thuộc cân bằng loss và dữ liệu, không "
          "được khẳng định chỉ từ việc kiến trúc có thêm decoder.")
    doc.heading("3.4. DECRA: biến đổi embedding và nhất quán tái tạo", 2)
    doc.p("DECRA đề xuất autoencoder có cấu trúc residual/adaptive để điều chỉnh biểu diễn theo "
          "nhiệm vụ phân cụm. Bài báo mô tả embedding bổ sung theo dạng residual; mã công khai "
          "sử dụng phép biến đổi affine tại embedding và hai đường decode dùng chung tham số. "
          "Bản chuyển thể của báo cáo đi theo loss trong mã công khai, không đồng nhất hai mô "
          "tả khi chưa đối chiếu đầy đủ. " + cite("DECRA"))
    doc.equation("z̃ = Az + b ;  x̂ = gψ(z) ;  x̃ = gψ(z̃)                                         (3.6)")
    doc.equation("Econs = MSE(x̃, x̂) ;  LDECRA = 2E + 0,6Econs + 0,1Kₙ/K                      (3.7)")
    doc.p("Trong (3.7), K = 10 là số cụm của thực nghiệm. Phép chia KL cho K phản ánh phép lấy "
          "trung bình theo mẫu và cụm trong mã tác giả; reconstruction consistency truyền "
          "gradient qua cả hai đường decode. So với IDEC, biến đổi affine tạo thêm khả năng "
          "điều chỉnh embedding nhưng tăng số tham số và yêu cầu cân bằng mục tiêu. Thực nghiệm "
          "hiện dùng tiền huấn luyện autoencoder thông thường, chưa dùng quy trình tiền huấn "
          "luyện residual riêng và chưa đo khả năng chịu nhiễu bằng một thử nghiệm độc lập.")
    doc.heading("3.5. DCSS: tối ưu hình học cụm bằng soft silhouette", 2)
    doc.p("DCSS sử dụng soft silhouette để khuyến khích cụm gọn và tách biệt, kết hợp reconstruction "
          "và entropy. Phân phối cụm được tạo từ Gaussian RBF và softmax; độ rộng RBF là tham số "
          "học được. Phương pháp được chọn làm ứng viên 2026 vì cùng họ autoencoder, có mã công "
          "khai và bài báo đối chiếu trực tiếp các phương pháp DEC/IDEC/DECRA. Điều này tạo cơ sở "
          "phân tích cơ chế, không xác lập DCSS mạnh nhất năm 2026. " + cite("DCSS"))
    doc.equation("φᵢⱼ = exp(−‖zᵢ − μⱼ‖²/σⱼ²) ;  qᵢⱼ = softmaxⱼ(φᵢⱼ/T)                    (3.8)")
    doc.equation("LDCSS = E + λ(1 − Ssoft) + βH₂(Q)                                           (3.9)")
    doc.p("Trong thực nghiệm chính, λ = β = 0,01; T = 0,25; σⱼ khởi tạo bằng 1. Entropy H₂ "
          "dùng log cơ số 2 và lấy trung bình theo mẫu. Soft silhouette được tính trong minibatch. "
          "Mã công khai dùng tổng khoảng cách có trọng số xác suất, không chia cho khối lượng "
          "cụm; phương trình (13) trong bài có phép chia theo tổng xác suất cụm sau khi loại "
          "mẫu đang xét. Mục 5.3 của bài ghi temperature 20, trong khi mã dùng 0,25. "
          "Triển khai chung theo phiên bản mã và giữ các khác biệt này như giới hạn khi suy "
          "rộng kết quả.")
    doc.p("DCSS đưa hình học cụm vào mục tiêu học một cách trực tiếp hơn KL tự làm sắc. Tuy nhiên, "
          "RBF phụ thuộc scale embedding và độ rộng khởi tạo; gán gần đều có thể tạo tín hiệu "
          "phân cụm yếu. Tính khoảng cách giữa mẫu trong minibatch cũng làm chi phí và hành vi "
          "loss phụ thuộc kích thước batch. Những yếu tố này cần được đánh giá cùng chất lượng.")
    doc.heading("3.6. BRB và các ứng viên về độ ổn định", 2)
    doc.p("BRB là cơ chế bổ sung cho các phương pháp dựa trên tâm, kết hợp soft reset encoder, "
          "reclustering và điều chỉnh trạng thái tối ưu của tâm để vượt hạn chế trong quá trình "
          "học lặp. Nó không phải một họ mô hình độc lập theo cùng nghĩa với DEC hoặc DCSS. "
          "BRB được giữ trong phần số liệu công bố và có thể được đưa vào thực nghiệm sau, "
          "nhưng không được mặc định là phương pháp tốt nhất. " + cite("BRB"))
    doc.p("LFSS, DCBoost và SANE là các ứng viên gần đây đáng xem xét vì chú trọng ổn định mẫu, "
          "lân cận hoặc lựa chọn mẫu động. CDC giải quyết calibration; CPP sử dụng đặc trưng "
          "tiền huấn luyện có thông tin ngoài. Khi so sánh các hướng này với họ autoencoder, cần "
          "đồng nhất đầu vào, ngân sách và thông tin sẵn có, hoặc tách thành các nhóm benchmark "
          "riêng. Cải thiện calibration hay linear evaluation không được đổi thành cải thiện "
          "ACC phân cụm. " + cite("LFSS","DCBoost","SANE","CDC","CPP","SwAV"))
    table("3.1", "Lý do chọn bốn mốc và giả thuyết cần đánh giá", ["Mốc", "Thay đổi cơ chế", "Giả thuyết/điểm đánh đổi"], [
        ["DEC 2016", "KL và mục tiêu tự làm sắc", "Baseline; nhạy khởi tạo và gán sai"],
        ["IDEC 2017", "Bổ sung reconstruction", "Hạn chế biến dạng; có thể giữ thông tin không phục vụ cụm"],
        ["DECRA 2024", "Nhánh adaptive và consistency", "Biểu diễn linh hoạt hơn; thêm tham số và yêu cầu tiền huấn luyện"],
        ["DCSS 2026", "Soft silhouette, entropy và RBF", "Cụm gọn/tách biệt; nhạy scale, độ rộng và batch"],
    ], [1.0, 2.0, 3.2])
    timeline = docs / (report_name + "_timeline.png")
    registry = {m: {**PAPERS.get(m, {}), **config.get('method_registry', {}).get(m, {})} for m in methods}
    draw_timeline(registry, methods, timeline)
    figure("3.1", "Các mốc phương pháp được chọn cho thực nghiệm; mũi tên biểu thị thời gian công bố", timeline)
    doc.p("Các mốc giúp theo dõi thay đổi cơ chế qua thời gian. Khoảng cách năm không biểu thị mức "
          "cải thiện, và mũi tên không khẳng định tất cả các bài là quan hệ kế thừa trực tiếp. "
          "Lựa chọn ứng viên cuối có thể thay đổi khi có bằng chứng phù hợp hơn từ khảo sát hoặc "
          "thực nghiệm mở rộng.")

    doc.heading("CHƯƠNG IV. THIẾT KẾ VÀ KẾT QUẢ THỰC NGHIỆM")
    doc.heading("4.1. Dữ liệu và tiền xử lý", 2)
    doc.p("Thực nghiệm sử dụng bộ Digits được phân phối qua scikit-learn, có nguồn gốc từ "
          "UCI Optical Recognition of Handwritten Digits. Bản dùng ở đây gồm 1.797 ảnh xám "
          "8×8 và 10 lớp chữ số, khác với toàn bộ bộ UCI gồm 5.620 mẫu. Mỗi ảnh được làm phẳng "
          "thành 64 đặc trưng; giá trị pixel ban đầu trong [0,16] được chia cho 16 để đưa về "
          "[0,1]. Nguồn UCI ghi giấy phép CC BY 4.0. [33] [34]")
    table("4.1", "Đặc điểm dữ liệu thực nghiệm", ["Thuộc tính", "Giá trị"], [
        ["Số mẫu", metadata['n_samples']], ["Kích thước ảnh", "8 × 8 pixel, mức xám"],
        ["Số đặc trưng", metadata['n_features']], ["Số cụm đặt trước", metadata['known_n_clusters']],
        ["Tiền xử lý", "Chia pixel cho 16; cùng thứ tự mẫu cho mọi phương pháp"],
        ["Sử dụng nhãn", "Chỉ tính metric sau huấn luyện"],
        ["Chế độ đánh giá", "Transductive: học và phân cụm toàn bộ X; không có tập chưa thấy"],
    ], [2.1, 4.1])
    table("4.2", "Phân bố mẫu theo lớp tham chiếu", ["Chữ số", "Số mẫu"],
          [[label, value] for label, value in metadata['class_counts'].items()], [2.0, 4.2])
    figure("4.1", "Ví dụ ảnh chữ số trong bộ Digits", out / "sample_images.png")
    doc.p("Digits có quy mô nhỏ, cho phép thực hiện nhiều seed và kiểm tra các cơ chế với chi phí "
          "thấp. Tuy nhiên, ảnh 8×8 không đại diện cho ảnh tự nhiên, văn bản hoặc dữ liệu có nhiều "
          "góc nhìn. Nó phù hợp cho một bước so sánh ban đầu, chưa đủ làm cơ sở suy rộng toàn lĩnh vực.")
    doc.heading("4.2. Giao thức so sánh và kiến trúc nền", 2)
    doc.p("Bốn phương pháp được chạy trên cùng X, cùng thứ tự mẫu, cùng số cụm và năm seed "
          "0–4. Với mỗi seed, autoencoder được tiền huấn luyện từ đầu bằng MSE; K-means được "
          "chạy trên embedding để khởi tạo tâm. Trọng số tiền huấn luyện và tâm ban đầu được "
          "sao chép cho từng phương pháp trong seed đó. DECRA thêm nhánh affine, DCSS thêm "
          "độ rộng RBF; các thành phần riêng được ghi nhận như khác biệt cơ chế.")
    table("4.3", "Cấu hình thực nghiệm chính", ["Tham số", "Giá trị", "Vai trò trong so sánh"], [
        ["Encoder / decoder", "64–64–32–10 / 10–32–64–64", "Kiến trúc nền chung"],
        ["Hàm kích hoạt", "ReLU; latent tuyến tính; output sigmoid", "Cùng scale và dạng biểu diễn nền"],
        ["Tiền huấn luyện", f"{config['pretrain_epochs']} epoch", "Học reconstruction trước phân cụm"],
        ["Huấn luyện phân cụm", f"{config['cluster_epochs']} epoch", "Ngân sách epoch chung"],
        ["Minibatch", config['batch_size'], "DCSS tính soft silhouette trong batch"],
        ["Optimizer / learning rate", "Adam / 0,001", "Áp dụng cho mọi cấu hình"],
        ["K-means", "K = 10; 20 khởi tạo", "Tâm chung trong từng seed"],
        ["Cập nhật mục tiêu P", "Mỗi 5 epoch, trên toàn bộ X", "DEC, IDEC và DECRA; không áp dụng DCSS"],
        ["Số seed / lượt chính", f"{len(seeds)} / {len(runs)}", "Đánh giá biến động và so sánh ghép cặp"],
        ["Tối ưu hệ số loss", "Giữ cấu hình cố định trong lượt chính", "Không chọn bằng ACC trên nhãn đánh giá"],
    ], [1.65, 1.8, 2.75])
    doc.p("Một epoch tương ứng một lượt đi qua dữ liệu; với batch 128, mỗi epoch có 15 minibatch. "
          "DEC/IDEC/DECRA làm mới P trước các epoch theo lịch, giữ P cố định khi tính gradient "
          "trong minibatch. DCSS tính xác suất RBF và loss hình học trực tiếp, không dùng P. "
          "Mọi mô hình được đánh giá tại điểm kết thúc ngân sách đã định, không chọn epoch tốt "
          "nhất dựa trên nhãn.")
    doc.p("Các triển khai sử dụng NumPy trên CPU trong môi trường Windows, với một luồng xử lý "
          "được cấu hình. So sánh dùng chung backbone nhằm giảm khác biệt kiến trúc, nhưng đồng "
          "thời thay đổi một số giả định so với công trình gốc. Kết quả vì vậy là đánh giá các "
          "bản chuyển thể cơ chế, không phải chứng nhận tái hiện toàn bộ bảng benchmark tác giả.")
    doc.heading("4.3. Độ đo, cách tổng hợp và kiểm chứng", 2)
    doc.equation("ACC = maxπ (1/N) ∑ᵢ 1[yᵢ = π(cᵢ)]                                       (4.1)")
    doc.equation("NMI = 2I(Y; C) / (H(Y) + H(C))                                            (4.2)")
    doc.p("Trong (4.1), π là phép hoán vị nhãn cụm tối ưu, được xác định bằng ghép nhãn Hungarian. "
          "Công thức (4.2) sử dụng chuẩn hóa bằng trung bình số học của entropy. ARI hiệu chỉnh "
          "mức đồng thuận cặp đối tượng so với ngẫu nhiên và không phụ thuộc số hiệu nhãn cụm. "
          "Ngoài ARI với nhãn tham chiếu, ARI giữa seed so sánh hai phân hoạch dự đoán mà không "
          "cần dùng nhãn lớp.")
    doc.equation("m̄ = (1/R) ∑ᵣ mᵣ ;  s = √[∑ᵣ(mᵣ − m̄)² / (R − 1)] ;  R = 5                 (4.3)")
    doc.p("Các bảng chính trình bày trung bình và độ lệch chuẩn mẫu trên năm seed. Mỗi phương "
          "pháp có 10 cặp seed để đo đồng thuận phân hoạch; các cặp dùng chung lượt chạy nên "
          "không được coi là 10 quan sát độc lập khi suy luận thống kê. So sánh DEC–IDEC còn "
          "được ghép theo seed để giảm ảnh hưởng của điểm khởi tạo chung.")
    doc.p("Thời gian một lượt bao gồm tiền huấn luyện, khởi tạo K-means, huấn luyện phân cụm và "
          "ghi nhận loss, không bao gồm đánh giá cuối, vẽ biểu đồ và xuất tệp. Do tiền huấn luyện "
          "được dùng chung trong từng seed, thời gian báo cáo cho từng mô hình là chi phí nếu "
          "chạy độc lập, không phải tổng thời gian thực tế của cả chiến dịch.")
    doc.p("Đạo hàm được đối chiếu bằng sai phân hữu hạn; nhãn cụm được tính lại từ trọng số đã "
          "lưu và metric được tính lại từ các dự đoán. Các kiểm chứng hỗ trợ độ tin cậy số học "
          "của implementation và bảng kết quả, nhưng không thay thế xác minh đúng giao thức "
          "tác giả hoặc đánh giá trên các benchmark khác.")
    doc.heading("4.4. Kết quả trên cùng bộ Digits", 2)
    table("4.4", "Chất lượng phân cụm của 20 lượt thực nghiệm chính", ["Phương pháp", "ACC (%)", "NMI (%)", "ARI (%)"],
          [[m if m != 'DCSS' else 'DCSS, σ = 1', ms(scores[m],'acc'), ms(scores[m],'nmi'), ms(scores[m],'ari')] for m in methods], [1.35, 1.6, 1.6, 1.65])
    table("4.5", "Độ ổn định phân hoạch và chi phí của các phương pháp", ["Phương pháp", "ARI giữa seed", "Thời gian (s)", "Cặp seed"],
          [[m, ms(scores[m],'pairwise_ari',1,4), ms(scores[m],'standalone_seconds',1,2), scores[m]['n_pairs']] for m in methods], [1.25, 2.0, 2.15, .8])
    doc.p("IDEC có ACC và mức đồng thuận giữa seed cao nhất trong lượt chính, nhưng DEC có NMI "
          "và ARI với nhãn tham chiếu cao hơn một chút. DECRA có độ lệch chuẩn ACC thấp hơn "
          "DEC/IDEC, đồng thời điểm trung bình và đồng thuận phân hoạch thấp hơn. DCSS với độ "
          "rộng ban đầu bằng 1 có chất lượng thấp và biến động lớn. Vì vậy, thứ hạng theo một "
          "metric không đủ mô tả đầy đủ hiệu năng và độ ổn định.")
    figure("4.2", "Chất lượng phân cụm và thời gian của các bản chuyển thể trên Digits", out / "performance.png")
    doc.heading("4.5. Phân tích ghép cặp và độ ổn định", 2)
    per_seed = {m:{int(r['seed']):float(r['acc'])*100 for r in runs if r['method']==m} for m in methods}
    deltas = [per_seed['IDEC'][int(s)]-per_seed['DEC'][int(s)] for s in seeds]
    table("4.6", "ACC theo seed và chênh lệch IDEC so với DEC", ["Seed", "DEC (%)", "IDEC (%)", "ΔACC (điểm %)"],
          [[s, number(per_seed['DEC'][int(s)]), number(per_seed['IDEC'][int(s)]), number(d)] for s,d in zip(seeds,deltas)], [.65, 1.75, 1.75, 2.05])
    doc.p(f"Chênh lệch ghép cặp trung bình là {number(statistics.mean(deltas),4)} ± "
          f"{number(statistics.stdev(deltas),4)} điểm phần trăm; IDEC cao hơn DEC ở "
          f"{sum(d>0 for d in deltas)}/{len(seeds)} seed. Kết quả không cho thấy ưu thế nhất quán "
          "của IDEC trên bộ Digits với cấu hình này. Biến động chung giữa seed lớn hơn chênh lệch "
          "trung bình của hai phương pháp, nhưng so sánh ghép cặp mới là bằng chứng phù hợp để "
          "xem xét mức cải thiện khi khởi tạo được dùng chung.")
    figure("4.3", "Biến động ACC và mức đồng thuận phân hoạch giữa các seed", out / "stability.png")
    doc.p("DEC có chi phí thấp nhất và chất lượng gần IDEC. Reconstruction của IDEC giúp bổ sung "
          "ràng buộc biểu diễn nhưng chưa tạo cải thiện rõ trong thí nghiệm này. DECRA làm tăng "
          "chi phí và chưa cải thiện chất lượng; điều đó có thể liên quan tiền huấn luyện chung, "
          "chuẩn hóa loss hoặc ngân sách, không đủ để kết luận DECRA nguyên gốc kém hơn. Các "
          "giả thuyết này cần thử nghiệm riêng thay vì được coi là nguyên nhân đã xác nhận.")
    figure("4.4", "Hình chiếu PCA hai chiều minh họa các phân hoạch ở seed 0", out / "embeddings.png")
    doc.p("Hình chiếu hai chiều hỗ trợ quan sát cấu trúc biểu diễn nhưng không thay thế metric "
          "trong không gian học. Seed 0 được dùng để minh họa, không được chọn vì cho kết quả "
          "cao nhất. Kết luận chính dựa trên toàn bộ năm seed và các bảng tổng hợp.")
    doc.heading("4.6. Độ nhạy của DCSS với khởi tạo RBF", 2)
    doc.p("Chẩn đoán trên embedding tiền huấn luyện của seed 0 không sử dụng nhãn cho thấy "
          "trung vị khoảng cách bình phương đến tâm gần nhất khoảng 7,21. Với σ = 1, Gaussian "
          "activation tương ứng chỉ khoảng 0,00074; xác suất cụm lớn nhất trung bình khoảng "
          "0,1068, gần mức 0,1 của phân phối đều trên 10 cụm. Điều này gợi ý sự không tương "
          "thích giữa độ rộng cố định và scale embedding tuyến tính trong bản chuyển thể.")
    ablation_path = ROOT / 'results/dcss_width_ablation_20261013'
    ablation = load_csv(ablation_path / 'summary.csv', True)[0]
    ablation_config = load_json(ablation_path / 'config.json', True)
    ablation_check = load_json(ablation_path / 'verification.json', True)
    if ablation_config['sha256_training_X'] != config['sha256_training_X'] or ablation_check.get('status') != 'passed':
        raise ValueError('DCSS ablation is not verified on the same X.')
    doc.equation("σⱼ = √[(1/|Cⱼ|) ∑ᵢ∈Cⱼ ‖zᵢ − μⱼ‖²]                                    (4.4)")
    doc.p("Một thực nghiệm bổ sung khởi tạo σ theo RMS khoảng cách trong từng cụm K-means ban "
          "đầu, giữ cùng X, seed, trọng số tiền huấn luyện và tâm. Chỉ X và phân hoạch khởi tạo "
          "được dùng để tính độ rộng, không dùng nhãn hoặc tìm kiếm theo ACC. Phép bổ sung "
          "được đề xuất sau khi quan sát lượt chính nên có tính thăm dò và được trình bày riêng.")
    table("4.7", "Đối chiếu khởi tạo độ rộng RBF của DCSS", ["Khởi tạo", "ACC (%)", "NMI (%)", "ARI (%)"],
          [["σ = 1 (lượt chính)", ms(scores['DCSS'],'acc'), ms(scores['DCSS'],'nmi'), ms(scores['DCSS'],'ari')],
           ["σ = RMS (bổ sung)", ms(ablation,'acc'), ms(ablation,'nmi'), ms(ablation,'ari')]], [1.5,1.55,1.55,1.6])
    doc.p(f"ACC tăng lên {ms(ablation,'acc')}%, với ARI giữa seed "
          f"{ms(ablation,'pairwise_ari',1,4)}. Kết quả hỗ trợ nhận định DCSS nhạy với độ rộng "
          "khởi tạo dưới backbone chung. Nó không chứng minh hiệu năng của DCSS nguyên gốc và "
          "không thay thế dòng σ = 1 trong bảng chính. Chi phí của phép bổ sung được ghi nhận "
          "nhưng không dùng để khẳng định tăng tốc vì chiến dịch đo và chi phí theo dõi có thể khác.")
    doc.heading("4.7. Đối chiếu số liệu công bố", 2)
    doc.p("Các bảng sau trình bày đối chiếu trong từng tài liệu nguồn, tách khỏi kết quả Digits. "
          "Ngay cả khi cùng tên MNIST, khác biệt kiến trúc, tiền huấn luyện, lựa chọn siêu tham "
          "số và nguồn baseline vẫn có thể thay đổi điểm. Không ghép các điểm tốt nhất của "
          "những tài liệu khác nhau thành một chuỗi tăng trưởng thực nghiệm đã được xác nhận.")
    table("4.8", "ACC của DEC và IDEC trong bài IDEC 2017", ["Benchmark", "DEC (%)", "IDEC (%)", "Δ (điểm %)"],
          [["MNIST", "86,55", "88,06", "1,51"], ["USPS", "74,08", "76,05", "1,97"],
           ["REUTERS-10K", "73,68", "75,64", "1,96"]], [1.6,1.5,1.5,1.6])
    doc.p("Nguồn: IDEC, Table 2 [2]. Bảng công bố thể hiện cải thiện của IDEC so với DEC trong "
          "giao thức của tài liệu này; bảng không cung cấp mean ± std để suy ra độ ổn định "
          "giữa các seed theo cách đo của thực nghiệm hiện tại.")
    published = load_json(docs / 'references/decra_reported_results.json', True)
    table("4.9", "Số liệu MNIST trong bài DECRA 2024", ["Phương pháp", "ACC (%)", "NMI (%)"],
          [[r['method'],number(r['acc'],1,100),number(r['nmi'],1,100)] for r in published['rows']], [2.0,2.1,2.1])
    doc.p("Nguồn: DECRA, Tables 2–3 [7]. DECRA đạt ACC 96,4% và NMI 91,7% trên MNIST trong "
          "bảng nguồn; không có cột std/SE và chưa xác định số lần chạy từ phần thiết lập đã "
          "đối chiếu. Baseline được lấy từ số liệu công bố hoặc chạy code, nên chưa xác lập mọi "
          "hàng dùng giao thức đồng nhất. NMI dùng chuẩn hóa maximum entropy, khác công thức "
          "trung bình số học ở (4.2). Các điểm này không được dùng để thay kết quả Digits.")
    brb = literature['brb_paper_reported']
    table("4.10", "ACC của IDEC có tiền huấn luyện khi bổ sung BRB", ["Benchmark", "IDEC (%)", "IDEC + BRB (%)", "Δ (điểm %)"],
          [[r['dataset'],f"{number(r['baseline_mean'])} ± {number(r['baseline_uncertainty'])}",
            f"{number(r['variant_mean'])} ± {number(r['variant_uncertainty'])}",
            number(float(r['variant_mean'])-float(r['baseline_mean']))] for r in brb], [1.45,1.65,1.75,1.35])
    doc.p("Nguồn: BRB, Table 13 [8]. Các hàng sử dụng reconstruction autoencoder có tiền huấn "
          "luyện, 10 seed; sai số là standard error theo quy ước của bài, không phải độ lệch "
          "chuẩn mẫu của bảng Digits. Mức tăng thay đổi theo benchmark, lớn nhất trong sáu "
          "hàng này là GTSRB. OPTDIGITS của bài sử dụng giao thức khác bản Digits 1.797 mẫu. "
          "Không thay baseline IDEC ở đây bằng điểm IDEC 2017 để tính mức tăng của BRB.")
    doc.p("DKM cung cấp một đối chiếu hữu ích về khởi tạo và tối ưu đồng thời. Trong preprint "
          "v2, Table 2 trên MNIST báo cáo DKMp ACC 84,0 ± 2,2% và IDECp 85,7 ± 2,4%, trên "
          "10 lượt chạy; tác giả chọn siêu tham số bằng nhãn 10% validation và đánh giá phần "
          "90% còn lại. Số liệu này chưa được đối chiếu với bảng journal cuối cùng và không "
          "tương đương giao thức không chọn tham số bằng nhãn của Digits. " + cite("DKM"))
    doc.p("DCSS báo cáo mean/std của 10 lượt trong các benchmark riêng và mô tả cải thiện NMI/ARI "
          "so với các đối chứng, nhưng không cung cấp cùng bảng ACC Digits đang dùng. LFSS, "
          "SANE, DCBoost và CDC bổ sung các mục tiêu hoặc điều kiện khác. Bằng chứng hiện tại "
          "hỗ trợ xem xét các ứng viên này, chưa cho phép chọn một phương pháp thắng phổ quát. " + cite("DCSS","LFSS","SANE","DCBoost","CDC"))
    doc.heading("4.8. Điểm mạnh, điểm yếu và giới hạn suy rộng", 2)
    table("4.11", "Đánh đổi quan sát được giữa các mốc phương pháp", ["Phương pháp", "Điểm mạnh", "Điểm yếu/giới hạn bằng chứng"], [
        ["DEC", "Chi phí thấp; NMI/ARI cao nhất lượt chính", "Tự làm sắc có thể củng cố gán sai; ACC biến động theo seed"],
        ["IDEC", "ACC và đồng thuận seed nhỉnh nhất; ràng buộc tái tạo", "Chênh DEC nhỏ, thắng 2/5 seed; cần cân bằng reconstruction"],
        ["DECRA", "Nhánh biến đổi linh hoạt; std ACC nhỏ hơn", "Chất lượng/đồng thuận thấp hơn; chưa thử nhiễu hay residual pretrain riêng"],
        ["DCSS", "Mục tiêu gọn/tách biệt; ablation phát hiện độ nhạy rõ", "RBF phụ thuộc scale; chuyển thể và khởi tạo ảnh hưởng mạnh"],
    ], [1.0,2.25,2.95])
    doc.p("Một dataset và năm seed chưa đủ kết luận khả năng tổng quát hóa hoặc thứ hạng toàn "
          "lĩnh vực. Việc dùng cùng backbone tạo điều kiện so sánh cơ chế nhưng có thể làm một "
          "phương pháp mất lợi thế kiến trúc vốn có. Ngân sách epoch chung không tương đương "
          "ngân sách thời gian hay tìm kiếm siêu tham số tối ưu cho từng phương pháp. Khả năng "
          "chịu nhiễu và thay đổi phân phối chưa được đo; ablation RBF là phân tích sau quan sát, "
          "cần xác nhận bằng thiết kế định trước trên dữ liệu khác.")

    doc.heading("CHƯƠNG V. THẢO LUẬN VÀ KẾT LUẬN")
    doc.heading("5.1. Trả lời các câu hỏi nghiên cứu", 2)
    doc.p("Về tiến trình phương pháp, các hướng phát triển không tạo một chuỗi tuyến tính đơn "
          "giản. Reconstruction, biến đổi embedding, prototype, nhất quán, lựa chọn mẫu và "
          "hình học cụm giải quyết các hạn chế khác nhau. DEC–IDEC–DECRA–DCSS là một trục phù "
          "hợp để kiểm tra cơ chế trong họ autoencoder, còn BRB/LFSS/SANE/DCBoost là những "
          "ứng viên cần đối chiếu theo điều kiện riêng.")
    doc.p("Về cải thiện dưới giao thức chung, IDEC chỉ nhỉnh hơn DEC về ACC trung bình và đồng "
          "thuận partition, trong khi DEC nhỉnh hơn ở NMI/ARI. DECRA chưa cải thiện chất lượng "
          "trong bản chuyển thể này. Độ lệch chuẩn thấp hơn của một metric không đủ chứng minh "
          "ổn định hơn khi chất lượng và mức đồng thuận phân hoạch đồng thời giảm.")
    doc.p("Về độ nhạy triển khai, phép đối chiếu RBF cho thấy một lựa chọn khởi tạo có thể làm "
          "thay đổi mạnh kết quả DCSS khi dùng embedding tuyến tính. Phân tích này giải thích "
          "vì sao cần khảo sát scale, loss và kiến trúc khi chuyển một phương pháp sang bộ "
          "thực nghiệm chung, thay vì xem mọi chênh lệch như bằng chứng về năng lực của bài gốc.")
    doc.p("Về lựa chọn tốt nhất năm 2025–2026, bằng chứng hiện tại chưa đủ. IDEC là lựa chọn có "
          "ACC trung bình cao nhất trong lượt Digits chính, nhưng kết luận đó không mở rộng "
          "thành vị trí dẫn đầu toàn lĩnh vực. BRB có cải thiện trong các đối chiếu của tác giả "
          "và vẫn là một ứng viên; nó có thể được thay bằng phương pháp khác khi khảo sát và "
          "thực nghiệm mở rộng cung cấp bằng chứng phù hợp hơn.")
    doc.heading("5.2. Kết quả đạt được và hạn chế", 2)
    doc.p(f"Báo cáo xây dựng danh mục {n} công trình có nguồn, cung cấp thống kê hội nghị/tạp chí, "
          "phân hạng có quy ước rõ, mã nguồn và benchmark; phân tích cơ chế bốn mốc tiêu biểu; "
          "và trình bày 20 lượt thực nghiệm chính cùng năm lượt đối chiếu độ rộng RBF. Các "
          "bảng công bố được giữ riêng theo tài liệu nguồn, giúp tránh nhầm tiến bộ trong paper "
          "với kết quả của bản chuyển thể trên cùng data.")
    doc.p("Khảo sát toàn văn chưa hoàn tất cho toàn bộ danh mục; phạm vi một số benchmark và "
          "số liệu còn thiếu trích xuất. Một tạp chí chưa xác minh đủ Q từ nguồn chính. Các "
          "môi trường mã tác giả chưa được chạy trong nghiên cứu này. Do đó, báo cáo là một "
          "khảo sát có thực nghiệm bước đầu, với giới hạn bằng chứng được công khai, chưa "
          "phải một tổng quan hệ thống hoàn chỉnh hay tái hiện đầy đủ các công trình.")
    doc.heading("5.3. Hướng phát triển", 2)
    doc.p("Giai đoạn tiếp theo cần hoàn tất phiếu đọc cho các phương pháp được phân tích sâu, "
          "trích xuất đúng bảng và giao thức gốc, đồng thời xác minh Q theo ngành/năm khi mục "
          "đích báo cáo yêu cầu. Về thực nghiệm, mở rộng thêm hai hoặc ba benchmark khác nhau "
          "về kiểu dữ liệu và độ khó, tăng seed và định trước ngân sách, quy tắc chọn siêu tham "
          "số cùng phép đo ổn định. Các thử nghiệm nhiễu và thay đổi khởi tạo giúp tách những "
          "khía cạnh ổn định chưa được đo trong báo cáo hiện tại.")
    doc.p("Để phân biệt ảnh hưởng của cơ chế với ảnh hưởng của kiến trúc, nên thực hiện cả so "
          "sánh trên backbone chung và tái hiện cấu hình nguyên gốc. Lựa chọn mô hình cuối cần "
          "dựa trên chất lượng, độ ổn định, chi phí và khả năng tái lập qua nhiều benchmark; "
          "không chỉ dựa vào năm công bố hoặc một điểm ACC thuận lợi.")

    doc.heading("TÀI LIỆU THAM KHẢO")
    for row in tracker:
        idx = refnum[row['method']]
        bib = bibliography[row['method']]
        authors = ', '.join(bib['authors'])
        venue = row['venue']
        if row['publication_type']=='journal' and bib.get('volume'):
            venue += ' '+bib['volume'] + ('('+bib['issue']+')' if bib.get('issue') else '')
        if bib.get('article_number'): venue += ', Article '+bib['article_number']
        if bib.get('first_page') and bib.get('last_page'):
            venue += ', tr. '+bib['first_page']+'–'+bib['last_page']
        extra = ''
        if row['method']=='DKM':
            extra=' Bản preprint 2018 và bản journal 2020 được tính một công trình. '+link('Preprint v2 và bảng số liệu','https://arxiv.org/pdf/1806.10069')+'.'
        if row['method']=='Survey-ACM': extra=' Online 2024; issue 57(3), Article 69, 2025.'
        doc.p(f"[{idx}] {authors}. {row['title']}. {venue}, {row['year']}. " +
              link('Nguồn công bố', row['paper_url']) + '.' + extra)
    doc.p("[33] Scikit-learn. Load digits: bộ dữ liệu ảnh chữ số 8×8. " + link('Tài liệu dữ liệu',metadata['sklearn_url']) + '.')
    doc.p("[34] E. Alpaydin và C. Kaynak. Optical Recognition of Handwritten Digits. UCI Machine Learning Repository. " +
          link('Nguồn dữ liệu',metadata['uci_url']) + '; DOI: 10.24432/C50P49.')
    doc.p("[35] SCImago Journal & Country Rank. SJR, năm tham chiếu 2024. " +
          '; '.join(link(r['venue'],r['source_url']) for r in ranking['records']) + '. Phân hạng ngành của PRLetters được đối chiếu riêng.')

    doc.heading("PHỤ LỤC A. DANH MỤC CÔNG TRÌNH VÀ KHẢ NĂNG TRUY CẬP")
    doc.p("Phụ lục liên hệ từng phương pháp với nơi công bố, mã công khai và benchmark đã "
          "ghi nhận. Tên benchmark có thể lấy từ bài, mục dữ liệu hoặc README; nó không chứng "
          "minh toàn bộ dữ liệu đã tải hoặc mọi phép đánh giá đã chạy. Q là năm tham chiếu "
          "2024 đã nêu ở mục 2.3; dấu — áp dụng cho hội nghị, không phải Q thấp.")
    table("A.1", "Công trình, nơi công bố và mã nguồn", ["Phương pháp / năm", "Nơi công bố", "Loại / Q", "Mã hoặc tài nguyên"],
          [[f"{r['method']} ({r['year']}) [{refnum[r['method']]}]", abbreviations.get(r['venue'],r['venue']),
            ("Tạp chí / "+verified_quartile(r).replace('unknown','chưa xác minh')) if r['publication_type']=='journal' else 'Hội nghị / —',
            link('Công khai',r['code_url']) if yes(r['code_public']) else 'Chưa xác minh'] for r in tracker], [1.5,2.1,1.25,1.35])
    table("A.2", "Benchmark và mức đối chiếu phạm vi", ["Phương pháp", "Benchmark trong hồ sơ", "Phạm vi đối chiếu"],
          [[f"{r['method']} [{refnum[r['method']]}]", r['datasets'] or 'Chưa trích xuất đầy đủ',
            'Đã đối chiếu tên/phạm vi' if yes(r['dataset_scope_verified']) else 'Chưa xác minh đầy đủ'] for r in tracker], [1.15,3.8,1.25])
    doc.p("Mã công khai ở đây bao gồm nguồn tác giả và các tài nguyên đã được đối chiếu trong "
          "hồ sơ; availability không đồng nghĩa thực thi thành công. Bài tổng quan ACM cung "
          "cấp thư viện và danh mục tài nguyên, không được đếm thành một thuật toán đã chạy.")
    numeric = [
        ["DEC [1]", "MNIST / ACC", "84,30%", "Tốt nhất trong 9 thiết lập, không phải trung bình seed"],
        ["IDEC [2]", "MNIST / ACC", "DEC 86,55 → IDEC 88,06%", "Table 2; giao thức của bài IDEC"],
        ["DCN [3]", "MNIST / ACC", "Raw 83%; tiền xử lý 95%", "Hai biểu diễn khác nhau, không gộp thành một kết quả"],
        ["DEC-DA [4]", "MNIST / ACC, NMI", "98,5%; 96,0%", "README; cách tổng hợp cần đối chiếu bài gốc"],
        ["CC [6]", "CIFAR-10/100 / NMI", "0,705 / 0,431", "Abstract nhà xuất bản"],
        ["DECRA [7]", "MNIST / ACC, NMI", "96,4%; 91,7%", "Tables 2–3; không hiển thị std/SE"],
        ["BRB [8]", "MNIST / ACC", "93,16 ± 2,20 → 94,19 ± 2,20%", "IDEC có pretrain; 10 seed; mean ± SE"],
        ["VaDE [9]", "MNIST / ACC", "94,46%", "README/checkpoint của tác giả"],
        ["DPAC [15]", "CIFAR-10 / ACC", "93,4%", "README tác giả; chưa chạy lại"],
        ["NNM [18]", "CIFAR-10 / ACC", "84,30%", "Model zoo của tác giả"],
        ["DCSS [21]", "NMI / ARI", "Tăng 0,03–0,07 / 0,03–0,06", "Mô tả §5.5 so với đối chứng thứ hai; benchmark riêng"],
        ["DCBoost [23]", "CIFAR-10 / ACC", "ProPos 94,4 → 96,0%", "Phần giới thiệu; sử dụng mô hình tiền huấn luyện"],
        ["SANE [24]", "Accuracy / hiệu quả huấn luyện", "Cải thiện đến 6,1%; đến 1,3×", "Giá trị tối đa mô tả trong abstract, không phải Digits"],
        ["CDC [25]", "ECE", "Giảm khoảng 5 lần trung bình", "Calibration error; không phải tăng ACC 5 lần"],
        ["CPP [27]", "ImageNet-1k / ACC", "57 → 66%", "Sử dụng đặc trưng pretrained, có thông tin ngoài"],
        ["SwAV [28]", "ImageNet / linear top-1", "75,3%", "Đánh giá biểu diễn; không phải clustering ACC"],
        ["DSCNet [30]", "COIL20 / error", "5,14%", "DSCNet-L2; error thấp hơn tốt hơn"],
        ["DKM [31]", "MNIST / ACC", "84,0 ± 2,2%", "Preprint v2; 10 lượt; validation có nhãn 10%"],
    ]
    assert len(numeric) == counts['paper_reported_numeric_summaries']
    table("A.3", "Các tóm tắt số liệu định lượng trong hồ sơ khảo sát", ["Công trình", "Benchmark / độ đo", "Số liệu nguồn", "Giao thức / mức chứng cứ"], numeric,
          [1.0,1.4,1.8,2.0])
    doc.p("Nguồn của mỗi hàng được liên hệ với công trình tương ứng trong tài liệu tham khảo "
          "và hồ sơ số liệu. Các hàng lấy từ abstract, README hoặc model zoo có mức chi tiết "
          "thấp hơn một bảng thực nghiệm đầy đủ. Không xếp hạng chéo các hàng do khác dữ liệu, "
          "độ đo và giao thức. Mười ba công trình còn thiếu trích xuất số liệu là SCAN, "
          "DeepCluster, JULE, DCEC, IIC, DECCS, CA, ProPos, DivClust, LFSS, PRCut, P2OT và IDC. "
          "Bài tổng quan ACM cung cấp taxonomy và tài nguyên, không có điểm của một mô hình "
          "cạnh tranh mới trong bảng này.")
    doc.heading("PHỤ LỤC B. MINH HỌA CƠ CHẾ VÀ SỐ LIỆU THEO SEED")
    doc.p("Đoạn Python dưới đây minh họa cách tạo phân phối mục tiêu của DEC/IDEC với ma trận "
          "xác suất Q có dạng N×K. Cơ chế bình phương xác suất ưu tiên các gán tự tin, còn f "
          "điều chỉnh theo tần suất cụm. P được tính ngoài bước lấy gradient và giữ cố định "
          "trong các cập nhật theo lịch. Đây là minh họa cơ chế, không phải mã huấn luyện đầy đủ.")
    doc.code("def target_distribution(q):\n"
             "    frequency = q.sum(axis=0)\n"
             "    weight = q ** 2 / frequency\n"
             "    return weight / weight.sum(axis=1, keepdims=True)", language='python')
    doc.p("Trong DEC, gradient cập nhật encoder và tâm theo KL; IDEC cộng gradient tái tạo. "
          "DECRA còn cập nhật nhánh affine và consistency hai đường decode. DCSS thay mục "
          "tiêu P bằng xác suất RBF, soft silhouette và entropy. Các cơ chế này giải thích "
          "khác biệt được khảo sát ở Chương III; kết quả đầy đủ theo seed được tổng hợp dưới đây.")
    table("B.1", "Kết quả của toàn bộ 20 lượt chính", ["Phương pháp", "Seed", "ACC (%)", "NMI (%)", "ARI (%)"],
          [[r['method'], r['seed'], number(r['acc'],2,100),number(r['nmi'],2,100),number(r['ari'],2,100)] for r in runs], [1.4,.6,1.4,1.4,1.4])

    # Front matter uses actual headings/captions; page numbers are computed by Word.
    headings = [b for b in doc.blocks if b['kind']=='heading']
    tables = [b['text'] for b in doc.blocks if b['kind']=='caption']
    figures = [b['caption'] for b in doc.blocks if b['kind']=='image']
    front = Report()
    front.contents('MỤC LỤC', [b['text'] for b in headings if b.get('level',1)<=2])
    front.heading('DANH MỤC TỪ VIẾT TẮT')
    front.table(['Viết tắt','Thuật ngữ','Ý nghĩa'], [
        ['AE','Autoencoder','Mạng tự mã hóa'], ['ACC','Clustering Accuracy','Độ chính xác phân cụm sau ghép nhãn'],
        ['NMI','Normalized Mutual Information','Thông tin tương hỗ chuẩn hóa'],
        ['ARI','Adjusted Rand Index','Chỉ số Rand hiệu chỉnh'], ['KL','Kullback–Leibler divergence','Độ phân kỳ giữa phân phối'],
        ['RBF','Radial Basis Function','Hàm cơ sở xuyên tâm'], ['MSE','Mean Squared Error','Lỗi bình phương trung bình'],
        ['SJR','SCImago Journal Rank','Hệ thống chỉ số và phân hạng tạp chí'],
        ['SD','Sample standard deviation','Độ lệch chuẩn mẫu'], ['SE','Standard error','Sai số chuẩn'],
        ['RMS','Root Mean Square','Căn trung bình bình phương'],
    ], [.7,2.45,3.05])
    front.contents('DANH MỤC BẢNG',tables)
    front.contents('DANH MỤC HÌNH',figures)
    doc.blocks[2:2] = front.blocks
    return doc


LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def inline_html(text: str) -> str:
    parts = []
    pos = 0
    for match in LINK_RE.finditer(text):
        parts.append(html.escape(text[pos:match.start()]))
        parts.append(f'<a href="{html.escape(match[2], quote=True)}">{html.escape(match[1])}</a>')
        pos = match.end()
    parts.append(html.escape(text[pos:]))
    return "".join(parts).replace("\n", "<br>")


def export_markdown(report: Report, target: Path):
    lines = []
    anchors = {b.get('text', b.get('caption', '')): f's{i}' for i,b in enumerate(report.blocks)
               if b['kind'] in {'heading','caption','image'}}
    for i,b in enumerate(report.blocks):
        kind = b["kind"]
        if kind in {'heading','caption','image'}:
            lines.append(f'<a id="s{i}"></a>\n')
        if kind == "title":
            lines.append("# " + b["text"].replace("\n", " — "))
        elif kind == 'subtitle':
            lines.append(b['text'].replace('\n',' — '))
        elif kind == 'contents':
            lines.append('## '+b['title']+'\n')
            lines.extend(f"- [{entry}](#{anchors[entry]})" for entry in b['entries'])
        elif kind == "heading":
            lines.append("#" * (b["level"] + 1) + " " + b["text"])
        elif kind == "p":
            lines.append(b["text"])
        elif kind == 'caption':
            lines.append('**'+b['text']+'**')
        elif kind == 'equation':
            lines.append(b['text']+' '+b.get('number',''))
        elif kind == "table":
            sanitize = lambda row: "| " + " | ".join(str(v).replace("|", "\\|").replace("\n", "<br>") for v in row) + " |"
            lines.extend([sanitize(b["headers"]), sanitize(["---"] * len(b["headers"])), *[sanitize(row) for row in b["rows"]]])
        elif kind == "image":
            path = os.path.relpath(b["path"], target.parent).replace("\\", "/")
            lines.append(f"![{b['caption']}]({path})\n\n{b['caption']}")
        elif kind == "code":
            lines.append("```" + b.get("language", "text") + "\n" + b["text"] + "\n```")
        elif kind == "details":
            lines.append(f"<details><summary>{b['title']}</summary>\n\n```text\n{b['text']}\n```\n\n</details>")
        lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")


def export_html(report: Report, target: Path):
    body, nav = [], []
    anchors = {b.get('text', b.get('caption', '')): f's{i}' for i,b in enumerate(report.blocks)
               if b['kind'] in {'heading','caption','image'}}
    for i, b in enumerate(report.blocks):
        kind = b["kind"]
        if kind == "title":
            body.append(f"<h1>{inline_html(b['text'])}</h1>")
        elif kind == 'subtitle':
            body.append(f"<p class='subtitle'>{inline_html(b['text'])}</p>")
        elif kind == 'contents':
            entries=''.join(f'<li><a href="#{anchors[t]}">{html.escape(t)}</a></li>' for t in b['entries'])
            body.append(f"<section class='contents'><h2>{html.escape(b['title'])}</h2><ul>{entries}</ul></section>")
        elif kind == "heading":
            level = b["level"] + 1
            body.append(f'<h{level} id="s{i}">{inline_html(b["text"])}</h{level}>')
            if b["level"] == 1:
                nav.append(f'<a href="#s{i}">{html.escape(b["text"])}</a>')
        elif kind == "p":
            body.append(f"<p>{inline_html(b['text'])}</p>")
        elif kind == 'caption':
            body.append(f'<p class="caption" id="s{i}">{inline_html(b["text"])}</p>')
        elif kind == 'equation':
            body.append(f'<p class="equation"><span>{html.escape(b["text"])}</span><span style="float:right">{html.escape(b.get("number",""))}</span></p>')
        elif kind == "table":
            cells = lambda row, tag: "<tr>" + "".join(f"<{tag}>{inline_html(v)}</{tag}>" for v in row) + "</tr>"
            body.append('<div class="table-wrap"><table><thead>' + cells(b["headers"], "th") + '</thead><tbody>' +
                        "".join(cells(row, "td") for row in b["rows"]) + "</tbody></table></div>")
        elif kind == "image":
            data = base64.b64encode(b["path"].read_bytes()).decode("ascii")
            body.append(f'<figure id="s{i}">' +
                        f'<img src="data:image/png;base64,{data}" alt="{html.escape(b["caption"], quote=True)}">' +
                        f'<figcaption>{html.escape(b["caption"])}</figcaption></figure>')
        elif kind == "code":
            body.append(f"<pre><code class=\"language-{html.escape(b.get('language', 'text'), quote=True)}\">{html.escape(b['text'])}</code></pre>")
        elif kind == "details":
            body.append(f"<details><summary>{html.escape(b['title'])}</summary><pre>{html.escape(b['text'])}</pre></details>")
    style = """*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#ededed;color:#111;font:18px/1.65 'Times New Roman',Times,serif}main{max-width:1080px;margin:auto;padding:52px 55px 80px;background:white}h1{text-align:center;font-size:30px;line-height:1.45;margin:50px 0 25px}h2{text-align:center;padding-top:32px;border-top:1px solid #ccc;font-size:24px;line-height:1.5}h3{font-size:21px;margin-top:26px}h4{font-size:19px}p{text-align:justify;margin:12px 0}a{color:#164e80;text-decoration:none}a:hover{text-decoration:underline}.subtitle{text-align:center;margin-bottom:55px}.contents ul{list-style:none;padding:0}.contents li{margin:5px 0}.contents a{color:#222}.caption{font-weight:bold;text-align:center;margin-top:25px;margin-bottom:8px}.equation{text-align:center;font-style:italic;white-space:pre-wrap}table{width:100%;border-collapse:collapse;font-size:16px;margin:8px 0 20px}th{background:#e8e8e8;text-align:center}td,th{border:1px solid #555;padding:8px;vertical-align:top}.table-wrap{overflow:auto}td{overflow-wrap:anywhere}figure{margin:24px 0}img{display:block;width:100%;height:auto}figcaption{text-align:center;font-style:italic;font-size:16px;margin:8px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;border:1px solid #bbb;background:#f7f7f7;padding:14px;font:16px/1.5 'Times New Roman',Times,serif}nav{display:none}@media(max-width:650px){main{padding:24px 16px}h1{font-size:24px}table{font-size:14px}}@media print{@page{size:A4;margin:2.54cm}body{background:white;font-size:13pt}main{padding:0}h2{break-before:page;border:0}h3{break-after:avoid}table{font-size:13pt}thead{display:table-header-group}tr{break-inside:avoid}.caption{break-after:avoid}figure{break-inside:avoid}.contents{break-before:page}pre{font-size:13pt}}"""
    target.write_text('<!DOCTYPE html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">' +
                      f'<title>Đánh giá hiệu năng và độ ổn định của các phương pháp phân cụm sâu</title><style>{style}</style><main>' +
                      '<nav>' + "".join(nav) + '</nav>' + "\n".join(body) + '</main></html>', encoding="utf-8")


def export_docx(report: Report, target: Path):
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
        from docx.enum.section import WD_SECTION_START
        from docx.enum.style import WD_STYLE_TYPE
        from docx.image.image import Image
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Inches, Cm, Pt, RGBColor
    except ImportError as exc:
        raise RuntimeError("Cài python-docx để xuất Word: .\\.venv\\Scripts\\python.exe -m pip install python-docx") from exc
    document = Document()
    word_font = "Times New Roman"
    word_size = 13

    def set_font_attributes(element):
        fonts = element.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            element.insert(0, fonts)
        for attribute in ["ascii", "hAnsi", "eastAsia", "cs"]:
            fonts.set(qn("w:" + attribute), word_font)
        for attribute in ["asciiTheme", "hAnsiTheme", "eastAsiaTheme", "csTheme"]:
            fonts.attrib.pop(qn("w:" + attribute), None)
        for tag in ["sz", "szCs"]:
            size = element.find(qn("w:" + tag))
            if size is None:
                size = OxmlElement("w:" + tag)
                element.append(size)
            size.set(qn("w:val"), str(word_size * 2))

    # Set the actual document defaults as well as styles so Word does not fall
    # back to Calibri/theme fonts for hyperlinks, fields or newly typed text.
    defaults = document.styles.element.find(qn("w:docDefaults"))
    if defaults is None:
        defaults = OxmlElement("w:docDefaults")
        document.styles.element.insert(0, defaults)
    default_run = defaults.find(qn("w:rPrDefault"))
    if default_run is None:
        default_run = OxmlElement("w:rPrDefault")
        defaults.append(default_run)
    default_properties = default_run.find(qn("w:rPr"))
    if default_properties is None:
        default_properties = OxmlElement("w:rPr")
        default_run.append(default_properties)
    set_font_attributes(default_properties)
    for style in document.styles:
        if hasattr(style, "font"):
            style.font.name, style.font.size = word_font, Pt(word_size)
            set_font_attributes(style.element.get_or_add_rPr())
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.27), Inches(11.69)
    section.top_margin = section.bottom_margin = Cm(2.54)
    section.left_margin = section.right_margin = Cm(2.54)
    section.header_distance = section.footer_distance = Cm(1.25)
    usable = (section.page_width-section.left_margin-section.right_margin)/914400
    normal = document.styles["Normal"]
    normal.font.name, normal.font.size = word_font, Pt(word_size)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.first_line_indent = Cm(.75)
    for name in ["Title", "Heading 1", "Heading 2", "Heading 3"]:
        style = document.styles[name]
        style.font.name = word_font
        style.font.color.rgb = RGBColor(0,0,0)
        style.font.bold = True
        style.font.size = Pt({"Title": 18, "Heading 1": 16, "Heading 2": 14, "Heading 3": 13}[name])
        style.element.get_or_add_rPr().find(qn("w:szCs")).set(
            qn("w:val"), str({"Title": 18, "Heading 1": 16, "Heading 2": 14, "Heading 3": 13}[name] * 2))
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.first_line_indent = Cm(0)
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER if name in {'Title','Heading 1'} else WD_ALIGN_PARAGRAPH.LEFT
        style.paragraph_format.space_before = Pt(18)
        style.paragraph_format.space_after = Pt(9)
        if name == 'Heading 1': style.paragraph_format.page_break_before = True
    for name in ['Caption Table','Caption Figure','Equation','TOC 1','TOC 2','Front Heading']:
        style = document.styles[name] if name in document.styles else document.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = normal
        style.font.name,style.font.size=word_font,Pt(word_size)
        set_font_attributes(style.element.get_or_add_rPr())
        style.paragraph_format.first_line_indent=Cm(0)
        style.paragraph_format.line_spacing=1.15
        style.paragraph_format.space_after=Pt(6)
        style.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER if name.startswith('Caption') or name in {'Equation','Front Heading'} else WD_ALIGN_PARAGRAPH.LEFT
        style.font.bold=name=='Caption Table'
        style.font.italic=name in {'Caption Figure','Equation'}
    front_heading=document.styles['Front Heading']
    front_heading.font.size=Pt(16);front_heading.font.bold=True
    front_heading.element.get_or_add_rPr().find(qn('w:szCs')).set(qn('w:val'),'32')
    front_heading.paragraph_format.page_break_before=True
    front_heading.paragraph_format.keep_with_next=True
    outline=OxmlElement('w:outlineLvl');outline.set(qn('w:val'),'9')
    front_heading.element.get_or_add_pPr().append(outline)
    document.styles['Caption Table'].paragraph_format.keep_with_next=True
    document.styles['TOC 2'].paragraph_format.left_indent=Cm(.6)
    settings = document.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)
    document.core_properties.title = "Đánh giá hiệu năng và độ ổn định của các phương pháp phân cụm sâu"
    document.core_properties.subject = "Khảo sát tài liệu 2016–2026 và thực nghiệm so sánh trên Digits"
    document.core_properties.language = "vi-VN"

    def add_inline(paragraph, value: str):
        pos = 0
        for match in LINK_RE.finditer(value):
            paragraph.add_run(value[pos:match.start()])
            relationship = paragraph.part.relate_to(match[2], "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
            hyperlink = OxmlElement("w:hyperlink")
            hyperlink.set(qn("r:id"), relationship)
            run, props = OxmlElement("w:r"), OxmlElement("w:rPr")
            set_font_attributes(props)
            color, underline = OxmlElement("w:color"), OxmlElement("w:u")
            color.set(qn("w:val"), "0866A2")
            underline.set(qn("w:val"), "single")
            props.extend([color, underline])
            run.append(props)
            text = OxmlElement("w:t")
            text.text = match[1]
            run.append(text)
            hyperlink.append(run)
            paragraph._p.append(hyperlink)
            pos = match.end()
        paragraph.add_run(value[pos:])

    anchors={b.get('text',b.get('caption','')):f's{i}' for i,b in enumerate(report.blocks)
             if b['kind'] in {'heading','caption','image'}}

    def bookmark(paragraph, name):
        start,end=OxmlElement('w:bookmarkStart'),OxmlElement('w:bookmarkEnd')
        identifier=name.removeprefix('s')
        start.set(qn('w:id'),identifier);start.set(qn('w:name'),name)
        end.set(qn('w:id'),identifier)
        paragraph._p.insert(1 if paragraph._p.find(qn('w:pPr')) is not None else 0,start)
        paragraph._p.append(end)

    def field_run(paragraph, field_type=None, instruction=None):
        run=paragraph.add_run();props=run._r.get_or_add_rPr();set_font_attributes(props)
        if field_type:
            element=OxmlElement('w:fldChar');element.set(qn('w:fldCharType'),field_type)
        else:
            element=OxmlElement('w:instrText');element.set(qn('xml:space'),'preserve');element.text=instruction
        run._r.append(element)

    def contents(block):
        document.add_paragraph(block['title'],style='Front Heading')
        instruction = (' TOC \\o "1-3" \\h \\z \\u ' if block['title']=='MỤC LỤC' else
                       ' TOC \\h \\z \\t "Caption Table,1" ' if block['title']=='DANH MỤC BẢNG' else
                       ' TOC \\h \\z \\t "Caption Figure,1" ')
        paragraph=document.add_paragraph()
        paragraph.paragraph_format.space_after=Pt(0)
        field_run(paragraph,'begin');field_run(paragraph,instruction=instruction);field_run(paragraph,'separate')
        for entry in block['entries']:
            paragraph=document.add_paragraph(style='TOC 2' if re.match(r'^\d+\.\d+',entry) else 'TOC 1')
            hyperlink=OxmlElement('w:hyperlink');hyperlink.set(qn('w:anchor'),anchors[entry])
            run,props=OxmlElement('w:r'),OxmlElement('w:rPr');set_font_attributes(props);run.append(props)
            text=OxmlElement('w:t');text.text=entry;run.append(text);hyperlink.append(run);paragraph._p.append(hyperlink)
        field_run(paragraph,'end')

    content_started=False

    for i,b in enumerate(report.blocks):
        kind = b["kind"]
        if kind == "title":
            paragraph=document.add_paragraph(b["text"], style="Title")
            paragraph.paragraph_format.space_before=Pt(110)
        elif kind == 'subtitle':
            paragraph=document.add_paragraph(b['text'])
            paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent=Cm(0)
            paragraph.paragraph_format.space_before=Pt(40)
            paragraph.paragraph_format.space_after=Pt(70)
        elif kind == 'contents':
            contents(b)
        elif kind == "heading":
            if b['text'].startswith('CHƯƠNG I.') and not content_started:
                section=document.add_section(WD_SECTION_START.NEW_PAGE)
                section.footer.is_linked_to_previous=False
                footer=section.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
                footer.paragraph_format.first_line_indent=Cm(0)
                footer.add_run('Trang ')
                field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE')
                run,props=OxmlElement('w:r'),OxmlElement('w:rPr');set_font_attributes(props);run.append(props)
                text=OxmlElement('w:t');text.text='1';run.append(text);field.append(run);footer._p.append(field)
                numbering=OxmlElement('w:pgNumType');numbering.set(qn('w:start'),'1');section._sectPr.append(numbering)
                content_started=True
            paragraph=(document.add_paragraph(b['text'],style='Front Heading') if b['text']=='DANH MỤC TỪ VIẾT TẮT' else
                       document.add_heading(b["text"], level=b["level"]))
            if b['text'].startswith('CHƯƠNG I.'):
                paragraph.paragraph_format.page_break_before=False
            bookmark(paragraph,f's{i}')
        elif kind == "p":
            paragraph=document.add_paragraph();add_inline(paragraph,b['text'])
            if re.match(r'^\[\d+\]',b['text']):
                paragraph.paragraph_format.first_line_indent=Cm(-.75)
                paragraph.paragraph_format.left_indent=Cm(.75)
        elif kind == 'caption':
            paragraph=document.add_paragraph(b['text'],style='Caption Table');bookmark(paragraph,f's{i}')
        elif kind == 'equation':
            paragraph=document.add_paragraph(style='Equation')
            paragraph.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.tab_stops.add_tab_stop(Inches(usable/2),WD_TAB_ALIGNMENT.CENTER)
            paragraph.paragraph_format.tab_stops.add_tab_stop(Inches(usable),WD_TAB_ALIGNMENT.RIGHT)
            paragraph.add_run('\t'+b['text']+'\t'+b.get('number',''))
        elif kind == "table":
            table = document.add_table(rows=1, cols=len(b["headers"]))
            table.style, table.autofit = "Table Grid", False
            widths = b["widths"] or [usable / len(b["headers"])] * len(b["headers"])
            widths = [w * usable / sum(widths) for w in widths]
            for col, width in zip(table.columns, widths):
                col.width = Inches(width)
            for index, text in enumerate(b["headers"]):
                cell = table.rows[0].cells[index]
                cell.width = Inches(widths[index])
                paragraph = cell.paragraphs[0]
                run = paragraph.add_run(text)
                run.bold, run.font.color.rgb = True, RGBColor(0,0,0)
                shade = OxmlElement("w:shd")
                shade.set(qn("w:fill"), "E7E6E6")
                cell._tc.get_or_add_tcPr().append(shade)
            repeat = OxmlElement("w:tblHeader")
            table.rows[0]._tr.get_or_add_trPr().append(repeat)
            for values in b["rows"]:
                row = table.add_row()
                cannot_split = OxmlElement("w:cantSplit")
                row._tr.get_or_add_trPr().append(cannot_split)
                for index, text in enumerate(values):
                    cell = row.cells[index]
                    cell.width = Inches(widths[index])
                    add_inline(cell.paragraphs[0], text)
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        paragraph.paragraph_format.space_after = Pt(3)
                        paragraph.paragraph_format.line_spacing = 1.05
                        paragraph.paragraph_format.first_line_indent=Cm(0)
                        paragraph.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
                        for run in paragraph.runs:
                            run.font.name, run.font.size = word_font, Pt(word_size)
            document.add_paragraph().paragraph_format.space_after = Pt(2)
        elif kind == "image":
            picture = Image.from_file(str(b["path"]))
            aspect = picture.px_width / picture.px_height
            width = min(usable, 6.0 * aspect)
            paragraph=document.add_paragraph();paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent=Cm(0)
            paragraph.paragraph_format.keep_with_next=True
            paragraph.add_run().add_picture(str(b['path']),width=Inches(width))
            paragraph = document.add_paragraph(b["caption"],style='Caption Figure')
            paragraph.paragraph_format.keep_with_next = False
            paragraph.runs[0].font.name, paragraph.runs[0].font.size = word_font, Pt(word_size)
            paragraph.runs[0].italic = True
            bookmark(paragraph,f's{i}')
        elif kind == "code":
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_before = Pt(4)
            paragraph.paragraph_format.space_after = Pt(10)
            paragraph.paragraph_format.first_line_indent=Cm(0)
            paragraph.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.line_spacing=1.15
            for i, line in enumerate(b["text"].splitlines()):
                run = paragraph.add_run(("\n" if i else "") + line)
                run.font.name, run.font.size = word_font, Pt(word_size)
        elif kind == "details":
            # Full machine-readable artifacts are available in HTML/Markdown.
            # Avoid duplicating long log/JSON tables in the Word report.
            continue
    # Conditional table styles also contain theme fonts. Pin every rFonts node,
    # including nested style properties, so non-Latin runs inherit the same font.
    for element in [document.styles.element, document.element, *[s.header._element for s in document.sections],
                    *[s.footer._element for s in document.sections]]:
        for fonts in element.iter(qn('w:rFonts')):
            for attribute in list(fonts.attrib):
                if 'theme' in attribute.lower(): del fonts.attrib[attribute]
            for attribute in ['ascii','hAnsi','eastAsia','cs']:
                fonts.set(qn('w:'+attribute),word_font)
    document.save(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=ROOT / "results/timeline_20261013")
    parser.add_argument("--docs", type=Path, default=ROOT / "docs")
    parser.add_argument("--name", default=None, help="Basename for DOCX/Markdown/HTML; choose a new name to preserve archived reports")
    parser.add_argument("--original-word", type=Path, default=ROOT / "docs/original/Bao_cao_Survey_Deep_Clustering_va_Demo_5_Phuong_phap.docx")
    args = parser.parse_args()
    if args.name is None:
        args.name = "Bao_cao_" + args.results.name.removeprefix("results_") if "timeline" in args.results.name else NAME
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.name):
        parser.error("--name must contain letters, digits, underscores or hyphens only.")
    out, docs = args.results.resolve(), args.docs.resolve()
    docs.mkdir(parents=True, exist_ok=True)
    report = make_report(out, docs, args.original_word.resolve(), args.name)
    export_docx(report, docs / (args.name + ".docx"))
    export_markdown(report, docs / (args.name + ".md"))
    export_html(report, docs / (args.name + ".html"))
    for suffix in ["docx", "md", "html"]:
        path = docs / (args.name + "." + suffix)
        print(f"Created {path} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
