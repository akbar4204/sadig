from __future__ import annotations

from django import forms
from django.utils import timezone

from .models import (
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


class BootstrapMixin:
    """Tambah class bootstrap pada widget form otomatis."""

    def _bootstrap(self):
        for _, field in self.fields.items():
            w = field.widget
            cls = w.attrs.get("class", "")
            if isinstance(w, (forms.CheckboxInput, forms.RadioSelect)):
                continue
            w.attrs["class"] = (cls + " form-control").strip()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrap()


# --- Bimbingan ---
class PengajuanBimbinganForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PengajuanBimbingan
        fields = ["mahasiswa", "dosen_pembimbing", "jenis", "topik", "pesan", "usulan_waktu", "metode", "lokasi_or_link"]
        widgets = {
            "pesan": forms.Textarea(attrs={"rows": 4}),
            "usulan_waktu": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class PengajuanBimbinganReviewForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PengajuanBimbingan
        fields = ["status", "jadwal_disetujui", "metode", "lokasi_or_link", "rejected_reason"]
        widgets = {
            "jadwal_disetujui": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "rejected_reason": forms.Textarea(attrs={"rows": 3}),
        }


class CatatanBimbinganForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = CatatanBimbingan
        fields = ["tanggal_pertemuan", "ringkasan", "tindak_lanjut", "lampiran"]
        widgets = {
            "tanggal_pertemuan": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ringkasan": forms.Textarea(attrs={"rows": 4}),
            "tindak_lanjut": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_tanggal_pertemuan(self):
        val = self.cleaned_data["tanggal_pertemuan"]
        # normalisasi jika user input kosong -> now
        return val or timezone.now()


# --- Portofolio ---
class MataKuliahForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = MataKuliah
        fields = ["kode", "nama", "prodi", "semester"]


class KelasKuliahForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = KelasKuliah
        fields = ["mata_kuliah", "tahun_ajaran", "nama_kelas", "dosen_pengampu"]
        widgets = {"dosen_pengampu": forms.SelectMultiple(attrs={"class": "form-select"})}


class LuaranMataKuliahForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = LuaranMataKuliah
        fields = ["kelas", "judul", "deskripsi", "deadline", "allowed_ext"]
        widgets = {
            "deskripsi": forms.Textarea(attrs={"rows": 4}),
            "deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class SubmissionLuaranForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = SubmissionLuaran
        fields = ["file_karya", "catatan_mahasiswa"]
        widgets = {"catatan_mahasiswa": forms.Textarea(attrs={"rows": 3})}


class SubmissionReviewForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = SubmissionLuaran
        fields = ["status", "feedback_dosen"]
        widgets = {"feedback_dosen": forms.Textarea(attrs={"rows": 4})}


# --- Akreditasi ---
class DokumenTriDharmaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = DokumenTriDharma
        fields = [
            "kategori",
            "tahun",
            "semester",
            "judul",
            "deskripsi",
            "jenis_bukti",
            "kode_standar",
            "kata_kunci",
            "file_bukti",
            "tautan",
            "status",
        ]
        widgets = {"deskripsi": forms.Textarea(attrs={"rows": 4})}


class DokumenTriDharmaReviewForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = DokumenTriDharma
        fields = ["status", "rejected_reason"]
        widgets = {"rejected_reason": forms.Textarea(attrs={"rows": 3})}


class DosenProfileForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = DosenProfile
        fields = ["nama", "nidn", "jabatan", "prodi", "fakultas", "email", "telepon"]


class MahasiswaProfileForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = MahasiswaProfile
        fields = ["nama", "nim", "prodi", "angkatan", "email"]