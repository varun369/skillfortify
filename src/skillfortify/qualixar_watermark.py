# Copyright (c) 2026 Varun Pratap Bhardwaj. All rights reserved.
# Licensed under MIT. See LICENSE file.
# Part of Qualixar — The Complete Agent Development Platform
"""Steganographic watermarking for invisible attribution in text outputs.

This module embeds invisible zero-width Unicode characters into text outputs
(HTML reports, CLI text, log files) to provide a hidden attribution layer
that survives copy-paste and reformatting.

The watermark encodes a tool identifier string as binary data using zero-width
characters that are invisible to humans but detectable by software.

Encoding scheme:
    - Zero-width space (U+200B) = binary 0
    - Zero-width joiner (U+200D) = binary 1
    - Byte order mark (U+FEFF) = delimiter/separator

Usage::

    from skillfortify.qualixar_watermark import encode_watermark, decode_watermark

    text = "SkillFortify Security Report\\n\\nFindings: 3 issues detected."
    marked = encode_watermark(text, "skillfortify")
    assert decode_watermark(marked) == "skillfortify"
    # The watermark is invisible — marked text looks identical to original.
"""

from __future__ import annotations

# Zero-width characters for binary encoding
ZW_SPACE = "\u200b"   # Zero-width space = 0
ZW_JOINER = "\u200d"  # Zero-width joiner = 1
ZW_SEP = "\ufeff"     # Byte order mark = separator


def encode_watermark(text: str, tool_id: str) -> str:
    """Embed an invisible watermark in text output.

    The watermark is inserted after the first paragraph break (double newline).
    If no paragraph break exists, it is appended to the end of the text.

    The watermark is completely invisible in terminals, browsers, and text
    editors. It does not affect rendering, line counts, or word counts.

    Args:
        text: The text content to watermark.
        tool_id: The identifier string to embed (e.g., "skillfortify").

    Returns:
        The text with an invisible watermark embedded.
    """
    binary = "".join(format(ord(c), "08b") for c in tool_id)
    watermark = ZW_SEP
    for bit in binary:
        watermark += ZW_SPACE if bit == "0" else ZW_JOINER
    watermark += ZW_SEP

    if "\n\n" in text:
        idx = text.index("\n\n") + 2
        return text[:idx] + watermark + text[idx:]
    return text + watermark


def decode_watermark(text: str) -> str:
    """Extract a hidden watermark from text.

    Locates the zero-width character sequence between two BOM delimiters
    and decodes the binary data back to the original tool identifier.

    Args:
        text: Text that may contain an embedded watermark.

    Returns:
        The decoded tool identifier string, or empty string if no
        watermark is found.
    """
    start = text.find(ZW_SEP)
    if start == -1:
        return ""
    end = text.find(ZW_SEP, start + 1)
    if end == -1:
        return ""
    encoded = text[start + 1:end]
    binary = "".join("0" if c == ZW_SPACE else "1" for c in encoded)
    chars = [binary[i:i + 8] for i in range(0, len(binary), 8)]
    return "".join(chr(int(b, 2)) for b in chars if len(b) == 8)


def has_watermark(text: str) -> bool:
    """Check if text contains a Qualixar watermark.

    A quick check without decoding the full content.

    Args:
        text: Text to check.

    Returns:
        True if the text contains watermark delimiters.
    """
    start = text.find(ZW_SEP)
    if start == -1:
        return False
    return text.find(ZW_SEP, start + 1) != -1
