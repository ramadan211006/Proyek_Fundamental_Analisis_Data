import os
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

st.set_page_config(page_title="Dashboard Bike Sharing", page_icon="🚲", layout="wide")
sns.set_theme(style="whitegrid")

BASE_DIR = Path(__file__).parent
SEASON_MAP = {1: "Spring", 2: "Summer", 3: "Fall", 4: "Winter"}
WEATHER_MAP = {
    1: "Cerah",
    2: "Berkabut/Berawan",
    3: "Hujan/Salju Ringan",
    4: "Hujan/Salju Lebat",
}
SEASON_ORDER = list(SEASON_MAP.values())
WEATHER_ORDER = list(WEATHER_MAP.values())


@st.cache_data
def muat_data():
    day_df = pd.read_csv(BASE_DIR / "main_day_df.csv", parse_dates=["dteday"])
    hour_df = pd.read_csv(BASE_DIR / "main_hour_df.csv", parse_dates=["dteday"])

    # Ubah kode angka menjadi label (hanya jika masih berupa angka)
    for df in (day_df, hour_df):
        if pd.api.types.is_numeric_dtype(df["season"]):
            df["season"] = df["season"].map(SEASON_MAP)
        if pd.api.types.is_numeric_dtype(df["weathersit"]):
            df["weathersit"] = df["weathersit"].map(WEATHER_MAP)
    return day_df, hour_df


try:
    day_df, hour_df = muat_data()
except FileNotFoundError:
    st.error(
        "File `main_day_df.csv` dan `main_hour_df.csv` tidak ditemukan. "
        "Letakkan keduanya di folder yang sama dengan file dashboard ini."
    )
    st.stop()


def bar_chart(seri, judul, xlabel):
    fig, ax = plt.subplots(figsize=(8, 5))
    warna = ["#1f77b4" if v == seri.max() else "#aec7e8" for v in seri.values]
    ax.bar(seri.index, seri.values, color=warna)
    ax.set_title(judul, fontsize=13)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Rata-rata Penyewaan / Hari")
    for i, v in enumerate(seri.values):
        ax.text(i, v + seri.max() * 0.01, f"{v:,.0f}", ha="center")
    return fig


st.sidebar.header("🔎 Filter Data")

tgl_min = day_df["dteday"].min().date()
tgl_max = day_df["dteday"].max().date()
rentang = st.sidebar.date_input(
    "Rentang tanggal", value=(tgl_min, tgl_max), min_value=tgl_min, max_value=tgl_max
)
pilih_musim = st.sidebar.multiselect("Musim", SEASON_ORDER, default=SEASON_ORDER)
pilih_cuaca = st.sidebar.multiselect("Kondisi cuaca", WEATHER_ORDER, default=WEATHER_ORDER)

if len(rentang) != 2:
    st.info("Pilih tanggal mulai dan tanggal akhir pada filter di sidebar.")
    st.stop()

mulai, akhir = pd.to_datetime(rentang[0]), pd.to_datetime(rentang[1])


def terapkan_filter(df):
    return df[
        (df["dteday"] >= mulai)
        & (df["dteday"] <= akhir)
        & (df["season"].isin(pilih_musim))
        & (df["weathersit"].isin(pilih_cuaca))
    ]


day = terapkan_filter(day_df)
hour = terapkan_filter(hour_df)

if day.empty or hour.empty:
    st.warning("Tidak ada data untuk filter yang dipilih. Ubah filter di sidebar.")
    st.stop()

st.title("🚲 Dashboard Analisis Bike Sharing")
st.caption("Data penyewaan sepeda tahun 2011–2012")

rata_musim = day.groupby("season")["cnt"].mean().reindex(SEASON_ORDER).dropna()
rata_jam = hour.groupby("hr")["cnt"].mean()
rata_cuaca = (
    day.groupby("weathersit")["cnt"]
    .agg(jumlah_hari="count", rata_rata="mean")
    .reindex(WEATHER_ORDER)
    .dropna()
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Penyewaan", f"{day['cnt'].sum():,}")
c2.metric("Rata-rata per Hari", f"{day['cnt'].mean():,.0f}")
c3.metric("Jam Tersibuk", f"{rata_jam.idxmax()}:00")
c4.metric("Musim Tersibuk", rata_musim.idxmax())

st.divider()

st.header("🍂 Pertanyaan 1: Musim apa penyewaan paling tinggi dan paling rendah?")
kiri, kanan = st.columns([2, 1])
with kiri:
    st.pyplot(bar_chart(rata_musim, "Rata-rata Penyewaan Harian per Musim", "Musim"))
with kanan:
    st.markdown("**Insight**")
    st.write(
        f"- Tertinggi: **{rata_musim.idxmax()}** ({rata_musim.max():,.0f} per hari)\n"
        f"- Terendah: **{rata_musim.idxmin()}** ({rata_musim.min():,.0f} per hari)\n"
        f"- Selisih tertinggi dan terendah sekitar **{rata_musim.max() / rata_musim.min():.1f}x**"
    )
    st.markdown("**Rekomendasi**")
    st.write("Siapkan lebih banyak sepeda pada musim ramai, dan manfaatkan musim sepi untuk perawatan armada.")

st.divider()

st.header("⏰ Pertanyaan 2: Pada jam berapa penyewaan paling tinggi?")
jam_puncak = rata_jam.idxmax()
fig, ax = plt.subplots(figsize=(11, 5))
sns.lineplot(x=rata_jam.index, y=rata_jam.values, marker="o", linewidth=2.5, ax=ax)
ax.axvline(jam_puncak, color="red", linestyle="--", label=f"Puncak: jam {jam_puncak}")
ax.set_title("Rata-rata Penyewaan Sepeda per Jam")
ax.set_xlabel("Jam (0-23)")
ax.set_ylabel("Rata-rata Penyewaan")
ax.set_xticks(range(0, 24))
ax.legend()
st.pyplot(fig)

top3 = rata_jam.nlargest(3)
st.markdown("**Insight**")
st.write(
    f"- Puncak penyewaan di jam **{jam_puncak}:00** (rata-rata {rata_jam.max():,.0f}).\n"
    f"- 3 jam tersibuk: "
    + ", ".join(f"jam {h}:00 ({v:,.0f})" for h, v in top3.items())
    + ".\n"
    f"- Jam paling sepi: jam {rata_jam.idxmin()}:00 ({rata_jam.min():,.0f}), "
    "cocok untuk jadwal perawatan sepeda."
)

st.divider()

st.header("🌦️ Pertanyaan 3: Pada kondisi cuaca apa penyewaan paling tinggi dan paling rendah?")
kiri, kanan = st.columns([2, 1])
with kiri:
    st.pyplot(
        bar_chart(rata_cuaca["rata_rata"], "Rata-rata Penyewaan Harian per Kondisi Cuaca", "Kondisi Cuaca")
    )
with kanan:
    st.markdown("**Insight**")
    st.write(
        f"- Tertinggi: **{rata_cuaca['rata_rata'].idxmax()}** ({rata_cuaca['rata_rata'].max():,.0f} per hari)\n"
        f"- Terendah: **{rata_cuaca['rata_rata'].idxmin()}** ({rata_cuaca['rata_rata'].min():,.0f} per hari)"
    )
    st.markdown("**Jumlah hari per kondisi cuaca**")
    st.dataframe(
        rata_cuaca.round(0).astype(int).rename(
            columns={"jumlah_hari": "Jumlah Hari", "rata_rata": "Rata-rata"}
        )
    )
    st.caption("Catatan: jumlah hari tiap cuaca tidak seimbang, jadi rata-rata cuaca buruk berasal dari sampel kecil.")

st.divider()

st.header("📈 Analisis Lanjutan: Manual Grouping Tingkat Permintaan")
st.write(
    "Hari dikelompokkan berdasarkan jumlah penyewaan harian (`cnt`): "
    "**Rendah** (<3.000), **Sedang** (3.000-6.000), dan **Tinggi** (>6.000)."
)

LABEL_PERMINTAAN = ["Rendah (<3000)", "Sedang (3000-6000)", "Tinggi (>6000)"]
day = day.copy()
day["kategori_permintaan"] = pd.cut(
    day["cnt"], bins=[0, 3000, 6000, 9000], labels=LABEL_PERMINTAAN
)

# Sebaran hari per kategori
jumlah = day["kategori_permintaan"].value_counts().reindex(LABEL_PERMINTAAN).fillna(0).astype(int)
persen_total = jumlah / jumlah.sum() * 100
m1, m2, m3 = st.columns(3)
for kol, label in zip((m1, m2, m3), LABEL_PERMINTAAN):
    kol.metric(label, f"{jumlah[label]} hari", f"{persen_total[label]:.1f}% dari total", delta_color="off")


def distribusi(kolom_grup, urutan):
    tabel = pd.crosstab(day[kolom_grup], day["kategori_permintaan"], normalize="index") * 100
    tabel = tabel.reindex(index=urutan, columns=LABEL_PERMINTAAN).dropna(how="all").fillna(0)
    return tabel.round(1)


def stacked_chart(tabel, judul, xlabel, rotasi=0):
    fig, ax = plt.subplots(figsize=(7, 5))
    tabel.plot(kind="bar", stacked=True, ax=ax, color=["#ff9896", "#aec7e8", "#1f77b4"])
    for c in ax.containers:
        ax.bar_label(
            c,
            labels=[f"{v:.0f}%" if v >= 4 else "" for v in c.datavalues],
            label_type="center",
            fontsize=9,
        )
    ax.set_title(judul, fontsize=13)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Persentase Hari (%)")
    ax.tick_params(axis="x", rotation=rotasi)
    ax.legend(title="Kategori", bbox_to_anchor=(1.02, 1), loc="upper left")
    return fig


dist_musim = distribusi("season", SEASON_ORDER)
dist_cuaca = distribusi("weathersit", WEATHER_ORDER)

kiri, kanan = st.columns(2)
with kiri:
    st.pyplot(stacked_chart(dist_musim, "Kategori Permintaan per Musim", "Musim"))
with kanan:
    st.pyplot(stacked_chart(dist_cuaca, "Kategori Permintaan per Kondisi Cuaca", "Kondisi Cuaca", rotasi=15))

st.markdown("**Insight**")
st.write(
    f"- Dari {jumlah.sum()} hari, kategori terbanyak adalah **{jumlah.idxmax()}** "
    f"({persen_total[jumlah.idxmax()]:.1f}%).\n"
    f"- Musim dengan hari Rendah terbanyak: **{dist_musim[LABEL_PERMINTAAN[0]].idxmax()}** "
    f"({dist_musim[LABEL_PERMINTAAN[0]].max():.1f}%). "
    f"Musim dengan hari Tinggi terbanyak: **{dist_musim[LABEL_PERMINTAAN[2]].idxmax()}** "
    f"({dist_musim[LABEL_PERMINTAAN[2]].max():.1f}%).\n"
    f"- Cuaca dengan hari Rendah terbanyak: **{dist_cuaca[LABEL_PERMINTAAN[0]].idxmax()}** "
    f"({dist_cuaca[LABEL_PERMINTAAN[0]].max():.1f}%). "
    f"Cuaca dengan hari Tinggi terbanyak: **{dist_cuaca[LABEL_PERMINTAAN[2]].idxmax()}** "
    f"({dist_cuaca[LABEL_PERMINTAAN[2]].max():.1f}%)."
)

st.divider()

st.header("✅ Kesimpulan")
st.write(
    "1. **Musim:** penyewaan harian tertinggi pada musim Fall dan terendah pada Spring.\n"
    "2. **Jam:** penyewaan memuncak pada jam 17:00, diikuti jam 18:00 dan jam 08:00 "
    "(pola jam berangkat dan pulang aktivitas).\n"
    "3. **Cuaca:** penyewaan tertinggi saat cuaca Cerah dan terendah saat Hujan/Salju Ringan.\n"
    "4. **Analisis lanjutan:** dari 731 hari, 51,8% masuk kategori permintaan Sedang, 24,6% Tinggi, "
    "dan 23,5% Rendah. Musim Spring paling banyak berisi hari Rendah (64,6%), sedangkan Fall paling "
    "banyak berisi hari Tinggi (41,5%). Pada cuaca Hujan/Salju Ringan, 90,5% hari masuk kategori "
    "Rendah dan tidak ada yang masuk Tinggi, sehingga musim dan cuaca terbukti memengaruhi seberapa "
    "sering permintaan jatuh ke kategori tinggi atau rendah."
)
st.subheader("Rekomendasi")
st.write(
    "- Sesuaikan jumlah sepeda yang dioperasikan dengan musim.\n"
    "- Pastikan sepeda siap sebelum jam sibuk (08:00, 17:00, 18:00).\n"
    "- Jadwalkan perawatan di jam sepi (sekitar 02:00-05:00).\n"
    "- Siapkan promo saat cuaca berkabut atau hujan untuk menjaga jumlah penyewaan."
)
st.caption("Kesimpulan di atas berdasarkan seluruh data (tanpa filter).")