from django.urls import path
from . import views

app_name = "dosen"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("profil/", views.profil_saya, name="profil_saya"),
    path("ganti-password-awal/", views.force_change_password, name="force_change_password"),
    path("logout/", views.logout_view, name="logout_view"),

    # 1) Bimbingan
    path("bimbingan/", views.PengajuanBimbinganListView.as_view(), name="bimbingan_list"),
    path("bimbingan/tambah/", views.PengajuanBimbinganCreateView.as_view(), name="bimbingan_create"),
    path("bimbingan/<int:pk>/", views.PengajuanBimbinganDetailView.as_view(), name="bimbingan_detail"),
    path("bimbingan/<int:pk>/review/", views.pengajuan_review, name="bimbingan_review"),
    path("bimbingan/<int:pk>/catatan/tambah/", views.catatan_tambah, name="catatan_tambah"),

    path("bimbingan/<int:pk>/chat/messages/", views.chat_messages, name="chat_messages"),
    path("bimbingan/<int:pk>/chat/send/", views.chat_send, name="chat_send"),

    # 2) Portofolio
    path("portofolio/mk/", views.MataKuliahListView.as_view(), name="mk_list"),
    path("portofolio/mk/tambah/", views.MataKuliahCreateView.as_view(), name="mk_create"),
    path("portofolio/kelas/", views.KelasKuliahListView.as_view(), name="kelas_list"),
    path("portofolio/kelas/tambah/", views.KelasKuliahCreateView.as_view(), name="kelas_create"),

    path("portofolio/luaran/", views.LuaranListView.as_view(), name="luaran_list"),
    path("portofolio/luaran/tambah/", views.LuaranCreateView.as_view(), name="luaran_create"),
    path("portofolio/luaran/<int:pk>/", views.LuaranDetailView.as_view(), name="luaran_detail"),
    path("portofolio/luaran/<int:pk>/submit/", views.submission_submit, name="submission_submit"),

    path("portofolio/submission/<int:pk>/", views.SubmissionDetailView.as_view(), name="submission_detail"),
    path("portofolio/submission/<int:pk>/review/", views.submission_review, name="submission_review"),

    # 3) Akreditasi
    path("akreditasi/", views.DokumenTriDharmaListView.as_view(), name="akreditasi_list"),
    path("akreditasi/tambah/", views.DokumenTriDharmaCreateView.as_view(), name="akreditasi_create"),
    path("akreditasi/<int:pk>/", views.DokumenTriDharmaDetailView.as_view(), name="akreditasi_detail"),
    path("akreditasi/<int:pk>/review/", views.akreditasi_review, name="akreditasi_review"),
]
