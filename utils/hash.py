import hashlib


def make_external_id(*parts: str) -> str:
    """
    Genera un hash estable para deduplicación
    """
    normalized = "|".join(
        part.strip().lower() for part in parts if part
    )

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
