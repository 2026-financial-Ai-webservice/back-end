import secrets


def generate_share_token(length: int = 16) -> str:
    """포트폴리오 결과 공유용 랜덤 토큰 생성"""
    return secrets.token_hex(length)