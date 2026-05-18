import struct
import os
import subprocess
import olefile
from config import WPS_SEARCH_PATHS


def parse_et(file_path: str) -> dict:
    """Parse WPS .et spreadsheet file.

    Strategy A: Self-developed olefile BIFF8 parser (experimental).
    Strategy B: Fallback to WPS command-line conversion (Windows only).
    Strategy C: Prompt user to convert to .xlsx.
    """
    # Strategy B first: WPS conversion (more reliable on Windows)
    result = _parse_et_via_wps(file_path)
    if result and result.get("primary_table") and len(result.get("primary_table", [])) > 1:
        return result

    # Strategy A: olefile parser (experimental, may have data issues)
    result = _parse_et_olefile(file_path)
    if result and result.get("primary_table") and len(result["primary_table"]) > 1:
        result["_warning"] = "ET 文件解析为实验性功能，数据可能不完整。建议用 WPS 另存为 .xlsx 格式。"
        return result

    return {"error": "ET_PARSE_FAILED", "primary_table": None,
            "message": "无法解析 .et 文件。WPS 格式(.et)支持有限，请用 WPS 打开文件后另存为 .xlsx 格式再上传。"}


def _parse_et_olefile(file_path: str) -> dict:
    """Self-developed BIFF8 parser for .et files."""
    try:
        ole = olefile.OleFileIO(file_path)
        if not ole.exists("Workbook"):
            return None
        data = ole.openstream("Workbook").read()
    except Exception:
        return None

    # Collect SST and CONTINUE records
    sst_chunks = []
    pos = 0
    collecting_sst = False
    while pos < len(data) - 4:
        rec_type, rec_size = struct.unpack_from("<HH", data, pos)
        if rec_type == 0x00FC:  # SST
            sst_chunks.append(data[pos + 4 : pos + 4 + rec_size])
            collecting_sst = True
        elif rec_type == 0x003C and collecting_sst:  # CONTINUE for SST
            sst_chunks.append(data[pos + 4 : pos + 4 + rec_size])
        elif rec_type == 0x000A:  # EOF
            break
        else:
            collecting_sst = False
        pos += 4 + rec_size

    if not sst_chunks:
        return None

    sst_full = b"".join(sst_chunks)
    strings = _parse_sst_strings(sst_full)
    if not strings:
        return None

    # Parse all cell data records
    pos = 0
    cell_data = {}  # (row, col) -> value (str or float)

    while pos < len(data) - 4:
        rec_type, rec_size = struct.unpack_from("<HH", data, pos)
        record_data = data[pos + 4 : pos + 4 + rec_size]

        try:
            if rec_type == 0x00FD and rec_size >= 8:  # LABELSST
                row, col, xf = struct.unpack_from("<HHH", record_data, 0)
                sst_idx = struct.unpack_from("<H", record_data, 6)[0]
                if sst_idx < len(strings):
                    cell_data[(row, col)] = strings[sst_idx]

            elif rec_type == 0x027E and rec_size >= 10:  # RK value
                row, col, xf = struct.unpack_from("<HHH", record_data, 0)
                rk_raw = struct.unpack_from("<I", record_data, 6)[0]
                cell_data[(row, col)] = _decode_rk(rk_raw)

            elif rec_type == 0x0203 and rec_size >= 14:  # NUMBER
                row, col, xf = struct.unpack_from("<HHH", record_data, 0)
                num = struct.unpack_from("<d", record_data, 6)[0]
                cell_data[(row, col)] = num
        except Exception:
            pass

        pos += 4 + rec_size

    if not cell_data:
        return None

    # Build table from cell data
    max_row = max(r for r, c in cell_data)
    max_col = max(c for r, c in cell_data)

    table = []
    for r in range(max_row + 1):
        row_vals = []
        for c in range(max_col + 1):
            val = cell_data.get((r, c), "")
            if isinstance(val, float):
                if val == int(val) and abs(val) < 1e9:
                    row_vals.append(str(int(val)))
                else:
                    row_vals.append(str(val))
            else:
                row_vals.append(str(val))
        if any(cell.strip() for cell in row_vals):
            table.append(row_vals)

    return {"primary_table": table, "sheets": {"Sheet1": table}, "primary_sheet": "Sheet1"}


def _parse_sst_strings(sst_data: bytes) -> list:
    """Parse BIFF8 Shared String Table with continue record handling."""
    if len(sst_data) < 8:
        return []

    cst_total, _ = struct.unpack_from("<II", sst_data, 0)
    strings = []
    pos = 8

    while pos < len(sst_data) and len(strings) < cst_total:
        if pos + 3 > len(sst_data):
            break
        cch = struct.unpack_from("<H", sst_data, pos)[0]
        pos += 2
        flags = sst_data[pos]
        pos += 1
        is_16bit = bool(flags & 0x01)
        has_ext = bool(flags & 0x08)

        if is_16bit:
            raw_len = cch * 2
            if pos + raw_len > len(sst_data):
                break
            raw = sst_data[pos : pos + raw_len]
            s = raw.decode("utf-16-le", errors="replace")
            pos += raw_len
        else:
            if pos + cch > len(sst_data):
                break
            raw = sst_data[pos : pos + cch]
            s = raw.decode("gbk", errors="replace")
            pos += cch

        if has_ext:
            if pos + 2 > len(sst_data):
                break
            ext_runs = struct.unpack_from("<H", sst_data, pos)[0]
            # Sanity check ext_runs
            if ext_runs > 1000:
                break
            pos += 2 + ext_runs * 4

        strings.append(s)

    return strings


def _decode_rk(rk_raw: int) -> float:
    """Decode BIFF8 RK value to float."""
    is_int = bool(rk_raw & 0x02)
    if is_int:
        val = rk_raw >> 2
        return float(val)
    else:
        is_div100 = bool(rk_raw & 0x01)
        ieee = (rk_raw & 0xFFFFFFFC) >> 2
        val = float(ieee)
        if is_div100:
            val = val / 100.0
        return val


def _find_wps_et_exe() -> str:
    """Find WPS et.exe executable."""
    for base in WPS_SEARCH_PATHS:
        if not os.path.exists(base):
            continue
        for root, dirs, files in os.walk(base):
            if "et.exe" in files:
                return os.path.join(root, "et.exe")
            if root.count(os.sep) - base.count(os.sep) > 4:
                dirs.clear()
    return None


def _parse_et_via_wps(file_path: str) -> dict:
    """Convert .et to .xlsx via WPS et.exe, then parse."""
    et_path = _find_wps_et_exe()
    if not et_path:
        return None

    import tempfile
    output_dir = tempfile.mkdtemp()

    try:
        subprocess.run(
            [et_path, "/x", file_path, output_dir],
            capture_output=True, text=True, timeout=30, shell=True
        )
        for f in os.listdir(output_dir):
            if f.endswith(".xlsx"):
                from models.excel_parser import parse_xlsx
                return parse_xlsx(os.path.join(output_dir, f))
    except Exception:
        pass

    return None
