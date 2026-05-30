from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.config import get_settings
from micro_fulfillment_network_jakarta.data_io import compute_data_folder_size_gb, write_text
from micro_fulfillment_network_jakarta.logger import get_logger
from micro_fulfillment_network_jakarta.reporting import (
    interpret_emission_reduction,
    interpret_moran_i,
    interpret_service_coverage,
)
from micro_fulfillment_network_jakarta.validators import require_file


def pct(value: float) -> str:
    """Format a proportion or percent value as percent text."""
    if pd.isna(value):
        return "tidak tersedia"
    if abs(value) <= 1.5:
        return f"{value * 100:.1f}%"
    return f"{value:.1f}%"


def num(value: float, digits: int = 1) -> str:
    """Format a number with fixed decimals."""
    if pd.isna(value):
        return "tidak tersedia"
    return f"{value:,.{digits}f}"


def read_required_csv(path: Path) -> pd.DataFrame:
    """Read a required CSV file."""
    require_file(path)
    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError(f"Required CSV is empty: {path}")
    return frame


def choose_reference_scenario(summary: pd.DataFrame) -> pd.Series:
    """Choose minimum scenario reaching 90 percent coverage, otherwise best available scenario."""
    eligible = summary[summary["coverage_share"] >= 0.90].sort_values("mfc_count")
    if not eligible.empty:
        return eligible.iloc[0]
    return summary.sort_values(["coverage_share", "mfc_count"], ascending=[False, True]).iloc[0]


def compute_demand_concentration(clusters_path: Path) -> dict[str, float]:
    """Compute area share required to reach at least 70 percent of demand proxy."""
    grid = gpd.read_file(clusters_path, layer="demand_clusters")
    ordered = grid[["demand_index", "area_m2"]].sort_values("demand_index", ascending=False).copy()
    total_demand = float(ordered["demand_index"].sum())
    total_area = float(ordered["area_m2"].sum())

    if total_demand <= 0 or total_area <= 0:
        return {
            "area_share_for_70pct_demand": np.nan,
            "top10_area_share": np.nan,
            "top10_demand_share": np.nan,
        }

    ordered["cum_demand_share"] = ordered["demand_index"].cumsum() / total_demand
    ordered["cum_area_share"] = ordered["area_m2"].cumsum() / total_area

    threshold_positions = np.where(ordered["cum_demand_share"].to_numpy() >= 0.70)[0]
    if len(threshold_positions) == 0:
        selected = ordered.copy()
    else:
        cutoff_position = int(threshold_positions[0])
        selected = ordered.iloc[: cutoff_position + 1].copy()

    top10_cut = ordered["demand_index"].quantile(0.90)
    top10 = ordered[ordered["demand_index"] >= top10_cut]

    return {
        "area_share_for_70pct_demand": float(selected["area_m2"].sum() / total_area),
        "top10_area_share": float(top10["area_m2"].sum() / total_area),
        "top10_demand_share": float(top10["demand_index"].sum() / total_demand),
    }



def build_how_to_read(settings, reference: pd.Series, best_emission: pd.Series, moran: pd.DataFrame) -> str:
    """Build Indonesian how-to-read report."""
    coverage_interpretation = interpret_service_coverage(float(reference["coverage_share"]))
    emission_interpretation = interpret_emission_reduction(float(best_emission["emission_reduction_percent"]))
    moran_demand = moran[moran["metric"] == "demand_index"].iloc[0]
    moran_underserved = moran[moran["metric"] == "underserved_score"].iloc[0]
    moran_interpretation = interpret_moran_i(float(moran_demand["moran_i"]))

    return f"""# Cara Membaca Metrik

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
  * Nilai skenario referensi: {pct(float(reference["coverage_share"]))}.
  * Label interpretasi: {coverage_interpretation["level"]}.
  * Deskripsi: {coverage_interpretation["description"]}
  * Rekomendasi: {coverage_interpretation["recommendation"]}
  * Referensi: {coverage_interpretation["reference"]}

* Demand-weighted distance
  * Unit: kilometer per 100.000 proxy deliveries.
  * Baseline: {num(float(reference["baseline_demand_weighted_distance_km"]), 1)} km.
  * Skenario referensi: {num(float(reference["demand_weighted_distance_km"]), 1)} km.
  * Threshold hipotesis: H1 menguji minimal 20 persen penurunan jarak.
  * Contoh interpretasi: penurunan jarak menunjukkan fulfillment lebih dekat ke demand proxy, tetapi belum memasukkan biaya inventory duplication.

* Emission reduction
  * Unit: persen pengurangan kg CO2e per 100.000 proxy deliveries.
  * Skenario terbaik: {pct(float(best_emission["emission_reduction_percent"]))} pada {int(best_emission["mfc_count"])} MFC dan {int(best_emission["ev_adoption_percent"])} persen EV adoption.
  * Label interpretasi: {emission_interpretation["level"]}.
  * Deskripsi: {emission_interpretation["description"]}
  * Rekomendasi: {emission_interpretation["recommendation"]}
  * Referensi: {emission_interpretation["reference"]}

* Global Moran's I
  * Unit: statistik autocorrelation spasial.
  * Demand index Moran's I: {num(float(moran_demand["moran_i"]), 3)}, p-value {num(float(moran_demand["p_value"]), 3)}.
  * Underserved score Moran's I: {num(float(moran_underserved["moran_i"]), 3)}, p-value {num(float(moran_underserved["p_value"]), 3)}.
  * Label interpretasi demand: {moran_interpretation["level"]}.
  * Deskripsi: {moran_interpretation["description"]}
  * Rekomendasi: {moran_interpretation["recommendation"]}
  * Referensi: Moran's I dan LISA spatial autocorrelation theory.

* LISA cluster
  * Unit: label lokal High-High, Low-Low, High-Low, Low-High, atau Not significant.
  * Threshold signifikansi: alpha 0.05 dengan 999 permutations.
  * Contoh interpretasi: High-High pada underserved score berarti cell bernilai underserved tinggi dan dikelilingi cell underserved tinggi lain, sehingga lebih kuat sebagai target intervensi dibanding cell tinggi yang berdiri sendiri.

* Cluster label operasional
  * Unit: kelas segmentasi KMeans.
  * Label: High-demand underserved priority, High-demand accessible core, Lower-demand peripheral, dan Mixed urban opportunity.
  * Contoh interpretasi: High-demand underserved priority adalah area prioritas MFC baru atau rebalancing fleet, sedangkan High-demand accessible core lebih cocok untuk densifikasi operasi dan EV deployment.
"""


def build_conclusions(
    reference: pd.Series,
    summary: pd.DataFrame,
    emissions: pd.DataFrame,
    moran: pd.DataFrame,
    admin_summary: pd.DataFrame,
    concentration: dict[str, float],
    trend: pd.DataFrame,
) -> str:
    """Build Indonesian conclusions report."""
    best_distance = summary.sort_values("distance_reduction_percent", ascending=False).iloc[0]
    best_emission = emissions.sort_values("emission_reduction_percent", ascending=False).iloc[0]
    ev50_reference = emissions[
        (emissions["mfc_count"] == int(reference["mfc_count"]))
        & (emissions["ev_adoption_percent"] == 50)
    ]
    ev50_text = "tidak tersedia"
    if not ev50_reference.empty:
        ev50_text = pct(float(ev50_reference.iloc[0]["emission_reduction_percent"]))

    top_underserved = admin_summary.sort_values("mean_underserved_score", ascending=False).head(5)
    moran_demand = moran[moran["metric"] == "demand_index"].iloc[0]
    moran_underserved = moran[moran["metric"] == "underserved_score"].iloc[0]

    trend_row = trend.iloc[0]
    trend_text = (
        f"Sen's slope VIIRS sebesar {num(float(trend_row['sen_slope_avg_rad_per_year']), 3)} avg_rad per tahun dengan Kendall p-value {num(float(trend_row['kendall_p_value']), 3)}"
        if "sen_slope_avg_rad_per_year" in trend.columns
        else "tren VIIRS tidak tersedia"
    )

    underserved_lines = "\n".join(
        f"* {row['NAME_2']}: mean underserved score {num(float(row['mean_underserved_score']), 4)}, high-high underserved cells {int(row['high_high_underserved_lisa_count'])}."
        for _, row in top_underserved.iterrows()
    )

    h1_status = "terdukung" if float(best_distance["distance_reduction_percent"]) >= 20 else "tidak terdukung"
    h2_status = "terdukung" if float(concentration["area_share_for_70pct_demand"]) < 0.40 else "tidak terdukung"
    h3_status = "terdukung" if (not ev50_reference.empty and float(ev50_reference.iloc[0]["emission_reduction_percent"]) >= 30) else "tidak terdukung"

    return f"""# Conclusions

## Answer to Research Questions

1. Jumlah minimum MFC yang mencapai target 90 persen coverage adalah {int(reference["mfc_count"])} jika skenario tersebut mencapai 90 persen. Coverage skenario referensi adalah {pct(float(reference["coverage_share"]))}. Jika nilai ini di bawah 90 persen, maka seluruh skenario yang diuji belum memenuhi target dan {int(reference["mfc_count"])} adalah konfigurasi coverage terbaik pada rentang p yang diuji.

2. Area underserved prioritas terbesar berada pada unit administratif dengan mean underserved score tertinggi. Lima unit teratas adalah:
{underserved_lines}

3. Skenario terbaik yang diuji menurunkan demand-weighted distance sebesar {pct(float(best_distance["distance_reduction_percent"]))} dibanding centralized baseline. Baseline distance adalah {num(float(best_distance["baseline_demand_weighted_distance_km"]), 1)} km per 100.000 proxy deliveries, sedangkan skenario terbaik adalah {num(float(best_distance["demand_weighted_distance_km"]), 1)} km.

4. Pengurangan CO2e tertinggi adalah {pct(float(best_emission["emission_reduction_percent"]))} pada {int(best_emission["mfc_count"])} MFC dan {int(best_emission["ev_adoption_percent"])} persen EV adoption. Pada skenario referensi dengan 50 persen EV adoption, pengurangan CO2e adalah {ev50_text}.

5. Demand index menunjukkan Moran's I sebesar {num(float(moran_demand["moran_i"]), 3)} dengan p-value {num(float(moran_demand["p_value"]), 3)}. Underserved score menunjukkan Moran's I sebesar {num(float(moran_underserved["moran_i"]), 3)} dengan p-value {num(float(moran_underserved["p_value"]), 3)}. Nilai ini menunjukkan apakah hotspot demand dan underserved area membentuk pola spasial yang signifikan, bukan hanya titik ekstrem individual.

## Top 5 Findings

* Optimasi lokasi MFC menghasilkan penurunan jarak maksimum sebesar {pct(float(best_distance["distance_reduction_percent"]))} pada rentang skenario yang diuji. Implikasinya, desain jaringan lebih menentukan efisiensi spasial daripada hanya mempercepat rider pada jaringan yang sama.

* Skenario referensi {int(reference["mfc_count"])} MFC memberi coverage {pct(float(reference["coverage_share"]))} dalam SLA 30 menit. Jika nilai ini belum mencapai 90 persen, maka operator perlu menaikkan jumlah MFC di atas rentang yang diuji atau menambah strategi hybrid seperti pop-up fulfillment dan rider staging.

* Kombinasi spatial optimization dan EV adoption menghasilkan pengurangan emisi tertinggi sebesar {pct(float(best_emission["emission_reduction_percent"]))}. Ini menunjukkan decarbonization tidak cukup hanya mengganti kendaraan, karena jarak fulfillment tetap menentukan beban energi.

* Sebanyak 70 persen demand proxy terkonsentrasi pada sekitar {pct(float(concentration["area_share_for_70pct_demand"]))} area grid. Status H2: {h2_status}. Jika area share rendah, strategi MFC perlu fokus pada cluster, bukan penyebaran merata.

* Spatial autocorrelation underserved score menunjukkan Moran's I {num(float(moran_underserved["moran_i"]), 3)}. Jika signifikan, rekomendasi lokasi harus berbasis cluster contiguous, bukan daftar cell ranking individual.

## Hypothesis Evaluation

* H1, distributed MFC network reduces distance by at least 20 percent: {h1_status}. Nilai terbaik yang diuji adalah {pct(float(best_distance["distance_reduction_percent"]))}.

* H2, at least 70 percent of demand proxy is concentrated within less than 40 percent of grid area: {h2_status}. Area share untuk 70 persen demand proxy adalah {pct(float(concentration["area_share_for_70pct_demand"]))}.

* H3, optimized MFC plus 50 percent EV adoption reduces CO2e by at least 30 percent: {h3_status}. Nilai skenario referensi EV 50 persen adalah {ev50_text}.

## Spatial Pattern Summary

Demand proxy tidak menyebar merata. Cell bernilai tinggi muncul pada kombinasi populasi tinggi, nighttime lights kuat, built-up intensity, akses jalan, dan POI komersial. Underserved hotspots paling penting adalah area demand tinggi yang masih berada di luar cakupan 30 menit dalam skenario referensi.

## Temporal Pattern Summary

Konteks temporal nighttime lights 2020 sampai 2024 menunjukkan {trend_text}. Angka ini harus dibaca sebagai perubahan aktivitas malam metropolitan, bukan pertumbuhan order q-commerce aktual.

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
"""


def build_recommendations(reference: pd.Series, emissions: pd.DataFrame, admin_summary: pd.DataFrame) -> str:
    """Build Indonesian recommendations report."""
    best_emission = emissions.sort_values("emission_reduction_percent", ascending=False).iloc[0]
    top_unit = admin_summary.sort_values("mean_underserved_score", ascending=False).iloc[0]

    return f"""# Recommendations

1. Prioritaskan MFC pada cluster demand tinggi yang belum tercakup 30 menit
   * Insight pemicu: skenario referensi {int(reference["mfc_count"])} MFC mencakup {pct(float(reference["coverage_share"]))} proxy demand.
   * Aksi konkret: lakukan site search dalam underserved High-High LISA clusters, bukan hanya pada ranking demand individual.
   * Aktor relevan: quick-commerce operator, real estate expansion team, city logistics planner.
   * Indikator keberhasilan: coverage proxy demand naik ke minimal 90 persen dan p90 nearest-MFC distance turun.
   * Prioritas: tinggi, karena langsung menurunkan jarak tempuh dan meningkatkan service level.

2. Paketkan network optimization dengan EV adoption bertahap
   * Insight pemicu: skenario terbaik menurunkan CO2e sebesar {pct(float(best_emission["emission_reduction_percent"]))}.
   * Aksi konkret: mulai EV deployment pada MFC dengan demand tinggi dan radius pendek agar utilization tinggi.
   * Aktor relevan: fleet manager, ESG team, energy partner, charging infrastructure provider.
   * Indikator keberhasilan: kg CO2e per 100.000 proxy deliveries turun dan EV utilization per shift stabil.
   * Prioritas: tinggi, karena EV paling efektif ketika jarak fulfillment sudah dipangkas.

3. Gunakan {str(top_unit["NAME_2"])} sebagai pilot underserved intervention
   * Insight pemicu: {str(top_unit["NAME_2"])} memiliki mean underserved score tertinggi sebesar {num(float(top_unit["mean_underserved_score"]), 4)}.
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
"""


def build_executive_summary(reference: pd.Series, summary: pd.DataFrame, emissions: pd.DataFrame, concentration: dict[str, float], moran: pd.DataFrame) -> str:
    """Build Indonesian executive summary around 500 words."""
    best_distance = summary.sort_values("distance_reduction_percent", ascending=False).iloc[0]
    best_emission = emissions.sort_values("emission_reduction_percent", ascending=False).iloc[0]
    moran_underserved = moran[moran["metric"] == "underserved_score"].iloc[0]

    return f"""# Executive Summary

Greater Jakarta adalah pasar metropolitan yang menuntut pengiriman cepat, tetapi quick commerce menghadapi trade-off antara SLA 30 menit, biaya last-mile, dan emisi operasional. Project ini membangun framework open-data untuk menguji apakah desain jaringan micro-fulfillment center dapat mengurangi jarak tempuh dan CO2e tanpa mengklaim order aktual platform. Demand yang dianalisis adalah latent quick-commerce demand proxy dari populasi, nighttime lights, built-up intensity, road accessibility, dan commercial POI density.

Metode utama mencakup pembuatan AOI dari GADM 4.1, preprocessing raster melalui Google Earth Engine, pembangunan grid demand 1 km, candidate MFC screening dari OSM POI dan high-demand cells, p-median optimization, 30-minute service coverage, spatial autocorrelation, dan emission scenario analysis. Emisi dihitung per 100.000 proxy deliveries agar hasil dapat dibandingkan tanpa membutuhkan data transaksi proprietary.

Temuan kunci:

* Skenario referensi memilih {int(reference["mfc_count"])} MFC dengan coverage {pct(float(reference["coverage_share"]))} terhadap proxy demand dalam SLA 30 menit.

* Skenario terbaik menurunkan demand-weighted distance sebesar {pct(float(best_distance["distance_reduction_percent"]))} dibanding centralized baseline.

* Pengurangan CO2e tertinggi mencapai {pct(float(best_emission["emission_reduction_percent"]))} pada {int(best_emission["mfc_count"])} MFC dan {int(best_emission["ev_adoption_percent"])} persen EV adoption.

* Sebanyak 70 persen demand proxy terkonsentrasi pada sekitar {pct(float(concentration["area_share_for_70pct_demand"]))} area grid, sehingga expansion planning harus berbasis cluster, bukan pemerataan fasilitas.

* Underserved score memiliki Moran's I {num(float(moran_underserved["moran_i"]), 3)} dengan p-value {num(float(moran_underserved["p_value"]), 3)}, yang menunjukkan apakah gap service membentuk cluster spasial signifikan.

Rekomendasi prioritas tinggi:

* Prioritaskan MFC pada underserved High-High LISA clusters untuk menaikkan coverage dan menurunkan p90 nearest-MFC distance.

* Paketkan MFC optimization dengan EV adoption karena electrification paling efektif ketika jarak fulfillment sudah dipersingkat.

* Jalankan sensitivity review sebelum capex real estate dengan skenario speed 15 km/h, bobot demand alternatif, dan grid 1500 m.

Reproducibility: seluruh pipeline dapat dijalankan dari repository dengan satu perintah setelah environment dan credential Google Earth Engine disiapkan.
"""


def build_methodology(settings) -> str:
    """Build English methodology report for international audience."""
    return f"""# Methodology

## Study Area

The study area is the road-based Greater Jakarta metropolitan logistics region. It includes DKI Jakarta and adjacent urban jurisdictions in Bogor, Depok, Tangerang, and Bekasi. Kepulauan Seribu is excluded because the study focuses on road-based last-mile delivery rather than multimodal island logistics. Administrative boundaries are generated reproducibly from GADM 4.1 level 2 polygons and dissolved into a functional metropolitan AOI.

## Data Sources

The analysis uses only open-access data. Population is represented by WorldPop population count from Google Earth Engine. Economic activity is proxied using NOAA VIIRS nighttime lights annual mean. Urban intensity is represented by Google Dynamic World built probability. Road accessibility and commercial intensity are derived from OpenStreetMap road segments and commercial POIs downloaded through OSMnx. Administrative boundaries are obtained from GADM 4.1. Emission scenarios use transparent vehicle activity-data accounting with stated assumptions for internal combustion motorcycles, electric motorcycle energy consumption, and grid emission intensity.

## Pre-processing Pipeline

Google Earth Engine is used for raster preprocessing. WorldPop is filtered to Indonesia, clipped to the AOI, aggregated to {settings.analysis_grid_size_meters} m using a sum reducer, and reprojected to EPSG:32748. VIIRS monthly nighttime lights are composited into an annual mean and aggregated to the same grid. Dynamic World built probability is composited as an annual mean and aggregated using a mean reducer. OpenStreetMap roads and POIs are downloaded inside the AOI, cleaned, clipped by query geometry, and reprojected to EPSG:32748. Raw data stored locally are preprocessed derivatives rather than unprocessed global tiles.

## Analytical Methods

A latent quick-commerce demand proxy is constructed with a weighted overlay:

Demand Index = 0.40 Population Score + 0.25 Nighttime Lights Score + 0.15 Built-up Score + 0.10 Road Accessibility Score + 0.10 POI Density Score.

Population, nighttime lights, road length, and POI count are transformed using log1p and scaled to 0 to 1 using percentile clipping. Candidate MFC locations are generated from high-demand grid cells and OpenStreetMap commercial POIs. Facility selection uses a deterministic greedy p-median heuristic to minimize demand-weighted distance across MFC count scenarios. Route distance is approximated as Euclidean distance multiplied by a detour factor of 1.35. Thirty-minute coverage is computed using the default speed assumption in the configuration file.

Operational emissions are calculated per 100,000 proxy deliveries:

ICE Emissions = Distance Ã— ICE Emission Factor.

EV Emissions = Distance Ã— Electricity Consumption per km Ã— Grid Emission Factor.

Fleet Emissions = ICE Share Ã— ICE Emissions + EV Share Ã— EV Emissions.

Emission reduction is calculated relative to a centralized internal combustion motorcycle baseline.

Spatial autocorrelation is evaluated using Global Moran's I and Local Moran's I. K-nearest-neighbor spatial weights with k=8 are used because the clipped grid may not remain perfectly contiguous. LISA clusters are classified into High-High, Low-Low, High-Low, Low-High, and Not significant using an alpha level of 0.05 and 999 permutations.

## Validation Strategy

The demand proxy is not validated against proprietary order volume because such data are not open access. Instead, the project performs an administrative-scale cross-check by aggregating demand proxy metrics to GADM level 2 units and comparing them with population proxy totals. This validates broad plausibility while preserving the explicit distinction between latent demand suitability and observed transactions.

## Software and Reproducibility

The project is implemented as pure Python scripts for Windows 11 and Python 3.11. Google Earth Engine Python API is used for cloud-first raster preprocessing, while geopandas, rasterio, OSMnx, scipy, scikit-learn, OR-Tools, libpysal, esda, matplotlib, folium, plotly, and pydeck are used for local analysis and visualization. All outputs are generated by scripts, each data file has metadata JSON, and the full pipeline is designed to run from a single command.
"""


def build_methodology_detail() -> str:
    """Build Indonesian detailed methodology document."""
    return """# Methodology Detail

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
"""


def build_data_dictionary() -> str:
    """Build data dictionary in Indonesian."""
    return """# Data Dictionary

* cell_id: ID unik grid cell 1 km.
* population_count: jumlah penduduk WorldPop hasil agregasi ke grid.
* nighttime_lights: annual mean VIIRS avg_rad.
* built_probability: annual mean Dynamic World built probability.
* road_length_m_intersecting: total panjang jalan OSM yang berinterseksi dengan cell.
* commercial_poi_count: jumlah POI komersial OSM dalam cell.
* population_score: skor populasi 0 sampai 1 setelah log1p dan scaling.
* nighttime_lights_score: skor VIIRS 0 sampai 1 setelah log1p dan scaling.
* built_score: skor built-up 0 sampai 1.
* road_accessibility_score: skor akses jalan 0 sampai 1.
* poi_density_score: skor POI 0 sampai 1.
* demand_index: latent quick-commerce demand proxy 0 sampai 1.
* proxy_deliveries_per_100k: bobot demand yang dinormalisasi ke 100.000 unit proxy.
* mfc_count: jumlah micro-fulfillment center dalam skenario.
* coverage_share: share proxy demand yang tercakup dalam SLA 30 menit.
* demand_weighted_distance_km: jarak demand-weighted per 100.000 proxy deliveries.
* distance_reduction_percent: penurunan jarak dibanding baseline centralized fulfillment.
* scenario_emissions_kgco2e: emisi skenario dalam kg CO2e per 100.000 proxy deliveries.
* emission_reduction_percent: penurunan emisi dibanding centralized ICE baseline.
* underserved_score: demand index dikalikan status tidak tercakup pada skenario referensi.
* local_moran_i: statistik Local Moran's I.
* local_moran_p: p-value Local Moran's I berbasis permutations.
* lisa_cluster: label cluster LISA.
* cluster_label: label segmentasi operasional KMeans.
"""


def build_figures_index(settings) -> str:
    """Build figures index from generated files."""
    map_files = sorted(settings.maps_dir.glob("*.png"))
    chart_files = sorted(settings.charts_dir.glob("*.png"))
    interactive_files = sorted((settings.outputs_dir / "maps_interactive").glob("*.html"))

    lines = [
        "# Figures Index",
        "",
        "Dokumen ini mengindeks visual yang dihasilkan pipeline.",
        "",
        "## Static Maps",
        "",
    ]
    if map_files:
        for path in map_files:
            lines.append(f"* `{path.name}`: peta statis untuk komunikasi jurnal, policy, atau public-facing portfolio.")
    else:
        lines.append("* Belum ada file peta statis. Jalankan `python scripts\\16_generate_static_maps.py`.")

    lines.extend(["", "## Charts", ""])
    if chart_files:
        for path in chart_files:
            lines.append(f"* `{path.name}`: chart analitis untuk trade-off, ranking, tren, atau validasi.")
    else:
        lines.append("* Belum ada chart. Jalankan `python scripts\\17_generate_charts.py`.")

    lines.extend(["", "## Interactive Outputs", ""])
    if interactive_files:
        for path in interactive_files:
            lines.append(f"* `{path.name}`: output HTML interaktif untuk eksplorasi portfolio.")
    else:
        lines.append("* Belum ada output interaktif. Jalankan `python scripts\\18_generate_interactive_maps.py`.")

    return "\n".join(lines) + "\n"


def build_processing_log(settings, reference: pd.Series, best_emission: pd.Series) -> str:
    """Build processed data log."""

    data_size = compute_data_folder_size_gb()

    return f"""# Processing Log


Total data folder size: {data_size:.4f} GB.

Processed outputs created by the pipeline:

* demand_grid.gpkg: latent quick-commerce demand proxy grid.
* demand_index.tif: rasterized demand index.
* mfc_candidates.gpkg: candidate micro-fulfillment center locations.
* optimized_mfc_networks.gpkg: selected MFC points by scenario.
* service_coverage.gpkg: nearest-MFC distance, coverage flags, and underserved score.
* emission_scenarios.csv: CO2e scenarios by MFC count and EV adoption.
* demand_underserved_lisa.gpkg: Local Moran's I cluster diagnostics.
* spatial_autocorrelation.csv: Global Moran's I diagnostics.
* demand_clusters.gpkg: operational KMeans segments.
* viirs_temporal_trend.csv: nighttime lights trend context.
* validation_crosscheck.csv: administrative-scale sanity checks.

Reference scenario:

* MFC count: {int(reference["mfc_count"])}.
* Coverage share: {float(reference["coverage_share"]):.4f}.
* Distance reduction percent: {float(reference["distance_reduction_percent"]):.4f}.

Best emission scenario:

* MFC count: {int(best_emission["mfc_count"])}.
* EV adoption percent: {int(best_emission["ev_adoption_percent"])}.
* Emission reduction percent: {float(best_emission["emission_reduction_percent"]):.4f}.

Interpretation boundary:

* Demand metrics are open-data proxy outputs, not proprietary order volume.
* Emission metrics are scenario-based kg CO2e per 100,000 proxy deliveries, not measured company emissions.
"""


def main() -> None:
    """Build all synthesis reports."""
    settings = get_settings()
    logger = get_logger("19_build_reports")

    summary = read_required_csv(settings.tables_dir / "optimized_network_summary.csv")
    emissions = read_required_csv(settings.tables_dir / "emission_scenarios.csv")
    moran = read_required_csv(settings.tables_dir / "spatial_autocorrelation.csv")
    admin_summary = read_required_csv(settings.tables_dir / "admin_unit_demand_summary.csv")
    trend = read_required_csv(settings.tables_dir / "viirs_temporal_trend.csv")
    clusters_path = require_file(settings.processed_dir / "demand_clusters.gpkg")

    reference = choose_reference_scenario(summary)
    best_emission = emissions.sort_values("emission_reduction_percent", ascending=False).iloc[0]
    concentration = compute_demand_concentration(clusters_path)

    reports_dir = settings.reports_dir
    docs_dir = settings.project_root / "docs"

    logger.info("Building how_to_read.md.")
    write_text(reports_dir / "how_to_read.md", build_how_to_read(settings, reference, best_emission, moran))

    logger.info("Building conclusions.md.")
    write_text(
        reports_dir / "conclusions.md",
        build_conclusions(reference, summary, emissions, moran, admin_summary, concentration, trend),
    )

    logger.info("Building recommendations.md.")
    write_text(reports_dir / "recommendations.md", build_recommendations(reference, emissions, admin_summary))

    logger.info("Building executive_summary.md.")
    write_text(reports_dir / "executive_summary.md", build_executive_summary(reference, summary, emissions, concentration, moran))

    logger.info("Building methodology.md.")
    write_text(reports_dir / "methodology.md", build_methodology(settings))

    logger.info("Building docs.")
    write_text(docs_dir / "methodology_detail.md", build_methodology_detail())
    write_text(docs_dir / "data_dictionary.md", build_data_dictionary())
    write_text(docs_dir / "figures_index.md", build_figures_index(settings))

    logger.info("Updating processing log.")
    write_text(settings.processed_dir / "PROCESSING_LOG.md", build_processing_log(settings, reference, best_emission))

    logger.info("Report synthesis completed.")
    print(f"Reports completed in: {reports_dir}")
    print(f"Docs updated in: {docs_dir}")


if __name__ == "__main__":
    main()
