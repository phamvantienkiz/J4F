from backend.app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token

def test_password_hashing():
    password = "supersecretpassword123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_jwt_tokens():
    subject = "user_id_12345"
    token = create_access_token(subject)
    decoded = decode_access_token(token)
    assert decoded == subject

def test_jwt_invalid_token():
    assert decode_access_token("invalid.token.here") is None
