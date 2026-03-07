from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from .forms import (
    CatatanBimbinganForm,
    DokumenTriDharmaForm,
    DokumenTriDharmaReviewForm,
    KelasKuliahForm,
    LuaranMataKuliahForm,
    MataKuliahForm,
    PengajuanBimbinganForm,
    PengajuanBimbinganReviewForm,
    SubmissionLuaranForm,
    SubmissionReviewForm,
    DosenProfileForm,
    MahasiswaProfileForm,
)
from .models import (
    CatatanBimbingan,
    DokumenTriDharma,
    EnrollmentKelas,
    KelasKuliah,
    LuaranMataKuliah,
    MataKuliah,
    PengajuanBimbingan,
    SubmissionLuaran,
    ChatThreadBimbingan,
    ChatMessageBimbingan,
)


# =========================
# Helpers (role + group)
# =========================
def _is_dosen(user) -> bool:
    return hasattr(user, "profil_dosen") and user.profil_dosen is not None


def _is_mahasiswa(user) -> bool:
    return hasattr(user, "profil_mahasiswa") and user.profil_mahasiswa is not None


def in_group(user, name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=name).exists()


def is_operator(user) -> bool:
    return user.is_superuser or in_group(user, "Operator Prodi")


def is_verifikator(user) -> bool:
    return user.is_superuser or in_group(user, "Verifikator Akreditasi")


def _can_access_pengajuan(user, pengajuan: PengajuanBimbingan) -> bool:
    """Akses pengajuan untuk detail + chat: pemilik (mhs), dosen pembimbing, operator/verifikator, superuser."""
    if user.is_superuser or is_operator(user) or is_verifikator(user):
        return True
    if _is_mahasiswa(user) and pengajuan.mahasiswa_id == user.profil_mahasiswa.id:
        return True
    if _is_dosen(user) and pengajuan.dosen_pembimbing_id == user.profil_dosen.id:
        return True
    return False


# =========================
# Pages: Home & Dashboard
# =========================
class HomeView(TemplateView):
    template_name = "dosen/home.html"


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dosen/dashboard.html"
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if user.is_authenticated:
            if _is_dosen(user) and getattr(user.profil_dosen, "must_change_password", False):
                return redirect("dosen:force_change_password")
            if _is_mahasiswa(user) and getattr(user.profil_mahasiswa, "must_change_password", False):
                return redirect("dosen:force_change_password")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        user = self.request.user

        pengajuan_qs = PengajuanBimbingan.objects.all()
        catatan_qs = CatatanBimbingan.objects.all()
        luaran_qs = LuaranMataKuliah.objects.all()
        submission_qs = SubmissionLuaran.objects.all()
        akreditasi_qs = DokumenTriDharma.objects.all()

        if _is_dosen(user) and not is_operator(user) and not is_verifikator(user):
            pengajuan_qs = pengajuan_qs.filter(dosen_pembimbing=user.profil_dosen)
            akreditasi_qs = akreditasi_qs.filter(dosen=user.profil_dosen)
            luaran_qs = luaran_qs.filter(kelas__dosen_pengampu=user.profil_dosen)
            submission_qs = submission_qs.filter(luaran__kelas__dosen_pengampu=user.profil_dosen)

        elif _is_mahasiswa(user):
            pengajuan_qs = pengajuan_qs.filter(mahasiswa=user.profil_mahasiswa)
            kelas_ids = EnrollmentKelas.objects.filter(
                mahasiswa=user.profil_mahasiswa,
                is_active=True,
            ).values_list("kelas_id", flat=True)
            luaran_qs = luaran_qs.filter(kelas_id__in=kelas_ids)
            submission_qs = submission_qs.filter(mahasiswa=user.profil_mahasiswa)
            akreditasi_qs = DokumenTriDharma.objects.none()
            catatan_qs = catatan_qs.filter(pengajuan__mahasiswa=user.profil_mahasiswa)

        ctx.update(
            {
                "count_pengajuan": pengajuan_qs.count(),
                "count_pengajuan_open": pengajuan_qs.filter(status=PengajuanBimbingan.Status.DIAJUKAN).count(),
                "count_catatan": catatan_qs.count(),
                "count_luaran": luaran_qs.count(),
                "count_submission": submission_qs.count(),
                "count_akreditasi": akreditasi_qs.count(),
                "count_akreditasi_submitted": akreditasi_qs.filter(status=DokumenTriDharma.Status.DIAJUKAN).count(),
                "recent_pengajuan": pengajuan_qs.order_by("-created_at")[:6],
                "recent_submission": submission_qs.order_by("-created_at")[:6],
                "recent_akreditasi": akreditasi_qs.order_by("-created_at")[:6],
                "today": today,
            }
        )
        return ctx


# =========================
# ListView base (search)
# =========================
class SearchableListView(LoginRequiredMixin, ListView):
    search_param = "q"
    search_fields: tuple[str, ...] = ()
    login_url = reverse_lazy("login")

    def get_search_query(self) -> str:
        return (self.request.GET.get(self.search_param) or "").strip()

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.get_search_query()
        if q and self.search_fields:
            cond = Q()
            for f in self.search_fields:
                cond |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(cond)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.get_search_query()
        return ctx


# =========================================================
# 1) Bimbingan (Pengajuan & Log Catatan)
# =========================================================
class PengajuanBimbinganListView(SearchableListView):
    model = PengajuanBimbingan
    template_name = "dosen/bimbingan/list.html"
    paginate_by = 10
    search_fields = ("mahasiswa__nama", "mahasiswa__nim", "dosen_pembimbing__nama", "topik", "pesan", "status")

    def get_queryset(self):
        qs = super().get_queryset().select_related("mahasiswa", "dosen_pembimbing")
        user = self.request.user
        if _is_dosen(user) and not is_operator(user) and not is_verifikator(user):
            return qs.filter(dosen_pembimbing=user.profil_dosen)
        if _is_mahasiswa(user):
            return qs.filter(mahasiswa=user.profil_mahasiswa)
        return qs


class PengajuanBimbinganCreateView(LoginRequiredMixin, CreateView):
    model = PengajuanBimbingan
    form_class = PengajuanBimbinganForm
    template_name = "dosen/bimbingan/form.html"
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm("dosen.add_pengajuanbimbingan"):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.dibuat_oleh = self.request.user

        if _is_mahasiswa(self.request.user):
            self.object.mahasiswa = self.request.user.profil_mahasiswa

        self.object.save()
        messages.success(self.request, "Pengajuan bimbingan berhasil dibuat.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("dosen:bimbingan_detail", kwargs={"pk": self.object.pk})


class PengajuanBimbinganDetailView(LoginRequiredMixin, DetailView):
    model = PengajuanBimbingan
    template_name = "dosen/bimbingan/detail.html"
    login_url = reverse_lazy("login")

    def get_queryset(self):
        # catatan + thread chat akan di-load via API polling
        qs = super().get_queryset().select_related("mahasiswa", "dosen_pembimbing").prefetch_related("catatan")
        user = self.request.user
        if _is_dosen(user) and not is_operator(user) and not is_verifikator(user):
            qs = qs.filter(dosen_pembimbing=user.profil_dosen)
        if _is_mahasiswa(user):
            qs = qs.filter(mahasiswa=user.profil_mahasiswa)
        return qs


@login_required(login_url="login")
def pengajuan_review(request, pk: int):
    obj = get_object_or_404(PengajuanBimbingan, pk=pk)
    if not (
        request.user.is_superuser
        or is_operator(request.user)
        or (_is_dosen(request.user) and obj.dosen_pembimbing_id == request.user.profil_dosen.id)
    ):
        messages.error(request, "Anda tidak punya akses untuk mereview pengajuan ini.")
        return redirect("dosen:bimbingan_detail", pk=pk)

    if request.method == "POST":
        form = PengajuanBimbinganReviewForm(request.POST, instance=obj)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.status == PengajuanBimbingan.Status.DISETUJUI and not updated.jadwal_disetujui:
                updated.jadwal_disetujui = timezone.now()
            updated.save()
            messages.success(request, "Review pengajuan bimbingan tersimpan.")
            return redirect("dosen:bimbingan_detail", pk=pk)
    else:
        form = PengajuanBimbinganReviewForm(instance=obj)

    return render(request, "dosen/bimbingan/review.html", {"form": form, "obj": obj})


@login_required(login_url="login")
def catatan_tambah(request, pk: int):
    pengajuan = get_object_or_404(PengajuanBimbingan, pk=pk)

    if not (
        request.user.is_superuser
        or is_operator(request.user)
        or (_is_dosen(request.user) and pengajuan.dosen_pembimbing_id == request.user.profil_dosen.id)
    ):
        messages.error(request, "Anda tidak punya akses untuk menambahkan catatan.")
        return redirect("dosen:bimbingan_detail", pk=pk)

    if request.method == "POST":
        form = CatatanBimbinganForm(request.POST, request.FILES)
        if form.is_valid():
            c = form.save(commit=False)
            c.pengajuan = pengajuan
            c.dibuat_oleh = request.user
            c.save()
            messages.success(request, "Catatan bimbingan berhasil ditambahkan.")
            return redirect("dosen:bimbingan_detail", pk=pk)
    else:
        form = CatatanBimbinganForm()

    return render(request, "dosen/bimbingan/catatan_form.html", {"form": form, "pengajuan": pengajuan})


@login_required(login_url="login")
def profil_saya(request):
    user = request.user

    if _is_dosen(user):
        obj = user.profil_dosen
        form_class = DosenProfileForm
    elif _is_mahasiswa(user):
        obj = user.profil_mahasiswa
        form_class = MahasiswaProfileForm
    else:
        messages.error(request, "Profil tidak ditemukan.")
        return redirect("dosen:dashboard")

    if request.method == "POST":
        form = form_class(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil berhasil diperbarui.")
            return redirect("dosen:profil_saya")
    else:
        form = form_class(instance=obj)

    return render(request, "dosen/profil_form.html", {"form": form})


@login_required(login_url="login")
def force_change_password(request):
    user = request.user

    must_change = False
    profile = None

    if _is_dosen(user):
        profile = user.profil_dosen
        must_change = profile.must_change_password
    elif _is_mahasiswa(user):
        profile = user.profil_mahasiswa
        must_change = profile.must_change_password

    if not must_change:
        return redirect("dosen:dashboard")

    if request.method == "POST":
        form = PasswordChangeForm(user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)

            if profile:
                profile.must_change_password = False
                profile.save(update_fields=["must_change_password"])

            messages.success(request, "Password berhasil diubah. Silakan lengkapi profil Anda.")
            return redirect("dosen:profil_saya")
    else:
        form = PasswordChangeForm(user)

    return render(request, "dosen/force_change_password.html", {"form": form})


# =========================
# Live chat endpoints (Polling)
# =========================
@require_GET
@login_required(login_url="login")
def chat_messages(request, pk: int):
    pengajuan = get_object_or_404(PengajuanBimbingan, pk=pk)
    if not _can_access_pengajuan(request.user, pengajuan):
        raise PermissionDenied

    thread, _ = ChatThreadBimbingan.objects.get_or_create(pengajuan=pengajuan)

    after = request.GET.get("after")
    qs = thread.messages.select_related("sender").order_by("id")
    if after and after.isdigit():
        qs = qs.filter(id__gt=int(after))

    data = []
    for m in qs[:200]:
        data.append(
            {
                "id": m.id,
                "sender": (m.sender.username if m.sender else "-"),
                "is_me": (m.sender_id == request.user.id),
                "message": m.message,
                "created_at": timezone.localtime(m.created_at).strftime("%d %b %Y %H:%M"),
                "attachment_url": (m.attachment.url if getattr(m, "attachment", None) else None),
                "attachment_name": (m.attachment.name.split("/")[-1] if getattr(m, "attachment", None) else None),
            }
        )

    return JsonResponse({"messages": data})


@require_POST
@login_required(login_url="login")
def chat_send(request, pk: int):
    pengajuan = get_object_or_404(PengajuanBimbingan, pk=pk)
    if not _can_access_pengajuan(request.user, pengajuan):
        raise PermissionDenied

    thread, _ = ChatThreadBimbingan.objects.get_or_create(pengajuan=pengajuan)

    text = (request.POST.get("message") or "").strip()
    file = request.FILES.get("attachment")

    if not text and not file:
        return JsonResponse({"ok": False, "error": "Pesan atau lampiran harus diisi."}, status=400)

    msg = ChatMessageBimbingan.objects.create(
        thread=thread,
        sender=request.user,
        message=text,
        attachment=file,
    )
    return JsonResponse({"ok": True, "id": msg.id})


# =========================================================
# 2) Portofolio Tugas / Luaran MK
# =========================================================
class MataKuliahListView(SearchableListView):
    model = MataKuliah
    template_name = "dosen/portofolio/mk_list.html"
    paginate_by = 10
    search_fields = ("kode", "nama", "prodi", "semester")


class MataKuliahCreateView(LoginRequiredMixin, CreateView):
    model = MataKuliah
    form_class = MataKuliahForm
    template_name = "dosen/portofolio/mk_form.html"
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not (is_operator(request.user) or request.user.is_superuser):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Mata kuliah berhasil ditambahkan.")
        return redirect("dosen:mk_list")


class KelasKuliahListView(SearchableListView):
    model = KelasKuliah
    template_name = "dosen/portofolio/kelas_list.html"
    paginate_by = 10
    search_fields = ("mata_kuliah__kode", "mata_kuliah__nama", "tahun_ajaran", "nama_kelas")

    def get_queryset(self):
        return super().get_queryset().select_related("mata_kuliah").prefetch_related("dosen_pengampu")


class KelasKuliahCreateView(LoginRequiredMixin, CreateView):
    model = KelasKuliah
    form_class = KelasKuliahForm
    template_name = "dosen/portofolio/kelas_form.html"
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not (is_operator(request.user) or request.user.is_superuser):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Kelas kuliah berhasil ditambahkan.")
        return redirect("dosen:kelas_list")


class LuaranListView(SearchableListView):
    model = LuaranMataKuliah
    template_name = "dosen/portofolio/luaran_list.html"
    paginate_by = 10
    search_fields = ("judul", "kelas__mata_kuliah__kode", "kelas__mata_kuliah__nama", "kelas__tahun_ajaran", "kelas__nama_kelas")

    def get_queryset(self):
        qs = super().get_queryset().select_related("kelas", "kelas__mata_kuliah")
        user = self.request.user

        if _is_mahasiswa(user):
            kelas_ids = EnrollmentKelas.objects.filter(
                mahasiswa=user.profil_mahasiswa,
                is_active=True,
            ).values_list("kelas_id", flat=True)
            qs = qs.filter(kelas_id__in=kelas_ids)

        elif _is_dosen(user) and not is_operator(user) and not is_verifikator(user):
            qs = qs.filter(kelas__dosen_pengampu=user.profil_dosen)

        return qs


class LuaranCreateView(LoginRequiredMixin, CreateView):
    model = LuaranMataKuliah
    form_class = LuaranMataKuliahForm
    template_name = "dosen/portofolio/luaran_form.html"
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not (is_operator(request.user) or request.user.is_superuser or _is_dosen(request.user)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Luaran mata kuliah berhasil dibuat.")
        return redirect("dosen:luaran_list")


class LuaranDetailView(LoginRequiredMixin, DetailView):
    model = LuaranMataKuliah
    template_name = "dosen/portofolio/luaran_detail.html"
    login_url = reverse_lazy("login")

    def get_queryset(self):
        qs = super().get_queryset().select_related("kelas", "kelas__mata_kuliah").prefetch_related("submissions")
        user = self.request.user

        if _is_mahasiswa(user):
            kelas_ids = EnrollmentKelas.objects.filter(
                mahasiswa=user.profil_mahasiswa,
                is_active=True,
            ).values_list("kelas_id", flat=True)
            qs = qs.filter(kelas_id__in=kelas_ids)

        elif _is_dosen(user) and not is_operator(user) and not is_verifikator(user):
            qs = qs.filter(kelas__dosen_pengampu=user.profil_dosen)

        return qs


@login_required(login_url="login")
def submission_submit(request, pk: int):
    luaran = get_object_or_404(LuaranMataKuliah, pk=pk)

    if not _is_mahasiswa(request.user) and not request.user.is_superuser:
        messages.error(request, "Hanya mahasiswa yang bisa mengunggah submission.")
        return redirect("dosen:luaran_detail", pk=pk)

    if _is_mahasiswa(request.user):
        allowed = EnrollmentKelas.objects.filter(
            mahasiswa=request.user.profil_mahasiswa,
            kelas=luaran.kelas,
            is_active=True,
        ).exists()
        if not allowed:
            messages.error(request, "Anda tidak terdaftar pada kelas ini.")
            return redirect("dosen:luaran_list")

    existing = None
    if _is_mahasiswa(request.user):
        existing = SubmissionLuaran.objects.filter(luaran=luaran, mahasiswa=request.user.profil_mahasiswa).first()

    if request.method == "POST":
        form = SubmissionLuaranForm(request.POST, request.FILES, instance=existing)
        if form.is_valid():
            obj = form.save(commit=False)
            if _is_mahasiswa(request.user):
                obj.mahasiswa = request.user.profil_mahasiswa
            obj.luaran = luaran
            obj.status = SubmissionLuaran.Status.DIKIRIM
            obj.save()
            messages.success(request, "Submission berhasil diunggah.")
            return redirect("dosen:luaran_detail", pk=pk)
    else:
        form = SubmissionLuaranForm(instance=existing)

    return render(request, "dosen/portofolio/submission_form.html", {"form": form, "luaran": luaran, "existing": existing})


class SubmissionDetailView(LoginRequiredMixin, DetailView):
    model = SubmissionLuaran
    template_name = "dosen/portofolio/submission_detail.html"
    login_url = reverse_lazy("login")

    def get_object(self, queryset=None):
        pk = self.kwargs.get("pk")
        obj = get_object_or_404(
            SubmissionLuaran.objects.select_related("luaran", "luaran__kelas", "mahasiswa"),
            pk=pk
        )
        user = self.request.user

        if _is_mahasiswa(user):
            if obj.mahasiswa_id != user.profil_mahasiswa.id:
                raise PermissionDenied
        elif _is_dosen(user) and not is_operator(user) and not is_verifikator(user):
            if not obj.luaran.kelas.dosen_pengampu.filter(pk=user.profil_dosen.pk).exists():
                raise PermissionDenied
        return obj


@login_required(login_url="login")
def submission_review(request, pk: int):
    sub = get_object_or_404(SubmissionLuaran, pk=pk)

    is_allowed = request.user.is_superuser or is_operator(request.user) or is_verifikator(request.user)
    if not is_allowed and _is_dosen(request.user):
        kelas = sub.luaran.kelas
        is_allowed = kelas.dosen_pengampu.filter(pk=request.user.profil_dosen.pk).exists()

    if not is_allowed:
        messages.error(request, "Anda tidak punya akses untuk mereview submission ini.")
        return redirect("dosen:submission_detail", pk=pk)

    if request.method == "POST":
        form = SubmissionReviewForm(request.POST, instance=sub)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
            obj.save()
            messages.success(request, "Review submission tersimpan.")
            return redirect("dosen:submission_detail", pk=pk)
    else:
        form = SubmissionReviewForm(instance=sub)

    return render(request, "dosen/portofolio/submission_review.html", {"form": form, "sub": sub})


# =========================================================
# 3) Akreditasi (Tri Dharma)
# =========================================================
class DokumenTriDharmaListView(SearchableListView):
    model = DokumenTriDharma
    template_name = "dosen/akreditasi/list.html"
    paginate_by = 10
    search_fields = ("judul", "kategori", "jenis_bukti", "kode_standar", "kata_kunci", "tahun", "semester", "dosen__nama")

    def get_queryset(self):
        qs = super().get_queryset().select_related("dosen")
        user = self.request.user
        if _is_dosen(user) and not is_operator(user) and not is_verifikator(user):
            return qs.filter(dosen=user.profil_dosen)
        if _is_mahasiswa(user):
            return qs.none()
        return qs


class DokumenTriDharmaCreateView(LoginRequiredMixin, CreateView):
    model = DokumenTriDharma
    form_class = DokumenTriDharmaForm
    template_name = "dosen/akreditasi/form.html"
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if _is_mahasiswa(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save(commit=False)
        if _is_dosen(self.request.user):
            obj.dosen = self.request.user.profil_dosen
        if obj.status == DokumenTriDharma.Status.DIAJUKAN:
            obj.submitted_by = self.request.user
            obj.submitted_at = timezone.now()
        obj.save()
        messages.success(self.request, "Dokumen Tri Dharma berhasil disimpan.")
        return redirect("dosen:akreditasi_detail", pk=obj.pk)


class DokumenTriDharmaDetailView(LoginRequiredMixin, DetailView):
    model = DokumenTriDharma
    template_name = "dosen/akreditasi/detail.html"
    login_url = reverse_lazy("login")

    def get_queryset(self):
        qs = super().get_queryset().select_related("dosen")
        user = self.request.user
        if _is_dosen(user) and not is_operator(user) and not is_verifikator(user):
            qs = qs.filter(dosen=user.profil_dosen)
        if _is_mahasiswa(user):
            qs = qs.none()
        return qs


@login_required(login_url="login")
def akreditasi_review(request, pk: int):
    doc = get_object_or_404(DokumenTriDharma, pk=pk)

    if not (is_verifikator(request.user) or is_operator(request.user) or request.user.is_superuser):
        messages.error(request, "Hanya Verifikator (Kaprodi/GKM/UPM) yang bisa melakukan verifikasi dokumen.")
        return redirect("dosen:akreditasi_detail", pk=pk)

    if request.method == "POST":
        form = DokumenTriDharmaReviewForm(request.POST, instance=doc)
        if form.is_valid():
            obj = form.save(commit=False)
            if obj.status == DokumenTriDharma.Status.TERVERIFIKASI:
                obj.verified_by = request.user
                obj.verified_at = timezone.now()
            obj.save()
            messages.success(request, "Status verifikasi dokumen tersimpan.")
            return redirect("dosen:akreditasi_detail", pk=pk)
    else:
        form = DokumenTriDharmaReviewForm(instance=doc)

    return render(request, "dosen/akreditasi/review.html", {"form": form, "doc": doc})
