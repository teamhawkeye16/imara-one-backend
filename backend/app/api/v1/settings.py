"""
User Privacy and Search Settings Endpoints
"""

import hashlib
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user_settings import UserSetting
from backend.app.schemas.settings import UserSettingsSchema, UpdateSettingsSchema

router = APIRouter(tags=["Settings"])


def get_client_hash(request: Request, client_token: str = None) -> str:
    """Generate anonymous client identifier hash without exposing raw IP."""
    token = client_token or request.headers.get("x-client-token") or "anonymous_default"
    return hashlib.sha256(f"imara_client_{token}".encode()).hexdigest()


@router.get("/settings", response_model=UserSettingsSchema)
def get_user_settings(
    request: Request,
    x_client_token: str = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Get privacy and search preferences for client.
    """
    client_hash = get_client_hash(request, x_client_token)
    user_setting = db.query(UserSetting).filter(UserSetting.client_id_hash == client_hash).first()

    if not user_setting:
        # Return defaults
        return UserSettingsSchema(
            safe_search="moderate",
            privacy_level="maximum",
            ai_enabled=True,
            results_per_page=10,
            theme="dark",
            allow_anonymous_metrics=False,
        )

    return UserSettingsSchema(
        safe_search=user_setting.safe_search,
        privacy_level=user_setting.privacy_level,
        ai_enabled=user_setting.ai_enabled,
        results_per_page=user_setting.results_per_page,
        theme=user_setting.theme,
        allow_anonymous_metrics=user_setting.allow_anonymous_metrics,
    )


@router.post("/settings", response_model=UserSettingsSchema)
def update_user_settings(
    request: Request,
    payload: UpdateSettingsSchema,
    x_client_token: str = Header(default=None),
    db: Session = Depends(get_db),
):
    """
    Update privacy preferences.
    """
    client_hash = get_client_hash(request, payload.client_id or x_client_token)
    user_setting = db.query(UserSetting).filter(UserSetting.client_id_hash == client_hash).first()

    if not user_setting:
        user_setting = UserSetting(
            client_id_hash=client_hash,
            safe_search=payload.safe_search or "moderate",
            privacy_level=payload.privacy_level or "maximum",
            ai_enabled=payload.ai_enabled if payload.ai_enabled is not None else True,
            results_per_page=payload.results_per_page or 10,
            theme=payload.theme or "dark",
            allow_anonymous_metrics=payload.allow_anonymous_metrics or False,
        )
        db.add(user_setting)
    else:
        if payload.safe_search is not None:
            user_setting.safe_search = payload.safe_search
        if payload.privacy_level is not None:
            user_setting.privacy_level = payload.privacy_level
        if payload.ai_enabled is not None:
            user_setting.ai_enabled = payload.ai_enabled
        if payload.results_per_page is not None:
            user_setting.results_per_page = payload.results_per_page
        if payload.theme is not None:
            user_setting.theme = payload.theme
        if payload.allow_anonymous_metrics is not None:
            user_setting.allow_anonymous_metrics = payload.allow_anonymous_metrics

    db.commit()
    db.refresh(user_setting)

    return UserSettingsSchema(
        safe_search=user_setting.safe_search,
        privacy_level=user_setting.privacy_level,
        ai_enabled=user_setting.ai_enabled,
        results_per_page=user_setting.results_per_page,
        theme=user_setting.theme,
        allow_anonymous_metrics=user_setting.allow_anonymous_metrics,
    )

