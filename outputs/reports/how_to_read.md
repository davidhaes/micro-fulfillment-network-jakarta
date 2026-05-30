# Cara Membaca Metrik

Dokumen ini menjelaskan arti setiap metrik utama dalam project. Semua metrik demand adalah proxy berbasis open data, bukan volume order aktual platform quick commerce.

* Demand index
  * Unit: indeks 0 sampai 1.
  * Range interpretasi: nilai mendekati 1 menunjukkan kombinasi populasi, aktivitas malam, built-up intensity, akses jalan, dan POI komersial yang lebih kuat.
  * Threshold operasional: top quantile digunakan untuk membaca hotspot, bukan sebagai batas order aktual.
  * Referensi: WorldPop, VIIRS nighttime lights, Dynamic World, OpenStreetMap.
  * Contoh interpretasi: cell dengan demand index tinggi layak diuji sebagai area kandidat MFC atau area demand capture.

* Proxy deliveries per 100,000
  * Unit: distribusi demand index yang dinormalisasi menjadi 100.000 unit proxy.
  * Range interpretasi: jumlah ini tidak berarti 100.000 order aktual, tetapi basis komparatif antar skenario.
  * Threshold operasional: dipakai sebagai bobot p-median dan emisi agar jarak dapat dibandingkan konsisten.
  * Referensi: activity-based scenario modeling.
  * Contoh interpretasi: skenario dengan jarak 20 persen lebih rendah per 100.000 proxy deliveries lebih efisien secara spasial daripada baseline.

* Thirty-minute service coverage
  * Unit: persentase proxy demand yang tercakup.
  * Nilai skenario referensi: 76.3%.
  * Label interpretasi: Moderate.
  * Deskripsi: Coverage is operationally meaningful but below the 90 percent target.
  * Rekomendasi: Add MFCs in underserved high-demand clusters before scaling fleet electrification.
  * Referensi: Quick commerce service-level convention is represented by a 30-minute delivery threshold; threshold is treated as an operational scenario assumption.

* Demand-weighted distance
  * Unit: kilometer per 100.000 proxy deliveries.
  * Baseline: 3,190,161.7 km.
  * Skenario referensi: 734,869.6 km.
  * Threshold hipotesis: H1 menguji minimal 20 persen penurunan jarak.
  * Contoh interpretasi: penurunan jarak menunjukkan fulfillment lebih dekat ke demand proxy, tetapi belum memasukkan biaya inventory duplication.

* Emission reduction
  * Unit: persen pengurangan kg CO2e per 100.000 proxy deliveries.
  * Skenario terbaik: 92.7% pada 30 MFC dan 100 persen EV adoption.
  * Label interpretasi: Transformational.
  * Deskripsi: The scenario reduces operational CO2e by at least half relative to the centralized ICE baseline.
  * Rekomendasi: Prioritize implementation if investment cost and inventory complexity remain acceptable.
  * Referensi: Emission reduction follows scenario-based CO2e accounting using distance multiplied by vehicle emission factors.

* Global Moran's I
  * Unit: statistik autocorrelation spasial.
  * Demand index Moran's I: 0.944, p-value 0.001.
  * Underserved score Moran's I: 0.870, p-value 0.001.
  * Label interpretasi demand: Strong positive spatial autocorrelation.
  * Deskripsi: High and low values are spatially clustered rather than randomly distributed.
  * Rekomendasi: Use LISA clusters to target spatially contiguous intervention zones.
  * Referensi: Moran's I dan LISA spatial autocorrelation theory.

* LISA cluster
  * Unit: label lokal High-High, Low-Low, High-Low, Low-High, atau Not significant.
  * Threshold signifikansi: alpha 0.05 dengan 999 permutations.
  * Contoh interpretasi: High-High pada underserved score berarti cell bernilai underserved tinggi dan dikelilingi cell underserved tinggi lain, sehingga lebih kuat sebagai target intervensi dibanding cell tinggi yang berdiri sendiri.

* Cluster label operasional
  * Unit: kelas segmentasi KMeans.
  * Label: High-demand underserved priority, High-demand accessible core, Lower-demand peripheral, dan Mixed urban opportunity.
  * Contoh interpretasi: High-demand underserved priority adalah area prioritas MFC baru atau rebalancing fleet, sedangkan High-demand accessible core lebih cocok untuk densifikasi operasi dan EV deployment.
