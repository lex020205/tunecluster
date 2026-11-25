# TuneCluster

![TuneCluster logo](assets/logo.png)

**Temukan playlist Spotify yang sesuai dengan aktivitas, mood, dan genre favorit Anda.**

TuneCluster adalah aplikasi rekomendasi musik berbasis clustering. Aplikasi menggunakan
fitur audio lagu untuk mencari rekomendasi yang dekat dengan suasana yang dipilih, lalu
menampilkan lagu beserta tautan dan pemutar Spotify.

> **Demo:** [TuneCluster di Streamlit Community Cloud](https://your-app-name.streamlit.app)  
> Ganti URL di atas dengan URL aplikasi setelah deployment selesai.
>
> **Source code:** [github.com/lex020205/tunecluster](https://github.com/lex020205/tunecluster)

## Screenshot

Tambahkan screenshot aplikasi pada `assets/screenshot.png`, lalu ganti placeholder ini:

<!-- TODO: Tambahkan screenshot halaman rekomendasi di sini. -->

## Fitur utama

- Rekomendasi playlist berdasarkan aktivitas, mood, dan genre favorit.
- Pilihan model clustering K-Means dan BIRCH.
- Profil pengguna, pengelolaan genre favorit, dan riwayat playlist.
- Halaman analisis berisi metrik evaluasi dan visualisasi interaktif.
- Pemutar Spotify tertanam dan tautan pencarian lagu.

## Tech stack

- Python dan Streamlit
- pandas, NumPy, scikit-learn, dan joblib
- Plotly, Matplotlib, dan Seaborn
- SQLite untuk akun pengguna dan riwayat

## Menjalankan secara lokal

Disarankan memakai Python stabil yang didukung Streamlit Community Cloud.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Database SQLite dibuat otomatis di `data/tunecluster_users.db` saat aplikasi pertama kali
dijalankan. File database ini bersifat lokal dan tidak dimasukkan ke repository.

## Deploy ke Streamlit Community Cloud

1. Push repository ini ke GitHub.
2. Buka [share.streamlit.io](https://share.streamlit.io/) dan hubungkan akun GitHub.
3. Pilih repository, branch `main`, dan file utama `app.py`.
4. Deploy aplikasi.

## Kredit dan lisensi

Dikembangkan oleh **Tim TuneCluster**. Aplikasi menggunakan dataset lagu Spotify dan
artefak model yang disertakan dalam repository. Pastikan hak penggunaan dataset dan
artefak tersebut sesuai dengan ketentuan sumbernya.

Lisensi project belum ditetapkan. Tambahkan file `LICENSE` setelah lisensi dipilih.
