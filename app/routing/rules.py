import re
import unicodedata


DEEP_ROLE_TRIGGERS = {"tool", "function", "observation"}
CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")

DEEP_KEYWORDS = (
    "traceback",
    "stack trace",
    "debug",
    "bug",
    "fix bug",
    "refactor",
    "implement",
    "implementation",
    "unit test",
    "test case",
    "endpoint",
    "api route",
    "step by step",
    "plan",
    "planning",
    "design",
    "architecture",
    "trade-off",
    "trade off",
    "compare approaches",
    "root cause",
    "investigate",
    "analyze",
    "analysis",
    "research",
    "report",
    "findings",
    "benchmark",
    "coding",
    "lap trinh",
    "viet code",
    "viet ma",
    "trien khai",
    "cai dat",
    "go loi",
    "sua loi",
    "loi",
    "ngoai le",
    "log loi",
    "kiem thu",
    "ca kiem thu",
    "tung buoc",
    "ke hoach",
    "lap ke hoach",
    "thiet ke",
    "kien truc",
    "danh doi",
    "so sanh phuong an",
    "nguyen nhan goc",
    "dieu tra",
    "phan tich",
    "nghien cuu",
    "tim hieu",
    "khao sat",
    "bao cao",
    "tong hop",
    "so sanh",
    "danh gia",
    "buoc 1",
    "buoc 2",
    "xem xet roi trien khai",
    "so sanh roi de xuat",
)

MULTISTEP_PATTERNS = (
    "first ",
    "then ",
    "step 1",
    "step 2",
    "review then implement",
    "compare and recommend",
    "truoc tien",
    "sau do",
    "xem xet roi trien khai",
    "so sanh roi de xuat",
)


def normalize_text(value: str) -> str:
    lowered = value.lower()
    normalized = unicodedata.normalize("NFD", lowered)
    without_diacritics = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    collapsed = re.sub(r"\s+", " ", without_diacritics)
    return collapsed.strip()
