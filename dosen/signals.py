from __future__ import annotations

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .middleware import get_current_user
from .models import (
    AuditLog,
    CatatanBimbingan,
    DokumenTriDharma,
    DosenProfile,
    KelasKuliah,
    LuaranMataKuliah,
    MahasiswaProfile,
    MataKuliah,
    PengajuanBimbingan,
    SubmissionLuaran,
)

TRACK_MODELS = (
    DosenProfile,
    MahasiswaProfile,
    PengajuanBimbingan,
    CatatanBimbingan,
    MataKuliah,
    KelasKuliah,
    LuaranMataKuliah,
    SubmissionLuaran,
    DokumenTriDharma,
)


def _model_label(instance) -> str:
    return f"{instance.__class__.__module__}.{instance.__class__.__name__}"


def _serialize_value(val):
    try:
        if hasattr(val, "_meta") and hasattr(val, "pk"):
            return str(val.pk) if val.pk is not None else None
    except Exception:
        pass

    try:
        import uuid
        import datetime
        from decimal import Decimal

        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.isoformat()
        if isinstance(val, uuid.UUID):
            return str(val)
        if isinstance(val, Decimal):
            return str(val)
    except Exception:
        pass

    return val


@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    if sender not in TRACK_MODELS:
        return

    if not getattr(instance, "pk", None):
        instance._audit_changes = None
        return

    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._audit_changes = None
        return

    changes: dict[str, dict[str, object]] = {}

    for field in instance._meta.fields:
        key = field.name
        attname = getattr(field, "attname", field.name)

        if key in ("updated_at", "created_at"):
            continue

        new_val = getattr(instance, attname, None)
        old_val = getattr(old, attname, None)

        # FileField: bandingkan "name"
        if hasattr(old_val, "name") or hasattr(new_val, "name"):
            old_val = getattr(old_val, "name", None)
            new_val = getattr(new_val, "name", None)

        if old_val != new_val:
            changes[key] = {"from": _serialize_value(old_val), "to": _serialize_value(new_val)}

    instance._audit_changes = changes or None


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    if sender not in TRACK_MODELS:
        return

    user = get_current_user()
    if hasattr(user, "is_authenticated") and not user.is_authenticated:
        user = None

    AuditLog.objects.create(
        user=user,
        action=AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE,
        model=_model_label(instance),
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        changes=getattr(instance, "_audit_changes", None),
    )


@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    if sender not in TRACK_MODELS:
        return

    user = get_current_user()
    if hasattr(user, "is_authenticated") and not user.is_authenticated:
        user = None

    AuditLog.objects.create(
        user=user,
        action=AuditLog.Action.DELETE,
        model=_model_label(instance),
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        changes=None,
    )
