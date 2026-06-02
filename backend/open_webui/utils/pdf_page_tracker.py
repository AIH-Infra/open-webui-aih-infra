"""
PDF页码追踪工具
用于从结构化提取的 PDF / markdown 文本中提取页码信息并附加到切块元数据
"""

import re
from typing import Dict, List, Optional, Tuple


Anchor = Tuple[int, int]
PageRange = Optional[Tuple[int, int]]

PDF_ANCHOR_PATTERN = re.compile(r"\{(\d+)\}")
PRINT_PAGE_PATTERN = re.compile(r"<!--\s*Page:\s*(\d+)\s*-->", re.IGNORECASE)
SPAN_PAGE_PATTERN = re.compile(r"<span\s+id=\"page-(\d+)-\d+\"></span>", re.IGNORECASE)
MEANINGFUL_TEXT_PATTERN = re.compile(
    r"(?:\{\d+\}|<!--\s*Page:\s*\d+\s*-->|<span\s+id=\"page-\d+-\d+\"></span>|\s|[-–—])+",
    re.IGNORECASE,
)


def extract_page_anchors(text: str) -> List[Anchor]:
    """
    提取文本中的 PDF 绝对页码锚点：{192}
    """
    return [
        (match.start(), int(match.group(1)))
        for match in PDF_ANCHOR_PATTERN.finditer(text or "")
    ]



def extract_print_page_anchors(text: str) -> List[Anchor]:
    """
    提取文本中的印刷页码锚点：<!-- Page: 170 -->
    """
    return [
        (match.start(), int(match.group(1)))
        for match in PRINT_PAGE_PATTERN.finditer(text or "")
    ]



def extract_span_page_anchors(text: str) -> List[Anchor]:
    """
    提取文本中的 span 页码锚点：<span id="page-201-0"></span>
    视为 PDF 绝对页码锚点的补充来源。
    """
    return [
        (match.start(), int(match.group(1)))
        for match in SPAN_PAGE_PATTERN.finditer(text or "")
    ]



def extract_all_page_anchors(text: str) -> Dict[str, List[Anchor]]:
    """
    返回统一锚点结构：
    - pdf: {192} 与 <span id="page-192-0"></span>
    - print: <!-- Page: 170 -->
    """
    pdf_anchors = extract_page_anchors(text)
    pdf_anchors.extend(extract_span_page_anchors(text))
    pdf_anchors.sort(key=lambda item: (item[0], item[1]))

    deduped_pdf_anchors: List[Anchor] = []
    seen_pdf = set()
    for anchor in pdf_anchors:
        if anchor not in seen_pdf:
            deduped_pdf_anchors.append(anchor)
            seen_pdf.add(anchor)

    print_anchors = extract_print_page_anchors(text)

    return {
        "pdf": deduped_pdf_anchors,
        "print": print_anchors,
    }



def _has_meaningful_content_after(chunk_text: str, anchor_end: int) -> bool:
    remainder = (chunk_text or "")[anchor_end:]
    if not remainder:
        return False

    cleaned = MEANINGFUL_TEXT_PATTERN.sub("", remainder)
    return bool(cleaned.strip())



def _get_range_from_direct_anchors(
    chunk_text: str,
    pattern: re.Pattern,
) -> PageRange:
    matches = list(pattern.finditer(chunk_text or ""))
    if not matches:
        return None

    first_match = matches[0]
    last_match = matches[-1]
    page_start = int(first_match.group(1))
    page_end = int(last_match.group(1))

    if _has_meaningful_content_after(chunk_text, last_match.end()):
        page_end += 1

    if page_end < page_start:
        page_end = page_start

    return (page_start, page_end)



def _find_chunk_position(chunk_text: str, full_text: str) -> int:
    chunk_clean = re.sub(
        r"\{\d+\}|<!--\s*Page:\s*\d+\s*-->|<span\s+id=\"page-\d+-\d+\"></span>",
        "",
        chunk_text or "",
        flags=re.IGNORECASE,
    )

    chunk_start = -1
    search_len = min(200, len(chunk_clean))
    if search_len > 0:
        chunk_start = full_text.find(chunk_clean[:search_len])

    if chunk_start == -1 and len(chunk_clean) > 50:
        chunk_stripped = chunk_clean.lstrip().lstrip("#").lstrip()
        search_len = min(150, len(chunk_stripped))
        if search_len > 0:
            chunk_start = full_text.find(chunk_stripped[:search_len])

    if chunk_start == -1 and len(chunk_clean) > 30:
        sentences = re.split(r"[.!?。！？]", chunk_clean)
        if len(sentences) > 0 and len(sentences[0]) > 20:
            chunk_start = full_text.find(sentences[0][:100])

    return chunk_start



def _get_range_from_full_text(
    chunk_text: str,
    full_text: str,
    anchors: List[Anchor],
) -> PageRange:
    if not anchors:
        return None

    chunk_start = _find_chunk_position(chunk_text, full_text)
    if chunk_start == -1:
        return None

    chunk_end = chunk_start + len(chunk_text)

    page_start: Optional[int] = None
    for pos, page_num in anchors:
        if pos <= chunk_start:
            page_start = page_num
        else:
            break

    if page_start is None:
        return None

    page_end = page_start
    last_anchor_before_end: Optional[Anchor] = None
    for pos, page_num in anchors:
        if pos < chunk_end:
            last_anchor_before_end = (pos, page_num)
            page_end = page_num
        else:
            break

    if last_anchor_before_end is not None:
        chunk_relative_anchor_end = last_anchor_before_end[0] - chunk_start
        if chunk_relative_anchor_end < 0:
            chunk_relative_anchor_end = 0
        if _has_meaningful_content_after(chunk_text, chunk_relative_anchor_end):
            page_end += 1

    if page_end < page_start:
        page_end = page_start

    return (page_start, page_end)



def get_page_range_for_chunk(
    chunk_text: str,
    full_text: str,
    page_anchors: List[Anchor],
) -> PageRange:
    """
    确定 chunk 在原文中的 PDF 绝对页码范围。
    优先直接解析 chunk 内的 {n}；找不到时再回退到 full_text 定位。
    """
    if not page_anchors:
        return None

    direct_range = _get_range_from_direct_anchors(chunk_text, PDF_ANCHOR_PATTERN)
    if direct_range is not None:
        return direct_range

    return _get_range_from_full_text(chunk_text, full_text, page_anchors)



def get_print_page_range_for_chunk(
    chunk_text: str,
    full_text: str,
    page_anchors: List[Anchor],
) -> PageRange:
    """
    确定 chunk 在原文中的印刷页码范围。
    优先直接解析 chunk 内的 <!-- Page: n -->；找不到时再回退到 full_text 定位。
    """
    if not page_anchors:
        return None

    direct_range = _get_range_from_direct_anchors(chunk_text, PRINT_PAGE_PATTERN)
    if direct_range is not None:
        return direct_range

    return _get_range_from_full_text(chunk_text, full_text, page_anchors)



def get_chunk_page_metadata(
    chunk_text: str,
    full_text: str,
    pdf_anchors: Optional[List[Anchor]] = None,
    print_anchors: Optional[List[Anchor]] = None,
) -> Dict[str, int]:
    """
    统一返回 chunk 页码元数据。
    """
    metadata: Dict[str, int] = {}

    pdf_range = get_page_range_for_chunk(chunk_text, full_text, pdf_anchors or [])
    if pdf_range is not None:
        metadata["page_start"] = pdf_range[0]
        metadata["page_end"] = pdf_range[1]

    print_range = get_print_page_range_for_chunk(
        chunk_text, full_text, print_anchors or []
    )
    if print_range is not None:
        metadata["print_page_start"] = print_range[0]
        metadata["print_page_end"] = print_range[1]

    return metadata
