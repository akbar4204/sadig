from __future__ import annotations

import hashlib
import logging
import uuid

from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


logger = logging.getLogger(__name__)
User = get_user_model()


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class DosenProfile(TimeStampedModel):
    """Profil dosen (terkait user)."""

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profil_dosen",
    )
    nama = models.CharField(max_length=120)
    nidn = models.CharField(max_length=50, unique=True)
    jabatan = models.CharField(max_length=120, blank=True)
    prodi = models.CharField(max_length=120, blank=True)
    fakultas = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    telepon = models.CharField(max_length=30, blank=True)
    must_change_password = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.nama

    class Meta:
        verbose_name_plural = "Dosen"
        ordering = ["nama"]
        indexes = [
            models.Index(fields=["nidn"]),
            models.Index(fields=["nama"]),
            models.Index(fields=["prodi"]),
        ]


class MahasiswaProfile(TimeStampedModel):
    """Profil mahasiswa (terkait user)."""

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profil_mahasiswa",
    )
    nama = models.CharField(max_length=120)
    nim = models.CharField(max_length=50, unique=True)
    prodi = models.CharField(max_length=120, blank=True)
    angkatan = models.PositiveIntegerField(null=True, blank=True)
    email = models.EmailField(blank=True)
    must_change_password = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.nama} ({self.nim})"

    class Meta:
        verbose_name_plural = "Mahasiswa"
        ordering = ["nama"]
        indexes = [
            models.Index(fields=["nim"]),
            models.Index(fields=["nama"]),
            models.Index(fields=["prodi"]),
        ]


class IntegrityFileMixin(models.Model):
    """Mixin untuk menyimpan checksum file upload (audit/akreditasi)."""

    file_checksum = models.CharField(max_length=64, blank=True, editable=False, db_index=True)

    class Meta:
        abstract = True

    def update_checksum_if_possible(self, file_field_name: str) -> None:
        f = getattr(self, file_field_name, None)
        if not f:
            return

        try:
            h = hashlib.sha256()
            f.open("rb")
            try:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            finally:
                f.close()

            self.file_checksum = h.hexdigest()
        except Exception:
            logger.exception("Gagal hitung checksum untuk %s", file_field_name)


# =========================================================
#  1) Digitalisasi Log Bimbingan (PA / Skripsi)
# =========================================================
class PengajuanBimbingan(TimeStampedModel):
    class Jenis(models.TextChoices):
        PA = "pa", "Bimbingan Akademik (Dosen PA)"
        SKRIPSI = "skripsi", "Bimbingan Skripsi"

    class Status(models.TextChoices):
        DIAJUKAN = "submitted", "Diajukan"
        DISETUJUI = "approved", "Disetujui / Dijadwalkan"
        DITOLAK = "rejected", "Ditolak"
        SELESAI = "done", "Selesai"
        DIBATALKAN = "canceled", "Dibatalkan"

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)

    mahasiswa = models.ForeignKey(MahasiswaProfile, on_delete=models.CASCADE, related_name="pengajuan_bimbingan")
    dosen_pembimbing = models.ForeignKey(DosenProfile, on_delete=models.CASCADE, related_name="pengajuan_masuk")

    jenis = models.CharField(max_length=20, choices=Jenis.choices, default=Jenis.PA)
    topik = models.CharField(max_length=200, blank=True)
    pesan = models.TextField(help_text="Jelaskan kebutuhan bimbingan / pertanyaan utama.")
    usulan_waktu = models.DateTimeField(null=True, blank=True, help_text="Usulan jadwal dari mahasiswa (opsional).")

    # penjadwalan final
    jadwal_disetujui = models.DateTimeField(null=True, blank=True, help_text="Jadwal bimbingan yang disepakati.")
    metode = models.CharField(
        max_length=20,
        choices=[("offline", "Tatap Muka"), ("online", "Online")],
        default="offline",
    )
    lokasi_or_link = models.CharField(max_length=200, blank=True, help_text="Ruang kelas/gedung atau link meeting.")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DIAJUKAN, db_index=True)
    rejected_reason = models.TextField(blank=True)

    dibuat_oleh = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pengajuan_bimbingan_dibuat",
    )

    def __str__(self) -> str:
        return f"{self.get_jenis_display()} • {self.mahasiswa} -> {self.dosen_pembimbing}"

    class Meta:
        verbose_name_plural = "Pengajuan Bimbingan"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["jenis"]),
        ]


class CatatanBimbingan(TimeStampedModel, IntegrityFileMixin):
    pengajuan = models.ForeignKey(PengajuanBimbingan, on_delete=models.CASCADE, related_name="catatan")
    tanggal_pertemuan = models.DateTimeField(default=timezone.now, db_index=True)
    ringkasan = models.TextField(help_text="Ringkasan diskusi / hasil bimbingan.")
    tindak_lanjut = models.TextField(blank=True, help_text="Action items / tugas lanjutan.")
    lampiran = models.FileField(
        upload_to="bimbingan/lampiran/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["pdf", "png", "jpg", "jpeg", "doc", "docx"])],
    )
    dibuat_oleh = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="catatan_bimbingan_dibuat",
    )

    def __str__(self) -> str:
        return f"Catatan {self.pengajuan_id} @ {self.tanggal_pertemuan:%Y-%m-%d}"

    class Meta:
        verbose_name_plural = "Log Catatan Bimbingan"
        ordering = ["-tanggal_pertemuan"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        old_checksum = self.file_checksum
        self.update_checksum_if_possible("lampiran")

        if self.file_checksum != old_checksum:
            super().save(update_fields=["file_checksum"])


# =========================================================
#  1b) Live Chat Bimbingan (per Pengajuan)
# =========================================================
class ChatThreadBimbingan(TimeStampedModel):
    """1 thread chat per pengajuan bimbingan."""

    pengajuan = models.OneToOneField(
        PengajuanBimbingan,
        on_delete=models.CASCADE,
        related_name="chat_thread",
    )

    def __str__(self) -> str:
        return f"Thread Pengajuan #{self.pengajuan_id}"

    class Meta:
        verbose_name_plural = "Thread Chat Bimbingan"


class ChatMessageBimbingan(TimeStampedModel, IntegrityFileMixin):
    thread = models.ForeignKey(
        ChatThreadBimbingan,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_bimbingan_sent",
    )
    message = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="bimbingan/chat/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["pdf", "png", "jpg", "jpeg", "doc", "docx", "ppt", "pptx", "zip", "rar"])],
    )

    def __str__(self) -> str:
        return f"Msg #{self.pk} by {self.sender_id}"

    class Meta:
        verbose_name_plural = "Chat Message Bimbingan"
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        old_checksum = self.file_checksum
        self.update_checksum_if_possible("attachment")

        if self.file_checksum != old_checksum:
            super().save(update_fields=["file_checksum"])


# =========================================================
#  2) Portofolio Tugas Mahasiswa / Luaran Mata Kuliah
# =========================================================
class MataKuliah(TimeStampedModel):
    kode = models.CharField(max_length=30, db_index=True)
    nama = models.CharField(max_length=200)
    prodi = models.CharField(max_length=120, blank=True)
    semester = models.CharField(max_length=20, blank=True)
    sks = models.PositiveSmallIntegerField(default=2)

    def __str__(self) -> str:
        return f"{self.kode} - {self.nama}"

    class Meta:
        verbose_name_plural = "Mata Kuliah"
        ordering = ["kode"]
        unique_together = [("kode", "prodi")]


class KelasKuliah(TimeStampedModel):
    mata_kuliah = models.ForeignKey(MataKuliah, on_delete=models.CASCADE, related_name="kelas")
    tahun_ajaran = models.CharField(max_length=30, help_text="Contoh: 2025/2026")
    nama_kelas = models.CharField(max_length=50, help_text="Contoh: A / B / Reg / Ekstensi")
    dosen_pengampu = models.ManyToManyField(DosenProfile, related_name="kelas_diampu")

    def __str__(self) -> str:
        return f"{self.mata_kuliah.kode} {self.nama_kelas} ({self.tahun_ajaran})"

    class Meta:
        verbose_name_plural = "Kelas Kuliah"
        ordering = ["-tahun_ajaran", "mata_kuliah__kode", "nama_kelas"]


class EnrollmentKelas(TimeStampedModel):
    """Mahasiswa yang terdaftar pada kelas (pengganti KRS eksternal)."""

    kelas = models.ForeignKey(KelasKuliah, on_delete=models.CASCADE, related_name="enrollments")
    mahasiswa = models.ForeignKey(MahasiswaProfile, on_delete=models.CASCADE, related_name="enrollments")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Peserta Kelas"
        unique_together = [("kelas", "mahasiswa")]
        indexes = [
            models.Index(fields=["kelas", "is_active"]),
            models.Index(fields=["mahasiswa", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.mahasiswa} @ {self.kelas}"


class NilaiMataKuliah(TimeStampedModel):
    """Nilai resmi mahasiswa per mata kuliah (diimpor operator)."""

    class Semester(models.TextChoices):
        GANJIL = "ganjil", "Ganjil"
        GENAP = "genap", "Genap"

    class NilaiHuruf(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        D = "D", "D"
        E = "E", "E"

    mahasiswa = models.ForeignKey(MahasiswaProfile, on_delete=models.CASCADE, related_name="nilai")
    mata_kuliah = models.ForeignKey(MataKuliah, on_delete=models.CASCADE, related_name="nilai_mahasiswa")

    tahun_ajaran = models.CharField(max_length=30, db_index=True)  # contoh: 2025/2026
    semester = models.CharField(max_length=10, choices=Semester.choices, db_index=True)

    nilai = models.CharField(max_length=2, choices=NilaiHuruf.choices, db_index=True)

    # snapshot SKS untuk menjaga histori kalau SKS MK berubah
    sks_snapshot = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Nilai Mata Kuliah"
        unique_together = [("mahasiswa", "mata_kuliah", "tahun_ajaran", "semester")]
        indexes = [
            models.Index(fields=["tahun_ajaran", "semester"]),
            models.Index(fields=["nilai"]),
        ]

    def __str__(self):
        return f"{self.mahasiswa.nim} {self.mata_kuliah.kode} {self.tahun_ajaran}-{self.semester} = {self.nilai}"

    @property
    def bobot(self) -> float:
        # A=4, B=3, C=2, D=1, E=0
        return {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "E": 0.0}.get(self.nilai, 0.0)

    def save(self, *args, **kwargs):
        if not self.sks_snapshot:
            self.sks_snapshot = self.mata_kuliah.sks
        super().save(*args, **kwargs)

class LuaranMataKuliah(TimeStampedModel):
    """Tugas/luaran final yang harus diunggah mahasiswa."""

    kelas = models.ForeignKey(KelasKuliah, on_delete=models.CASCADE, related_name="luaran")
    judul = models.CharField(max_length=200)
    deskripsi = models.TextField(blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    allowed_ext = models.CharField(
        max_length=200,
        default="pdf,doc,docx,ppt,pptx,zip,rar",
        help_text="Daftar ekstensi yang diizinkan (dipisah koma).",
    )

    def __str__(self) -> str:
        return f"{self.kelas} • {self.judul}"

    class Meta:
        verbose_name_plural = "Luaran Mata Kuliah"
        ordering = ["-created_at"]


class SubmissionLuaran(TimeStampedModel, IntegrityFileMixin):
    class Status(models.TextChoices):
        DIKIRIM = "submitted", "Dikirim"
        REVISI = "revision", "Perlu Revisi"
        DISETUJUI = "approved", "Disetujui"
        DITOLAK = "rejected", "Ditolak"

    luaran = models.ForeignKey(LuaranMataKuliah, on_delete=models.CASCADE, related_name="submissions")
    mahasiswa = models.ForeignKey(MahasiswaProfile, on_delete=models.CASCADE, related_name="submissions")

    file_karya = models.FileField(
        upload_to="portofolio/submission/",
        validators=[FileExtensionValidator(["pdf", "doc", "docx", "ppt", "pptx", "zip", "rar"])],
    )
    catatan_mahasiswa = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DIKIRIM, db_index=True)

    feedback_dosen = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submission_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.mahasiswa} -> {self.luaran}"

    class Meta:
        verbose_name_plural = "Submission Luaran"
        ordering = ["-created_at"]
        unique_together = [("luaran", "mahasiswa")]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        old_checksum = self.file_checksum
        self.update_checksum_if_possible("file_karya")

        if self.file_checksum != old_checksum:
            super().save(update_fields=["file_checksum"])


# =========================================================
#  3) Dokumen Penunjang Akreditasi (Tri Dharma Dosen)
# =========================================================
class DokumenTriDharma(TimeStampedModel, IntegrityFileMixin):
    class Kategori(models.TextChoices):
        PENGAJARAN = "pengajaran", "Pengajaran"
        PENELITIAN = "penelitian", "Penelitian"
        PENGABDIAN = "pengabdian", "Pengabdian"
        PENUNJANG = "penunjang", "Penunjang"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        DIAJUKAN = "submitted", "Diajukan"
        TERVERIFIKASI = "verified", "Terverifikasi"
        DITOLAK = "rejected", "Ditolak"

    dosen = models.ForeignKey(DosenProfile, on_delete=models.CASCADE, related_name="dokumen_tridharma")
    kategori = models.CharField(max_length=20, choices=Kategori.choices, db_index=True)

    tahun = models.PositiveIntegerField(db_index=True)
    semester = models.CharField(
        max_length=10,
        choices=[("ganjil", "Ganjil"), ("genap", "Genap"), ("antara", "Antara")],
        default="ganjil",
        db_index=True,
    )

    judul = models.CharField(max_length=200)
    deskripsi = models.TextField(blank=True)

    jenis_bukti = models.CharField(
        max_length=120,
        help_text="Contoh: RPS, Kontrak Kuliah, Jurnal, Sertifikat, SK, Laporan",
    )
    kode_standar = models.CharField(
        max_length=50,
        blank=True,
        help_text="Opsional: kode/standar borang/indikator akreditasi.",
    )
    kata_kunci = models.CharField(
        max_length=250,
        blank=True,
        help_text="Pisahkan dengan koma. Contoh: rps, OBE, rubrik",
    )

    file_bukti = models.FileField(
        upload_to="akreditasi/dokumen/",
        validators=[FileExtensionValidator(["pdf", "doc", "docx", "ppt", "pptx", "png", "jpg", "jpeg", "zip"])],
    )
    tautan = models.URLField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    rejected_reason = models.TextField(blank=True)

    submitted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dokumen_tridharma_diajukan",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dokumen_tridharma_diverifikasi",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.get_kategori_display()} • {self.judul} ({self.tahun}-{self.semester})"

    class Meta:
        verbose_name_plural = "Dokumen Tri Dharma"
        ordering = ["-tahun", "-created_at"]
        indexes = [
            models.Index(fields=["tahun", "semester"]),
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        old_checksum = self.file_checksum
        self.update_checksum_if_possible("file_bukti")

        if self.file_checksum != old_checksum:
            super().save(update_fields=["file_checksum"])


# =========================================================
#  Audit Log (siapa ubah apa)
# =========================================================
class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=Action.choices, db_index=True)

    model = models.CharField(max_length=120, db_index=True)
    object_id = models.CharField(max_length=64, db_index=True)
    object_repr = models.CharField(max_length=255)
    changes = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Audit Log"
