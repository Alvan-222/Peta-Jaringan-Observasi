import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
import os

# --- KONFIGURASI HALAMAN & NAMA FILE ---
st.set_page_config(
    page_title="Indonesia AWS Network Dashboard",
    page_icon="🛰️",
    layout="wide"
)

# Nama file yang akan dibaca secara otomatis
FILE_PATH = "METADATA_SELURUH_DATA.xlsx"

# --- NAMA FILE GAMBAR ---
# Pastikan gambar ada di folder yang sama dengan skrip Python dan nama file gambar sesuai dengan nama file.
IMAGE_MAPPING = {
    "IKRO": "ikro.png",
    "AWS": "aws.png",
    "AAWS": "aaws.png",
    "ARG": "arg.png",
    "ASRS": "asrs.png"
    # Tambahkan atau ubah sesuai nama sheet dan gambar Anda
}
# --- FUNGSI-FUNGSI APLIKASI ---

@st.cache_data
def get_sheet_names(file_path):
    """Membaca dan mengembalikan nama-nama sheet dari file Excel."""
    try:
        xls = pd.ExcelFile(file_path)
        return xls.sheet_names
    except FileNotFoundError:
        return None
    except Exception as e:
        st.error(f"Gagal membaca file Excel: {e}")
        return None

@st.cache_data
def load_data_from_sheet(file_path, sheet_name):
    """Memuat dan memproses data dari sheet Excel yang dipilih."""
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # Pemetaan kolom yang mungkin ke nama standar
        column_mapping = {
            'id_station': 'id_site', 'id_site': 'id_site',
            'name_station': 'nama_site', 'nama_site': 'nama_site',
            'nama_propinsi': 'provinsi', 'provinsi': 'provinsi',
            'nama_kota': 'kabupaten', 'kabupaten': 'kabupaten',
            'kecamatan': 'kecamatan',
            'kelurahan': 'desa', 'desa':'desa',
            'latt_station': 'latitude', 'latitude': 'latitude',
            'long_station': 'longitude', 'longitude': 'longitude',
            'elv_station': 'elevasi', 'elevasi': 'elevasi',
            'tgl_pasang': 'tgl_pasang', 'th_pengadaan': 'tgl_pasang',
            'addr_instansi': 'alamat', 'alamat': 'alamat',
            'nama_vendor': 'merk', 'merk': 'merk',
            'instansi': 'instansi'
        }
        # Ganti nama kolom yang ada di DataFrame
        df.rename(columns=lambda col: column_mapping.get(col, col), inplace=True)
        
        # --- Proses dan Bersihkan Data ---
        # Pastikan kolom-kolom standar ada, jika tidak buat kolom kosong
        standard_columns = ['id_site', 'nama_site', 'provinsi', 'kabupaten', 'kecamatan', 'desa', 'latitude', 'longitude', 'elevasi', 'tgl_pasang', 'alamat', 'merk', 'instansi']
        for col in standard_columns:
            if col not in df.columns:
                df[col] = None

        # Konversi dan pembersihan data
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['id_site'] = df['id_site'].astype(str)
        # Ekstrak tahun dari 'tgl_pasang'
        df['th_pengadaan'] = pd.to_datetime(df['tgl_pasang'], errors='coerce').dt.year
        # Isi nilai 'merk' yang kosong dengan 'N/A'
        df['merk'] = df['merk'].fillna('N/A').astype(str)
        # Hapus baris dengan koordinat yang tidak valid
        df.dropna(subset=['latitude', 'longitude'], inplace=True)
        
        return df
    
    except Exception as e:
        st.error(f"Gagal memuat sheet '{sheet_name}'. Error: {e}")
        return pd.DataFrame() # Kembalikan DataFrame kosong jika gagal

def create_indonesia_map(df, selected_site_id=None):
    """
    Membuat peta interaktif Indonesia dengan popup.
    Menampilkan semua lokasi stasiun cuaca dengan opsi untuk memilih satu stasiun.
    """
    if df.empty: return folium.Map(location=[-2.5, 129.0], zoom_start=4)

    m = folium.Map(location=[-2.5, 129.0], zoom_start=4.5, tiles='CartoDB positron')
    folium.TileLayer('OpenStreetMap').add_to(m)

    for _, site in df.iterrows():
        is_selected = str(site['id_site']) == str(selected_site_id)
        color, icon = ('red', 'star') if is_selected else ('blue', 'cloud')
        
        # --- KONTEN POPUP YANG DIPERBARUI ---
        popup_content = f"""
        <div style="width: 300px; font-family: Arial, sans-serif; font-size: 14px;">
            <h4 style="margin-bottom: 10px; color: #007BFF;">{site.get('nama_site', 'N/A')}</h4>
            <hr style="margin: 5px 0;">
            <b>ID Stasiun:</b> {site.get('id_site', 'N/A')}<br>
            <b>Provinsi:</b> {site.get('provinsi', 'N/A')}<br>
            <b>Kab/Kota:</b> {site.get('kabupaten', 'N/A')}<br>
            <b>Elevasi:</b> {site.get('elevasi', 'N/A')} m<br>
            <b>Tahun Pasang:</b> {int(site['th_pengadaan']) if pd.notna(site['th_pengadaan']) else 'N/A'}<br>
            <b>Vendor:</b> {site.get('merk', 'N/A')}
        </div>
        """
        
        folium.Marker(
            location=[site['latitude'], site['longitude']],
            popup=folium.Popup(popup_content, max_width=350),
            tooltip=f"{site.get('nama_site', 'N/A')}",
            icon=folium.Icon(color=color, icon=icon, prefix='glyphicon')
        ).add_to(m)
    
    folium.LayerControl().add_to(m)
    return m

# --- FUNGSI-FUNGSI UNTUK STATISTIK DAN CHARTS ---
def create_province_distribution_chart(df):
    """Membuat chart distribusi stasiun per provinsi."""
    if df.empty or 'provinsi' not in df.columns: return go.Figure()
    province_counts = df['provinsi'].dropna().value_counts()
    fig = px.bar(province_counts, y=province_counts.index, orientation='h', title="Distribusi Stasiun per Provinsi", labels={'value': 'Jumlah', 'index': 'Provinsi'}, color=province_counts.values, color_continuous_scale='Viridis')
    fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
    return fig

def create_installation_timeline_chart(df):
    """Membuat chart linimasa instalasi stasiun."""
    if df.empty or 'th_pengadaan' not in df.columns: return go.Figure()
    df_clean = df.dropna(subset=['th_pengadaan'])
    if df_clean.empty: return go.Figure()
    year_counts = df_clean['th_pengadaan'].value_counts().sort_index()
    fig = px.line(x=year_counts.index.astype(int), y=year_counts.values, title="Linimasa Instalasi Stasiun", markers=True)
    fig.update_layout(xaxis_title="Tahun", yaxis_title="Jumlah", xaxis_type='category')
    return fig

def create_equipment_distribution_chart(df):
    if df.empty or 'merk' not in df.columns: return go.Figure()
    df_clean = df[df['merk'] != 'N/A'].dropna(subset=['merk'])
    if df_clean.empty: return go.Figure()
    brand_counts = df_clean['merk'].value_counts().nlargest(15)
    fig = px.pie(brand_counts, values=brand_counts.values, names=brand_counts.index, title="Distribusi Vendor Peralatan (Top 15)")
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

# --- APLIKASI UTAMA ---
def main():
    st.title("🛰️ Dashboard Peta Jaringan BMKG")
    st.markdown("---")

    if not os.path.exists(FILE_PATH):
        st.error(f"File tidak ditemukan! Pastikan file '{FILE_PATH}' ada di folder yang sama.")
        st.stop()

    sheet_names = get_sheet_names(FILE_PATH)
    if not sheet_names:
        st.error("Tidak dapat membaca nama sheet. File mungkin rusak.")
        st.stop()

    st.sidebar.header("⚙️ Pengaturan Data")
    selected_sheet = st.sidebar.selectbox("1. Pilih Sumber Data (Sheet)", sheet_names)
    
    df = load_data_from_sheet(FILE_PATH, selected_sheet)

    if df.empty:
        st.warning(f"Tidak ada data valid di sheet '{selected_sheet}'.")
        st.stop()

    st.sidebar.header("🔍 Filter & Seleksi")
    site_options = df[['id_site', 'nama_site']].copy().dropna(subset=['nama_site'])
    site_options['display'] = site_options['id_site'].astype(str) + ' - ' + site_options['nama_site']
    
    selected_site_display = st.sidebar.selectbox("2. Pilih Stasiun untuk Detail", site_options['display'].tolist())
    selected_site_id = selected_site_display.split(' - ')[0]

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ Peta Interaktif", "📊 Statistik", "📋 Direktori", "🎯 Detail", "🖼️ Gambar Statis"])
    
    with tab1:
        st.subheader(f"Peta Sebaran Stasiun dari Sheet: `{selected_sheet}`")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Stasiun", len(df))
        col2.metric("Provinsi Terjangkau", df['provinsi'].nunique())
        col3.metric("Aktif Sejak", int(df['th_pengadaan'].min()) if df['th_pengadaan'].notna().any() else "N/A")

        map_obj = create_indonesia_map(df, selected_site_id)
        st_folium(map_obj, width=1200, height=600, returned_objects=[])
        
        st.markdown("""
        **Legenda Peta:**
        - 🔴 **Bintang Merah**: Stasiun yang sedang dipilih.
        - 🔵 **Awan Biru**: Stasiun lainnya.
        """)
    
    with tab2:
        st.subheader(f"Statistik Jaringan dari Sheet: `{selected_sheet}`")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_province_distribution_chart(df), use_container_width=True)
        with col2:
            st.plotly_chart(create_equipment_distribution_chart(df), use_container_width=True)
        st.plotly_chart(create_installation_timeline_chart(df), use_container_width=True)
        
    with tab3:
        st.subheader(f"Direktori Lengkap dari Sheet: `{selected_sheet}`")
        display_cols = ['id_site', 'nama_site', 'provinsi', 'kabupaten', 'latitude', 'longitude', 'th_pengadaan', 'merk']
        st.dataframe(df[display_cols], use_container_width=True)
        
    with tab4:
        st.subheader("🎯 Detail Stasiun Terpilih")
        selected_site = df[df['id_site'] == selected_site_id].iloc[0]
        st.write(selected_site.to_dict())

    with tab5:
        st.subheader(f"Tampilan Gambar untuk Sheet: `{selected_sheet}`")
        
        # Ambil nama file gambar dari pemetaan berdasarkan sheet yang dipilih
        image_filename = IMAGE_MAPPING.get(selected_sheet)
        
        if image_filename and os.path.exists(image_filename):
            st.image(image_filename, caption=f"Gambar untuk sheet: {selected_sheet}", use_column_width=True)
        elif image_filename:
            st.warning(f"File gambar tidak ditemukan! Pastikan ada file bernama '{image_filename}' di folder yang sama.")
        else:
            st.info(f"Tidak ada gambar yang diatur untuk sheet '{selected_sheet}'. Anda bisa mengaturnya di variabel `IMAGE_MAPPING` dalam kode.")


if __name__ == "__main__":
    main()