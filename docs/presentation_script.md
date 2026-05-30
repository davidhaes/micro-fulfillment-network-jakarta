## Opening

Project ini menjawab satu pertanyaan operasional: jika quick commerce ingin mempertahankan SLA 30 menit di Greater Jakarta, di mana micro-fulfillment center sebaiknya ditempatkan agar jarak last-mile dan CO2e turun?

Saya tidak memakai data order proprietary. Demand yang saya gunakan adalah latent quick-commerce demand proxy dari open data, yaitu WorldPop, VIIRS nighttime lights, Dynamic World built probability, OpenStreetMap road accessibility, dan commercial POI density. Tujuannya adalah membangun decision-support framework yang reproducible, bukan mengklaim volume transaksi aktual.

## Problem

Quick commerce berbeda dari e-commerce biasa karena service level sangat pendek. Jika fulfillment terlalu jauh dari demand, operator membayar biaya dalam bentuk jarak rider, waktu tempuh, energi, dan emisi. Centralized fulfillment lebih sederhana secara inventory, tetapi sering membuat last-mile lebih panjang. Distributed micro-fulfillment bisa memangkas jarak, tetapi menambah biaya fixed asset dan inventory complexity.

Karena itu project ini mengukur trade-off spasial: berapa banyak MFC yang dibutuhkan, seberapa besar coverage 30 menit, berapa penurunan jarak, dan bagaimana dampaknya terhadap CO2e ketika fleet mulai beralih ke electric motorcycle.

## Data

AOI dibuat dari GADM 4.1 level 2, bukan shapefile manual. Raster diproses melalui Google Earth Engine Python API, lalu hasil preprocessed diunduh lokal. WorldPop dipakai sebagai population base. VIIRS nighttime lights dipakai sebagai economic activity proxy. Dynamic World built probability dipakai sebagai urban intensity proxy. OpenStreetMap dipakai untuk road accessibility dan commercial POI density.

Semua data disimpan dengan metadata JSON, termasuk source URL, license, temporal coverage, CRS, unit, preprocessing steps, dan citation. CRS analitis adalah EPSG:32748 karena Jakarta berada di UTM zone 48S dan analisis jarak membutuhkan satuan meter.

## Method

Demand index dibangun sebagai weighted overlay. Population score diberi bobot 40 persen, nighttime lights 25 persen, built-up intensity 15 persen, road accessibility 10 persen, dan POI density 10 persen. Variabel skewed seperti populasi, nighttime lights, road length, dan POI count ditransformasi log1p lalu diskalakan ke 0 sampai 1.

Kandidat MFC dibuat dari high-demand cells dan OSM commercial POIs. Optimasi memakai p-median karena objective utamanya adalah meminimalkan demand-weighted distance. Saya menguji beberapa jumlah MFC, yaitu 5, 10, 15, 20, 25, dan 30. Coverage 30 menit dihitung dari speed assumption dan corrected Euclidean distance dengan detour factor 1.35.

Emisi dihitung per 100.000 proxy deliveries. Motor bensin dihitung dari distance dikali emission factor per km. Motor listrik dihitung dari distance dikali kWh per km dan grid emission factor. Ini membuat EV tidak dianggap zero emission dalam grid-based accounting.

Spatial statistics memakai Global Moran's I dan LISA untuk melihat apakah demand dan underserved area benar-benar clustered, bukan hanya tinggi secara individual.

## Results

Bagian ini harus Anda isi dengan angka final dari file `outputs/reports/executive_summary.md`.

Sampaikan lima angka:

* Jumlah MFC referensi.
* Coverage share.
* Distance reduction maksimum.
* Emission reduction maksimum.
* Top underserved administrative unit.

Contoh struktur penyampaian:

Skenario referensi memilih [X] MFC dan mencakup [Y] persen proxy demand dalam SLA 30 menit. Skenario terbaik menurunkan demand-weighted distance sebesar [Z] persen dibanding centralized baseline. Kombinasi MFC optimization dan EV adoption terbaik menurunkan CO2e sebesar [A] persen per 100.000 proxy deliveries. Area dengan underserved score tertinggi adalah [B], sehingga pilot intervention sebaiknya dimulai dari cluster tersebut.

## Implications

Insight paling penting adalah decarbonization last-mile bukan hanya vehicle technology problem. Lokasi stok dan desain jaringan fulfillment menentukan jarak. EV adoption paling efektif ketika fulfillment sudah ditempatkan lebih dekat ke demand.

Untuk operator, framework ini bisa dipakai sebagai pre-screening expansion planning. Untuk ESG team, framework ini memisahkan efek distance reduction dan fleet electrification. Untuk policymaker, output hotspot bisa dipakai untuk merancang low-emission logistics zone, charging location, dan loading regulation.

## Limitations
Limitasi utama adalah tidak adanya data order aktual dan travel time aktual. Karena itu demand dibaca sebagai proxy. Distance juga masih approximation, bukan time-dependent routing. Emission result adalah scenario-based per 100.000 proxy deliveries, bukan inventaris perusahaan. Keputusan real estate final tetap perlu data sewa, kapasitas, loading access, inventory cost, dan data operasional internal.

## Closing

Project ini menunjukkan bagaimana open geospatial data, optimization, spatial statistics, dan emission scenario modeling dapat digabungkan menjadi reproducible decision-support framework untuk urban logistics decarbonization di megacity.
