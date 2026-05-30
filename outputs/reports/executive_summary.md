# Executive Summary

Greater Jakarta adalah pasar metropolitan yang menuntut pengiriman cepat, tetapi quick commerce menghadapi trade-off antara SLA 30 menit, biaya last-mile, dan emisi operasional. Project ini membangun framework open-data untuk menguji apakah desain jaringan micro-fulfillment center dapat mengurangi jarak tempuh dan CO2e tanpa mengklaim order aktual platform. Demand yang dianalisis adalah latent quick-commerce demand proxy dari populasi, nighttime lights, built-up intensity, road accessibility, dan commercial POI density.

Metode utama mencakup pembuatan AOI dari GADM 4.1, preprocessing raster melalui Google Earth Engine, pembangunan grid demand 1 km, candidate MFC screening dari OSM POI dan high-demand cells, p-median optimization, 30-minute service coverage, spatial autocorrelation, dan emission scenario analysis. Emisi dihitung per 100.000 proxy deliveries agar hasil dapat dibandingkan tanpa membutuhkan data transaksi proprietary.

Temuan kunci:

* Skenario referensi memilih 30 MFC dengan coverage 76.3% terhadap proxy demand dalam SLA 30 menit.

* Skenario terbaik menurunkan demand-weighted distance sebesar 77.0% dibanding centralized baseline.

* Pengurangan CO2e tertinggi mencapai 92.7% pada 30 MFC dan 100 persen EV adoption.

* Sebanyak 70 persen demand proxy terkonsentrasi pada sekitar 48.3% area grid, sehingga expansion planning harus berbasis cluster, bukan pemerataan fasilitas.

* Underserved score memiliki Moran's I 0.870 dengan p-value 0.001, yang menunjukkan apakah gap service membentuk cluster spasial signifikan.

Rekomendasi prioritas tinggi:

* Prioritaskan MFC pada underserved High-High LISA clusters untuk menaikkan coverage dan menurunkan p90 nearest-MFC distance.

* Paketkan MFC optimization dengan EV adoption karena electrification paling efektif ketika jarak fulfillment sudah dipersingkat.

* Jalankan sensitivity review sebelum capex real estate dengan skenario speed 15 km/h, bobot demand alternatif, dan grid 1500 m.

Reproducibility: seluruh pipeline dapat dijalankan dari repository dengan satu perintah setelah environment dan credential Google Earth Engine disiapkan.
