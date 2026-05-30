# Recommendations

1. Prioritaskan MFC pada cluster demand tinggi yang belum tercakup 30 menit
   * Insight pemicu: skenario referensi 30 MFC mencakup 76.3% proxy demand.
   * Aksi konkret: lakukan site search dalam underserved High-High LISA clusters, bukan hanya pada ranking demand individual.
   * Aktor relevan: quick-commerce operator, real estate expansion team, city logistics planner.
   * Indikator keberhasilan: coverage proxy demand naik ke minimal 90 persen dan p90 nearest-MFC distance turun.
   * Prioritas: tinggi, karena langsung menurunkan jarak tempuh dan meningkatkan service level.

2. Paketkan network optimization dengan EV adoption bertahap
   * Insight pemicu: skenario terbaik menurunkan CO2e sebesar 92.7%.
   * Aksi konkret: mulai EV deployment pada MFC dengan demand tinggi dan radius pendek agar utilization tinggi.
   * Aktor relevan: fleet manager, ESG team, energy partner, charging infrastructure provider.
   * Indikator keberhasilan: kg CO2e per 100.000 proxy deliveries turun dan EV utilization per shift stabil.
   * Prioritas: tinggi, karena EV paling efektif ketika jarak fulfillment sudah dipangkas.

3. Gunakan Tangerang sebagai pilot underserved intervention
   * Insight pemicu: Tangerang memiliki mean underserved score tertinggi sebesar 0.4012.
   * Aksi konkret: uji MFC tambahan, rider staging point, atau dark-store partnership di unit administratif ini.
   * Aktor relevan: operator q-commerce, pemerintah kota atau kabupaten, pemilik retail anchor.
   * Indikator keberhasilan: penurunan underserved score lokal dan peningkatan share demand tercakup 30 menit.
   * Prioritas: tinggi, karena pilot harus dimulai dari gap spasial terbesar.

4. Jangan menyamakan peta populasi dengan peta demand quick commerce
   * Insight pemicu: demand index memasukkan VIIRS, built-up, road access, dan POI density selain populasi.
   * Aksi konkret: gunakan multi-proxy scoring untuk expansion planning dan hindari keputusan berbasis populasi tunggal.
   * Aktor relevan: strategy analyst, data science team, commercial expansion team.
   * Indikator keberhasilan: kandidat lokasi memiliki demand index tinggi dan road accessibility score tinggi.
   * Prioritas: menengah, karena meningkatkan kualitas site screening sebelum due diligence properti.

5. Buat policy sandbox untuk low-emission urban logistics zones
   * Insight pemicu: emission reduction paling besar muncul dari kombinasi lokasi MFC dan fleet electrification.
   * Aksi konkret: pemerintah dapat menetapkan zona pilot untuk loading, charging, dan micro-fulfillment di area high-demand.
   * Aktor relevan: Dinas Perhubungan, Dinas Lingkungan Hidup, BPTJ, operator platform.
   * Indikator keberhasilan: penurunan jarak rata-rata last-mile, peningkatan EV share, dan pengurangan CO2e per delivery proxy.
   * Prioritas: menengah, karena memerlukan koordinasi lintas instansi.

6. Terapkan sensitivity review sebelum investasi real estate
   * Insight pemicu: hasil bergantung pada bobot demand proxy, detour factor, dan speed assumption.
   * Aksi konkret: jalankan ulang pipeline dengan grid 1500 m, speed 15 km/h, dan bobot demand alternatif sebelum finalisasi lokasi.
   * Aktor relevan: investment committee, operations research team, finance team.
   * Indikator keberhasilan: kandidat lokasi tetap muncul pada beberapa skenario sensitivitas.
   * Prioritas: tinggi untuk keputusan capex, karena mengurangi risiko salah lokasi.

7. Integrasikan data proprietary setelah framework open-data tervalidasi
   * Insight pemicu: project ini membangun reproducible baseline tanpa order aktual.
   * Aksi konkret: tambahkan anonymized order density, rider GPS aggregates, cancellation rate, dan delivery time actuals ke pipeline internal.
   * Aktor relevan: operator q-commerce, data privacy officer, analytics team.
   * Indikator keberhasilan: korelasi demand proxy dengan order aktual meningkat dan rekomendasi MFC lebih presisi.
   * Prioritas: menengah, karena membutuhkan governance data internal.
