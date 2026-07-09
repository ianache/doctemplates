import re

from fastapi import HTTPException

TOKEN_PATTERN = re.compile(r"{{\s*([^{}]+?)\s*}}")


def extract_template_tokens(html: str) -> list[str]:
    tokens = [token.strip() for token in TOKEN_PATTERN.findall(html)]
    return list(dict.fromkeys(token for token in tokens if token))


def clean_token(token: str) -> str:
    # Remove filters
    base = token.split("|")[0].strip()
    # Normalize list indices e.g. [0] -> []
    base = re.sub(r"\[\d+\]", "[]", base)
    return base.strip()


def validate_template_tokens(html: str, allowed_tokens: list[str]) -> list[str]:
    raw_tokens = extract_template_tokens(html)
    cleaned_allowed = {a.lower() for a in allowed_tokens}
    
    unknown = []
    validated_tokens = []
    
    for raw in raw_tokens:
        token = clean_token(raw)
        if not token:
            continue
        
        # Exact case-insensitive match
        if token.lower() in cleaned_allowed:
            validated_tokens.append(raw)
            continue
            
        # Fallback check (leaf-level comparison for dots in list elements)
        if "." in token:
            token_leaf = token.split(".")[-1].strip().lower()
            matched = False
            for allowed in allowed_tokens:
                if "[]" in allowed:
                    allowed_leaf = allowed.split(".")[-1].strip().lower()
                    if token_leaf == allowed_leaf:
                        matched = True
                        break
            if matched:
                validated_tokens.append(raw)
                continue
                
        unknown.append(raw)
        
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown template tokens: {', '.join(sorted(list(set(unknown))))}",
        )
    return validated_tokens
