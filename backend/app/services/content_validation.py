import re

from fastapi import HTTPException

TOKEN_PATTERN = re.compile(r"{{\s*([^{}]+?)\s*}}")


def extract_template_tokens(html: str) -> list[str]:
    tokens = [token.strip() for token in TOKEN_PATTERN.findall(html)]
    return list(dict.fromkeys(token for token in tokens if token))


def validate_template_tokens(html: str, allowed_tokens: list[str]) -> list[str]:
    tokens = extract_template_tokens(html)
    unknown = [token for token in tokens if token not in set(allowed_tokens)]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown template tokens: {', '.join(sorted(unknown))}",
        )
    return tokens
