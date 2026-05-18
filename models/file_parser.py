import os
from models.docx_parser import parse_docx
from models.excel_parser import parse_xlsx, parse_xls
from models.pdf_parser import parse_pdf
from models.et_parser import parse_et


def parse_file(file_path: str) -> dict:
    """Dispatch to the appropriate parser based on file extension.

    Returns:
        {
            "file_name": str,
            "file_path": str,
            "extension": str,
            "primary_table": list[list[str]] or None,
            "error": str or None,
            "meta": dict
        }
    """
    ext = os.path.splitext(file_path)[1].lower()
    file_name = os.path.basename(file_path)
    result = {"file_name": file_name, "file_path": file_path, "extension": ext, "primary_table": None, "error": None, "meta": {}}

    try:
        if ext == ".docx":
            parsed = parse_docx(file_path)
        elif ext in (".xlsx",):
            parsed = parse_xlsx(file_path)
        elif ext in (".xls",):
            parsed = parse_xls(file_path)
        elif ext == ".pdf":
            parsed = parse_pdf(file_path)
        elif ext == ".et":
            parsed = parse_et(file_path)
        else:
            result["error"] = f"不支持的文件格式: {ext}"
            return result

        if "error" in parsed:
            result["error"] = parsed.get("error")
            result["message"] = parsed.get("message", "")

        result["primary_table"] = parsed.get("primary_table")
        result["meta"] = {k: v for k, v in parsed.items() if k not in ("primary_table", "error", "message")}

    except Exception as e:
        result["error"] = f"解析失败: {str(e)}"

    return result
