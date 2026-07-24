from datetime import timedelta
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend import security


TEST_SECRET = "test-only-secret-key-with-at-least-32-characters"


class ScalarSession:
    def __init__(self, user):
        self.user = user

    def scalar(self, _statement):
        return self.user


@pytest.fixture(autouse=True)
def jwt_settings(monkeypatch):
    monkeypatch.setattr(security, "JWT_SECRET_KEY", TEST_SECRET)
    monkeypatch.setattr(security, "JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(security, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60)


def user(**overrides):
    values = {
        "user_id": 7,
        "account_type": "MEMBER",
        "is_active": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def credentials(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_valid_access_token_authenticates_user():
    expected = user()
    token = security.create_access_token(expected)

    authenticated = security.get_current_user(
        credentials(token), ScalarSession(expected)
    )

    assert authenticated is expected


def test_expired_access_token_returns_401():
    token = security.create_access_token(user(), expires_delta=timedelta(seconds=-1))

    with pytest.raises(HTTPException) as error:
        security.decode_access_token(token)

    assert error.value.status_code == 401


def test_forged_access_token_returns_401():
    token = jwt.encode(
        {
            "sub": "7",
            "account_type": "MEMBER",
            "iat": 1,
            "exp": 4_102_444_800,
            "type": "access",
        },
        "different-secret-key-with-at-least-32-characters",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as error:
        security.decode_access_token(token)

    assert error.value.status_code == 401


def test_missing_token_returns_401():
    with pytest.raises(HTTPException) as error:
        security.get_current_user(None, ScalarSession(user()))

    assert error.value.status_code == 401


def test_inactive_user_returns_403():
    inactive = user(is_active=False)
    token = security.create_access_token(inactive)

    with pytest.raises(HTTPException) as error:
        security.get_current_user(credentials(token), ScalarSession(inactive))

    assert error.value.status_code == 403


def test_token_role_change_requires_login_again():
    original = user(account_type="MEMBER")
    token = security.create_access_token(original)
    changed = user(account_type="TRAINER")

    with pytest.raises(HTTPException) as error:
        security.get_current_user(credentials(token), ScalarSession(changed))

    assert error.value.status_code == 401


def test_self_access_allows_owner_and_rejects_other_user():
    owner = user(user_id=7)
    security.enforce_self(owner, 7)

    with pytest.raises(HTTPException) as error:
        security.enforce_self(owner, 8)

    assert error.value.status_code == 403


def test_account_type_dependency_rejects_wrong_role():
    dependency = security.require_account_type("ADMIN")

    with pytest.raises(HTTPException) as error:
        dependency(user(account_type="MEMBER"))

    assert error.value.status_code == 403


def test_active_trainer_member_relation_is_required():
    relation = SimpleNamespace(
        trainer_id=10, member_id=20, status="ACTIVE"
    )
    assert security.require_active_trainer_member(
        ScalarSession(relation), trainer_id=10, member_id=20
    ) is relation

    with pytest.raises(HTTPException) as error:
        security.require_active_trainer_member(
            ScalarSession(None), trainer_id=10, member_id=21
        )

    assert error.value.status_code == 403
