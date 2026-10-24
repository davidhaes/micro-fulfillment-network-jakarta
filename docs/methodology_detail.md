# Methodology Detail

Dokumen ini menjelaskan metodologi teknis project untuk reviewer domestik.

* AOI dibuat dari GADM 4.1 level 2, bukan shapefile user.
* Raster diproses di Google Earth Engine, lalu hasil preprocessed disimpan lokal.
* CRS analitis adalah EPSG:32748 karena Jakarta berada di UTM zone 48S dan analisis jarak membutuhkan satuan meter.
* Demand quick commerce diperlakukan sebagai latent proxy, bukan order aktual.
* Demand index menggabungkan populasi, nighttime lights, built-up probability, road length, dan commercial POI count.
* Kandidat MFC berasal dari high-demand cells dan OSM commercial POIs.
* Optimasi lokasi memakai p-median greedy deterministic agar stabil dan reproducible di mesin lokal.
* Jarak rute didekati dengan corrected Euclidean distance memakai detour factor 1.35.
* Coverage 30 menit memakai asumsi kecepatan default dari file konfigurasi.
* Emisi dihitung per 100.000 proxy deliveries agar tidak mengklaim volume transaksi aktual.
* Spatial clustering diuji dengan Global Moran's I dan Local Moran's I.
* Validasi dilakukan sebagai sanity check administratif, bukan validasi order platform.
