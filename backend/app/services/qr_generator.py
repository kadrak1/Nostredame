"""QR code generation service.

Generates QR-code PNGs using the *qrcode[pil]* library.
Each QR encodes a URL that leads guests to the table landing page.
"""

import io

import qrcode
import qrcode.constants


def generate_qr_png(url: str, size: int = 300) -> bytes:
    """Generate a square QR-code PNG and return raw bytes.

    Args:
        url:  The URL to encode in the QR code.
        size: Desired output dimension in pixels (square). Default 300 px.

    Returns:
        PNG-encoded bytes ready to be served as ``image/png``.
    """
    # box_size: pixels per individual QR module.
    # A typical auto-version code with border=4 is ~(version*4+17 + 8) modules wide.
    # Version-1 → 29 cells; version-3 → 37 cells.
    # box_size = size // 33 is a good heuristic for URLs up to ~50 chars.
    box_size = max(4, size // 33)

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
