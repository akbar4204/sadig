from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html
from .models import NilaiMataKuliah

from .models import (
    AuditLog,
    CatatanBimbingan,
    DokumenTriDharma,
    DosenProfile,
    EnrollmentKelas,
    KelasKuliah,
    LuaranMataKuliah,
    MahasiswaProfile,
    MataKuliah,
    PengajuanBimbingan,
    SubmissionLuaran,
    ChatThreadBimbingan,
    ChatMessageBimbingan,
)


@admin.register(DosenProfile)
class DosenAdmin(admin.ModelAdmin):
    list_display = ("nama", "nidn", "jabatan", "prodi", "email")
    search_fields = ("nama", "nidn", "jabatan", "prodi", "email")
    list_filter = ("prodi", "fakultas")
    autocomplete_fields = ("user",)


@admin.register(MahasiswaProfile)
class MahasiswaAdmin(admin.ModelAdmin):
    list_display = ("nama", "nim", "prodi", "angkatan", "email")
    search_fields = ("nama", "nim", "prodi", "email")
    list_filter = ("prodi", "angkatan")
    autocomplete_fields = ("user",)


@admin.register(EnrollmentKelas)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("kelas", "mahasiswa", "is_active", "created_at")
    search_fields = ("kelas__mata_kuliah__kode", "kelas__nama_kelas", "mahasiswa__nama", "mahasiswa__nim")
    list_filter = ("is_active", "kelas__tahun_ajaran", "kelas__mata_kuliah__prodi")
    autocomplete_fields = ("kelas", "mahasiswa")


@admin.register(NilaiMataKuliah)
class NilaiMataKuliahAdmin(admin.ModelAdmin):
    list_display = ("mahasiswa", "mata_kuliah", "tahun_ajaran", "semester", "nilai", "sks_snapshot")
    search_fields = ("mahasiswa__nama", "mahasiswa__nim", "mata_kuliah__kode", "mata_kuliah__nama")
    list_filter = ("tahun_ajaran", "semester", "nilai")
    autocomplete_fields = ("mahasiswa", "mata_kuliah")


@admin.register(ChatThreadBimbingan)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ("pengajuan", "created_at", "updated_at")
    search_fields = ("pengajuan__mahasiswa__nama", "pengajuan__mahasiswa__nim", "pengajuan__dosen_pembimbing__nama")
    autocomplete_fields = ("pengajuan",)


@admin.register(ChatMessageBimbingan)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "sender", "created_at", "has_attachment")
    search_fields = ("message", "sender__username", "thread__pengajuan__mahasiswa__nim")
    list_filter = ("created_at",)
    autocomplete_fields = ("thread", "sender")
    readonly_fields = ("file_checksum", "created_at", "updated_at")

    def has_attachment(self, obj):
        return bool(getattr(obj, "attachment", None))
    has_attachment.short_description = "Lampiran"


class CatatanInline(admin.TabularInline):
    model = CatatanBimbingan
    extra = 0
    fields = ("tanggal_pertemuan", "ringkasan", "tindak_lanjut", "lampiran", "file_checksum", "dibuat_oleh")
    readonly_fields = ("file_checksum",)
    show_change_link = True


@admin.register(PengajuanBimbingan)
class PengajuanBimbinganAdmin(admin.ModelAdmin):
    list_display = ("jenis", "mahasiswa", "dosen_pembimbing", "status", "usulan_waktu", "jadwal_disetujui")
    search_fields = ("mahasiswa__nama", "mahasiswa__nim", "dosen_pembimbing__nama", "topik", "pesan")
    list_filter = ("jenis", "status")
    autocomplete_fields = ("mahasiswa", "dosen_pembimbing")
    inlines = [CatatanInline]
    readonly_fields = ("token", "created_at", "updated_at")


@admin.register(CatatanBimbingan)
class CatatanBimbinganAdmin(admin.ModelAdmin):
    list_display = ("pengajuan", "tanggal_pertemuan", "dibuat_oleh", "lampiran", "file_checksum")
    search_fields = ("pengajuan__mahasiswa__nama", "pengajuan__mahasiswa__nim", "ringkasan", "tindak_lanjut")
    list_filter = ("tanggal_pertemuan",)
    autocomplete_fields = ("pengajuan",)
    readonly_fields = ("file_checksum", "created_at", "updated_at")


@admin.register(MataKuliah)
class MataKuliahAdmin(admin.ModelAdmin):
    list_display = ("kode", "nama", "prodi", "semester")
    search_fields = ("kode", "nama", "prodi", "semester")
    list_filter = ("prodi", "semester")


@admin.register(KelasKuliah)
class KelasKuliahAdmin(admin.ModelAdmin):
    list_display = ("mata_kuliah", "tahun_ajaran", "nama_kelas")
    search_fields = ("mata_kuliah__kode", "mata_kuliah__nama", "tahun_ajaran", "nama_kelas")
    list_filter = ("tahun_ajaran", "mata_kuliah__prodi")
    autocomplete_fields = ("mata_kuliah",)
    filter_horizontal = ("dosen_pengampu",)


@admin.register(LuaranMataKuliah)
class LuaranAdmin(admin.ModelAdmin):
    list_display = ("judul", "kelas", "deadline")
    search_fields = ("judul", "kelas__mata_kuliah__kode", "kelas__mata_kuliah__nama", "kelas__tahun_ajaran", "kelas__nama_kelas")
    list_filter = ("kelas__tahun_ajaran", "kelas__mata_kuliah__prodi")
    autocomplete_fields = ("kelas",)


@admin.register(SubmissionLuaran)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("luaran", "mahasiswa", "status", "reviewed_at", "file_link")
    search_fields = ("luaran__judul", "mahasiswa__nama", "mahasiswa__nim", "feedback_dosen")
    list_filter = ("status", "reviewed_at")
    autocomplete_fields = ("luaran", "mahasiswa")
    readonly_fields = ("file_checksum", "created_at", "updated_at")

    def file_link(self, obj: SubmissionLuaran):
        if not obj.file_karya:
            return "-"
        return format_html('<a href="{}" target="_blank">Buka File</a>', obj.file_karya.url)
    file_link.short_description = "File"


@admin.register(DokumenTriDharma)
class DokumenTriDharmaAdmin(admin.ModelAdmin):
    list_display = ("judul", "dosen", "kategori", "tahun", "semester", "status", "file_link")
    search_fields = ("judul", "dosen__nama", "jenis_bukti", "kode_standar", "kata_kunci")
    list_filter = ("kategori", "tahun", "semester", "status")
    autocomplete_fields = ("dosen",)
    readonly_fields = ("file_checksum", "created_at", "updated_at")

    def file_link(self, obj: DokumenTriDharma):
        if not obj.file_bukti:
            return "-"
        return format_html('<a href="{}" target="_blank">Buka File</a>', obj.file_bukti.url)
    file_link.short_description = "File"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "model", "object_id", "object_repr")
    list_filter = ("action", "model", "created_at")
    search_fields = ("object_repr", "object_id", "model", "user__username")
    readonly_fields = ("created_at", "user", "action", "model", "object_id", "object_repr", "changes")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.site_header = "Dosen Digital"
admin.site.site_title = "Dosen Digital Admin"
admin.site.index_title = "Dashboard Admin"
