from django.conf import settings

def branding(request):
    user = getattr(request, "user", None)

    def in_group(name: str) -> bool:
        try:
            return bool(user and user.is_authenticated and user.groups.filter(name=name).exists())
        except Exception:
            return False

    is_dosen = bool(getattr(user, "profil_dosen", None)) if user and getattr(user, "is_authenticated", False) else False
    is_mahasiswa = bool(getattr(user, "profil_mahasiswa", None)) if user and getattr(user, "is_authenticated", False) else False

    is_operator = bool(user and user.is_authenticated and (user.is_superuser or in_group("Operator Prodi")))
    is_verifikator = bool(user and user.is_authenticated and (user.is_superuser or in_group("Verifikator Akreditasi")))

    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Dosen Digital"),
        "ORGANIZATION_NAME": getattr(settings, "ORGANIZATION_NAME", ""),
        "THEME_COLOR": getattr(settings, "THEME_COLOR", "#2563EB"),

        # ✅ flags untuk template
        "IS_DOSEN": is_dosen,
        "IS_MAHASISWA": is_mahasiswa,
        "IS_OPERATOR": is_operator,
        "IS_VERIFIKATOR": is_verifikator,
    }