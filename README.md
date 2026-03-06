# Dosen Digital (Django)

Aplikasi web untuk tupoksi dosen:
1) Pengajuan Bimbingan & Log Catatan Bimbingan (PA / Skripsi)
2) Portofolio Tugas Mahasiswa / Luaran Mata Kuliah (upload + feedback + approval)
3) Dokumen Tri Dharma untuk akreditasi/audit (metadata + verifikasi admin)

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Catatan Role
- User dianggap Dosen jika punya `profil_dosen`
- User dianggap Mahasiswa jika punya `profil_mahasiswa`

Buat profil via Admin Panel:
- Dosen Profile
- Mahasiswa Profile
