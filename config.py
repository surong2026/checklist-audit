import os
import sys

APP_NAME = "清单核对系统"
APP_VERSION = "1.0.0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.join(os.path.expanduser("~"), "清单核对系统", "tasks")
AUTOSAVE_DIR = os.path.join(os.path.expanduser("~"), "清单核对系统", "autosave")

os.makedirs(TASK_DIR, exist_ok=True)
os.makedirs(AUTOSAVE_DIR, exist_ok=True)

SUPPORTED_EXTENSIONS = (".xls", ".xlsx", ".pdf", ".docx", ".et")
MAX_FILES = 10
MIN_FILES = 2

STANDARD_FIELDS = {
    "name": {"cn": "品名", "aliases": ["采购品名", "名称", "货物名称", "商品名", "产品名称", "名  称", "名 称"]},
    "brand": {"cn": "品牌", "aliases": ["商标", "厂家", "生产厂家", "制造商", "品牌/厂家"]},
    "spec": {"cn": "规格型号", "aliases": ["型号及简要参数", "规格", "型号", "货物型号规格", "参数", "货物型号规格、标准及配置等", "型号及简要参数", "货物型号规格、标准及配置等\n（或服务内容、标准）"]},
    "quantity": {"cn": "数量", "aliases": ["计量数量", "入库数量", "件数", "数  量", "数 量"]},
    "unit_price": {"cn": "单价", "aliases": ["单价(元)", "含税单价", "未税单价", "单价（元）", "单  价"]},
    "total_price": {"cn": "总价", "aliases": ["金额", "总金额", "合计金额", "金  额", "金 额", "总  价", "总 价"]},
}

SUMMARY_KEYWORDS = [
    "合计", "总计", "优惠", "小计", "大写金额", "备注：以上",
    "合  计", "合 计",
    # 验收书/审批表单中的非数据行
    "验收具体内容", "验收小组意见", "签字", "盖章",
    "监督人员", "单位负责人", "中标或者成交供应商",
    "验收方式", "验收情况",
]

NON_NUMERIC_PATTERNS = ["见照片", "见附件", "无", "-", "/", "—"]

FUZZY_MATCH_THRESHOLD_AUTO = 90
FUZZY_MATCH_THRESHOLD_MANUAL = 60

WPS_SEARCH_PATHS = [
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Kingsoft"),
    os.path.join(os.environ.get("APPDATA", ""), "Kingsoft"),
    r"C:\Program Files\Kingsoft",
    r"C:\Program Files (x86)\Kingsoft",
]

COLOR_RED = "FFD7D7"
COLOR_YELLOW = "FFFFCC"
COLOR_GREEN = "D7FFD7"
COLOR_GRAY = "E0E0E0"
COLOR_BLUE = "CCE5FF"
COLOR_WHITE = "FFFFFF"
