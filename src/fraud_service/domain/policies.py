from fastapi import HTTPException

from fraud_service.domain.entities import Decision

REVIEW_BAND = 0.15


def decide(probability: float, block_threshold: float) -> Decision:
    if not 0.0 <= probability <= 1.0:
        raise HTTPException(status_code=422, detail="probability out of range")
    if probability >= block_threshold:
        return Decision.BLOCK
    if probability >= block_threshold - REVIEW_BAND:
        return Decision.REVIEW
    return Decision.ALLOW
