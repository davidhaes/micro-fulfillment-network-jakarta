# Conclusions

## Answer to Research Questions

1. Jumlah minimum MFC yang mencapai target 90 persen coverage adalah 30 jika skenario tersebut mencapai 90 persen. Coverage skenario referensi adalah 76.3%. Jika nilai ini di bawah 90 persen, maka seluruh skenario yang diuji belum memenuhi target dan 30 adalah konfigurasi coverage terbaik pada rentang p yang diuji.

2. Area underserved prioritas terbesar berada pada unit administratif dengan mean underserved score tertinggi. Lima unit teratas adalah:
* Tangerang: mean underserved score 0.4012, high-high underserved cells 675.
* Bekasi: mean underserved score 0.3497, high-high underserved cells 522.
* Bogor: mean underserved score 0.2757, high-high underserved cells 737.
* TangerangSelatan: mean underserved score 0.1299, high-high underserved cells 25.
* Depok: mean underserved score 0.0145, high-high underserved cells 3.

3. Skenario terbaik yang diuji menurunkan demand-weighted distance sebesar 77.0% dibanding centralized baseline. Baseline distance adalah 3,190,161.7 km per 100.000 proxy deliveries, sedangkan skenario terbaik adalah 734,869.6 km.

4. Pengurangan CO2e tertinggi adalah 92.7% pada 30 MFC dan 100 persen EV adoption. Pada skenario referensi dengan 50 persen EV adoption, pengurangan CO2e adalah 84.8%.

5. Demand index menunjukkan Moran's I sebesar 0.944 dengan p-value 0.001. Underserved score menunjukkan Moran's I sebesar 0.870 dengan p-value 0.001. Nilai ini menunjukkan apakah hotspot demand dan underserved area membentuk pola spasial yang signifikan, bukan hanya titik ekstrem individual.

## Top 5 Findings

* Optimasi lokasi MFC menghasilkan penurunan jarak maksimum sebesar 77.0% pada rentang skenario yang diuji. Implikasinya, desain jaringan lebih menentukan efisiensi spasial daripada hanya mempercepat rider pada jaringan yang sama.

* Skenario referensi 30 MFC memberi coverage 76.3% dalam SLA 30 menit. Jika nilai ini belum mencapai 90 persen, maka operator perlu menaikkan jumlah MFC di atas rentang yang diuji atau menambah strategi hybrid seperti pop-up fulfillment dan rider staging.

* Kombinasi spatial optimization dan EV adoption menghasilkan pengurangan emisi tertinggi sebesar 92.7%. Ini menunjukkan decarbonization tidak cukup hanya mengganti kendaraan, karena jarak fulfillment tetap menentukan beban energi.

* Sebanyak 70 persen demand proxy terkonsentrasi pada sekitar 48.3% area grid. Status H2: tidak terdukung. Jika area share rendah, strategi MFC perlu fokus pada cluster, bukan penyebaran merata.

* Spatial autocorrelation underserved score menunjukkan Moran's I 0.870. Jika signifikan, rekomendasi lokasi harus berbasis cluster contiguous, bukan daftar cell ranking individual.

## Hypothesis Evaluation

* H1, distributed MFC network reduces distance by at least 20 percent: terdukung. Nilai terbaik yang diuji adalah 77.0%.

* H2, at least 70 percent of demand proxy is concentrated within less than 40 percent of grid area: tidak terdukung. Area share untuk 70 persen demand proxy adalah 48.3%.

* H3, optimized MFC plus 50 percent EV adoption reduces CO2e by at least 30 percent: terdukung. Nilai skenario referensi EV 50 persen adalah 84.8%.

## Spatial Pattern Summary

Demand proxy tidak menyebar merata. Cell bernilai tinggi muncul pada kombinasi populasi tinggi, nighttime lights kuat, built-up intensity, akses jalan, dan POI komersial. Underserved hotspots paling penting adalah area demand tinggi yang masih berada di luar cakupan 30 menit dalam skenario referensi.

## Temporal Pattern Summary

Konteks temporal nighttime lights 2020 sampai 2024 menunjukkan Sen's slope VIIRS sebesar 0.531 avg_rad per tahun dengan Kendall p-value 0.817. Angka ini harus dibaca sebagai perubahan aktivitas malam metropolitan, bukan pertumbuhan order q-commerce aktual.

## Surprises and Counter-Intuitive Findings

* Area dengan populasi tinggi tidak selalu menjadi kandidat MFC tertinggi jika POI komersial dan akses jalan rendah. Ini menjelaskan mengapa demand proxy berbeda dari peta kepadatan penduduk murni.

* EV adoption memberi dampak kuat, tetapi skenario EV tanpa pengurangan jarak tetap membawa penalti grid electricity. Karena itu network design dan electrification harus dipaketkan.

* Jika coverage tidak mencapai 90 persen pada p=30, masalah utamanya bukan hanya jumlah fasilitas, tetapi bentuk metropolitan, detour factor, dan konsentrasi demand di koridor yang tidak selalu mudah dijangkau.

## Limitations

* Demand quick commerce aktual tidak tersedia sebagai open data. Semua hasil demand adalah latent proxy.

* Corrected Euclidean distance dengan detour factor 1.35 digunakan sebagai approximation. Travel time aktual memerlukan time-dependent routing dan data congestion proprietary.

* Emission factors bersifat scenario assumption berbasis literature-style accounting. Hasil bukan inventaris emisi perusahaan aktual.

* OSM POI completeness dapat bervariasi antar wilayah. Area dengan kontribusi OSM rendah bisa underrepresented dalam POI density score.

* Analisis belum memasukkan biaya sewa, kapasitas gudang, inventory duplication, rider shift schedule, dan time-window order batching.
