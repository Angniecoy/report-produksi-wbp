import streamlit as st
import pandas as pd
import pdfkit
import os
import platform
from datetime import datetime
from supabase import create_client, Client

# Konfigurasi Halaman
st.set_page_config(page_title="Report Produksi Readymix", layout="wide", initial_sidebar_state="collapsed")

# --- KONEKSI SUPABASE (HARDCODED) ---
@st.cache_resource
def init_connection():
    url = "https://vsqcfuoilxkwhzqnfbzs.supabase.co"
    key = "sb_publishable_MG-0l3M-SdNUfofE1h_bEQ_D6VPGwGq"
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error(f"⚠️ Gagal terhubung ke Database: {e}")
    st.stop()

# --- DAFTAR UNIT MASTER WASKITA PRECAST ---
UNIT_LIST = [
    "Soeta", "Jejawi", "KAPB", "PBB", "Pegangsaan", 
    "Cibadak", "Bend Bener", "Solo", "Magelang", "IKN", "Quarry Boja"
]

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("Navigasi Menu")
mode = st.sidebar.radio("Pilih Mode Aplikasi:", ["📝 Input Data Harian Baru", "📂 Cetak dari Master Excel Lama"])
st.sidebar.markdown("---")
st.sidebar.info("Aplikasi Report Produksi Readymix & Quarry - Waskita Beton Precast")

def hitung_status(rencana, realisasi, achv):
    if rencana == 0 and realisasi == 0: return "Critical"
    elif realisasi >= rencana: return "Optimal"
    elif achv >= 50: return "Warning"
    else: return "Critical"

def tampilkan_dashboard_dan_pdf(df, tanggal_str):
    df['Rencana (m³)'] = pd.to_numeric(df['Rencana (m³)'], errors='coerce').fillna(0)
    df['Realisasi (m³)'] = pd.to_numeric(df['Realisasi (m³)'], errors='coerce').fillna(0)
    if 'Deviasi (m³)' not in df.columns:
        df['Deviasi (m³)'] = df['Realisasi (m³)'] - df['Rencana (m³)']
    
    total_rencana = df['Rencana (m³)'].sum()
    total_realisasi = df['Realisasi (m³)'].sum()
    total_deviasi = total_realisasi - total_rencana
    overall_achv = (total_realisasi / total_rencana * 100) if total_rencana > 0 else 0

    html_dashboard = f"""
<style>
.waskita-dash {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin-top: -30px; }}
.waskita-header {{ display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 3px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 25px; }}
.waskita-title h2 {{ margin: 0; color: #0a1f44; font-size: 28px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }}
.waskita-title p {{ margin: 5px 0 0 0; color: #64748b; font-size: 15px; }}
.waskita-date {{ background: #eff6ff; color: #1e3a8a; padding: 10px 25px; border-radius: 4px; border: 1px solid #bfdbfe; font-weight: bold; font-size: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
.waskita-kpi-row {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
.waskita-card {{ flex: 1; min-width: 200px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }}
.waskita-card h4 {{ margin: 0 0 8px 0; font-size: 12px; color: #64748b; font-weight: 700; text-transform: uppercase; }}
.waskita-card h2 {{ margin: 0; font-size: 32px; font-weight: 800; display: flex; align-items: baseline; gap: 5px; }}
.waskita-card h2 span {{ font-size: 20px; }}
.waskita-card p {{ margin: 8px 0 0 0; font-size: 12px; font-weight: 500; }}
.card-rencana {{ border-left: 5px solid #2563eb; }}
.card-rencana h2 {{ color: #2563eb; }}
.card-rencana p {{ color: #3b82f6; }}
.card-realisasi {{ border-left: 5px solid #16a34a; }}
.card-realisasi h2 {{ color: #16a34a; }}
.card-realisasi p {{ color: #22c55e; }}
.card-deviasi {{ border-left: 5px solid #dc2626; }}
.card-deviasi h2 {{ color: #dc2626; }}
.card-deviasi p {{ color: #ef4444; }}
.card-achv {{ background: #0f172a; border: none; }}
.card-achv h4 {{ color: #94a3b8; }}
.card-achv h2 {{ color: #f59e0b; }}
.card-achv p {{ color: #cbd5e1; }}
.waskita-table {{ width: 100%; border-collapse: collapse; font-size: 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
.waskita-table th {{ background: #0f172a; color: white; padding: 14px 15px; text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
.waskita-table td {{ padding: 12px 15px; border-bottom: 1px solid #e2e8f0; font-weight: 600; color: #1e293b !important; }}
.row-even {{ background: #fdfbf7; }}
.row-odd {{ background: #f8fafc; }}
.row-alert {{ background: #fef2f2; }}
.row-success {{ background: #f0fdf4; }}
.text-red {{ color: #dc2626 !important; font-weight: bold; }}
.text-green {{ color: #16a34a !important; font-weight: bold; }}
.text-gold {{ color: #d97706 !important; font-weight: bold; }}
</style>

<div class="waskita-dash">
<div class="waskita-header">
<div class="waskita-title">
<h2>DASHBOARD MONITORING PRODUKSI READYMIX & QUARRY</h2>
<p>Rekapitulasi Harian Operasional Batching Plant & Quarry — Data {tanggal_str}</p>
</div>
<div class="waskita-date">{tanggal_str}</div>
</div>
<div class="waskita-kpi-row">
<div class="waskita-card card-rencana">
<h4>TOTAL RENCANA TARGET</h4>
<h2>{total_rencana:,.0f} <span>m<sup>3</sup></span></h2>
<p>10 Unit Batching Plant & 1 Unit Quarry</p>
</div>
<div class="waskita-card card-realisasi">
<h4>REALISASI PRODUKSI</h4>
<h2>{total_realisasi:,.0f} <span>m<sup>3</sup></span></h2>
<p>Volume aktual tercatat</p>
</div>
<div class="waskita-card card-deviasi">
<h4>TOTAL DEVIASI</h4>
<h2>{total_deviasi:,.0f} <span>m<sup>3</sup></span></h2>
<p>Defisit terhadap target</p>
</div>
<div class="waskita-card card-achv">
<h4>OVERALL ACHIEVEMENT</h4>
<h2>{overall_achv:.1f}%</h2>
<p>Capaian harian keseluruhan</p>
</div>
</div>
<table class="waskita-table">
<tr>
<th>NAMA UNIT</th>
<th>RENCANA</th>
<th>REALISASI</th>
<th>DEVIASI</th>
<th>ACHV (%)</th>
</tr>
"""
    
    for idx, row in df.iterrows():
        unit = row.get('Nama Unit', '-')
        rencana = row.get('Rencana (m³)', 0)
        realisasi = row.get('Realisasi (m³)', 0)
        deviasi = row.get('Deviasi (m³)', 0)
        achv = row.get('Achv (%)', 0)
        
        str_rencana = f"{rencana:,.0f} m<sup>3</sup>" if rencana > 0 else "—"
        str_realisasi = f"{realisasi:,.0f} m<sup>3</sup>" if realisasi > 0 else "—"
        
        dev_class = "text-red" if deviasi < 0 else ("text-green" if deviasi >= 0 and rencana > 0 else "")
        str_deviasi = f"<span class='{dev_class}'>{deviasi:,.0f} m<sup>3</sup></span>" if (rencana > 0 or realisasi > 0) else "—"
        
        achv_class = "text-green" if achv >= 100 else ("text-gold" if achv >= 50 else "text-red")
        str_achv = f"<span class='{achv_class}'>{achv:.0f}%</span>"
        
        if rencana == 0 and realisasi == 0: row_class = "row-even"
        elif deviasi < 0: row_class = "row-alert"
        elif achv >= 100 and rencana > 0: row_class = "row-success"
        else: row_class = "row-odd"
            
        html_dashboard += f"""<tr class="{row_class}">
<td>{unit}</td>
<td>{str_rencana}</td>
<td>{str_realisasi}</td>
<td>{str_deviasi}</td>
<td>{str_achv}</td>
</tr>
"""
        
    html_dashboard += """</table>
<p style="font-size: 11px; color: #64748b; margin-top: 10px;">
Catatan: angka rencana/realisasi mengikuti data sumber. Deviasi total dihitung dari total rencana dikurangi realisasi.
</p>
</div>
"""
    
    st.markdown(html_dashboard, unsafe_allow_html=True)
    
    st.markdown("<br><h3>Detail Kendala & Mitigasi (Sesuai Status)</h3>", unsafe_allow_html=True)
    display_cols_2 = ['Nama Unit', 'Status', 'Issue / Kendala', 'Aksi Mitigasi']
    if 'Issue / Kendala' in df.columns:
        st.dataframe(df[display_cols_2].dropna(subset=['Issue / Kendala']).replace("", float("NaN")).dropna(), use_container_width=True)
    
    st.markdown("---")
    st.subheader("🖨️ Cetak & Simpan Laporan")
    
    df_export = df.copy()
    rumus_deviasi, rumus_achv, rumus_status = [], [], []
    
    for i in range(len(df_export)):
        baris_excel = i + 2
        rumus_deviasi.append(f'=D{baris_excel}-C{baris_excel}')
        rumus_achv.append(f'=IFERROR(D{baris_excel}/C{baris_excel},0)')
        rumus_status.append(f'=IF(AND(C{baris_excel}=0,D{baris_excel}=0),"Critical",IF(D{baris_excel}>=C{baris_excel},"Optimal",IF(D{baris_excel}/C{baris_excel}>=0.5,"Warning","Critical")))')
        
    df_export['Deviasi (m³)'] = rumus_deviasi
    df_export['Achv (%)'] = rumus_achv
    df_export['Status'] = rumus_status

    excel_file = f"Data_Produksi_{tanggal_str.replace(' ', '_')}.xlsx"
    with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name=tanggal_str[:31])
    
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        with open(excel_file, "rb") as file:
            st.download_button(
                label="💾 Download File Excel (Otomatis Rumus)",
                data=file,
                file_name=excel_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    with col_dl2:
        if st.button("🖨️ Generate Laporan PDF", use_container_width=True):
            with st.spinner("Membangun file PDF..."):
                html_pdf = f"""
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; color: #333; }}
                        .header {{ text-align: center; color: #1a457b; margin-bottom: 5px; }}
                        .subheader {{ text-align: center; color: #666; margin-top: 0px; font-size: 14px; margin-bottom: 20px; }}
                        .box-container {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
                        th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: center; }}
                        th {{ background-color: #1a457b; color: white; }}
                        .legend-table {{ width: 100%; border: none; margin-top: 20px; font-size: 11px; text-align: left; }}
                        .legend-table td {{ border: none; padding: 3px; text-align: left; vertical-align: top; }}
                    </style>
                </head>
                <body>
                    <h2 class="header">DASHBOARD MONITORING PRODUKSI READYMIX & QUARRY</h2>
                    <p class="subheader">Rekapitulasi Harian Operasional - Data {tanggal_str}</p>
                    <div style="width: 100%; display: table;">
                        <div style="display: table-cell; width: 33%; text-align: center; border: 1px solid #000; padding: 5px;">
                            <h4 style="margin:5px 0;">TOTAL RENCANA</h4><h2 style="color:blue; margin:5px 0;">{total_rencana:,.0f} m³</h2>
                        </div>
                        <div style="display: table-cell; width: 33%; text-align: center; border: 1px solid #000; padding: 5px;">
                            <h4 style="margin:5px 0;">REALISASI PRODUKSI</h4><h2 style="color:green; margin:5px 0;">{total_realisasi:,.0f} m³</h2>
                        </div>
                        <div style="display: table-cell; width: 33%; text-align: center; border: 1px solid #000; padding: 5px;">
                            <h4 style="margin:5px 0;">TOTAL DEVIASI</h4><h2 style="color:red; margin:5px 0;">{total_deviasi:,.0f} m³</h2>
                        </div>
                    </div>
                    <h3 style="text-align:center; margin-top: 15px;">OVERALL ACHIEVEMENT: {overall_achv:.1f}%</h3>
                    <table>
                        <tr><th style="width: 15%">NAMA UNIT</th><th>RENCANA</th><th>REALISASI</th><th>DEVIASI</th><th>ACHV</th><th>STATUS</th><th style="width: 20%">KENDALA</th><th style="width: 20%">MITIGASI</th></tr>
                """
                for idx, row in df.iterrows():
                    unit = row.get('Nama Unit', '-')
                    rencana = row.get('Rencana (m³)', 0)
                    realisasi = row.get('Realisasi (m³)', 0)
                    deviasi = row.get('Deviasi (m³)', 0)
                    achv = row.get('Achv (%)', 0)
                    status = row.get('Status', '-')
                    kendala, mitigasi = str(row.get('Issue / Kendala', '')), str(row.get('Aksi Mitigasi', ''))
                    if kendala == "nan": kendala = ""
                    if mitigasi == "nan": mitigasi = ""
                    
                    html_pdf += f"<tr><td>{unit}</td><td>{rencana:.0f}</td><td>{realisasi:.0f}</td><td>{deviasi:.0f}</td><td>{achv:.0f}%</td><td>{status}</td><td style='text-align:left; font-size:11px;'>{kendala}</td><td style='text-align:left; font-size:11px;'>{mitigasi}</td></tr>"
                    
                html_pdf += """
                    </table>
                    <table class="legend-table">
                        <tr><td style="width: 10%;"><strong>Catatan :</strong></td><td style="width: 12%;"><strong>Status Produksi</strong></td><td></td></tr>
                        <tr><td></td><td>Optimal</td><td>Kondisi produksi berjalan baik dan sesuai target yang ditetapkan.</td></tr>
                        <tr><td></td><td>Warning</td><td>Kondisi produksi menunjukkan potensi masalah yang dapat mengganggu pencapaian target.</td></tr>
                        <tr><td></td><td>Critical</td><td>Kondisi produksi mengalami permasalahan serius yang berpotensi menghambat atau menghentikan kegiatan produksi.</td></tr>
                    </table>
                </body>
                </html>
                """
                
                # AUTO DETECT OS (WINDOWS VS CLOUD/LINUX)
                if platform.system() == "Windows":
                    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
                else:
                    path_wkhtmltopdf = '/usr/bin/wkhtmltopdf' # Format Linux
                
                if not os.path.exists(path_wkhtmltopdf):
                    st.error(f"❌ Error: wkhtmltopdf tidak ditemukan di {path_wkhtmltopdf}.")
                else:
                    try:
                        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
                        pdf_file_path = f"Report_Produksi.pdf"
                        options = {'encoding': "UTF-8", 'page-size': 'A4', 'orientation': 'Landscape'}
                        pdfkit.from_string(html_pdf, pdf_file_path, configuration=config, options=options)
                        
                        with open(pdf_file_path, "rb") as pdf_file:
                            st.download_button(
                                label="⬇️ Download Hasil PDF",
                                data=pdf_file,
                                file_name=f"Report_Produksi_{tanggal_str.replace(' ', '_')}.pdf",
                                mime="application/pdf",
                                type="primary",
                                use_container_width=True
                            )
                        st.success("✅ PDF Laporan Harian berhasil dibuat! Silakan klik tombol Download di atas.")
                    except Exception as e:
                        st.error(f"Gagal saat membuat PDF: {e}")

# =====================================================================
# MODE 1: INPUT DATA HARIAN BARU
# =====================================================================
if mode == "📝 Input Data Harian Baru":
    st.title("📝 Input Data Produksi Harian")
    
    tanggal_input = st.date_input("Pilih Tanggal Produksi")
    tanggal_str = tanggal_input.strftime("%d %b %Y").upper()
    tanggal_excel = tanggal_input.strftime("%m/%d/%Y")

    if st.button("🔄 Tarik Data dari Database Server"):
        st.session_state.pop("daily_data", None)

    if "daily_data" not in st.session_state or st.session_state.get("last_date") != tanggal_excel:
        with st.spinner("Memeriksa data di server Supabase..."):
            try:
                response = supabase.table("report_produksi").select("*").eq("tanggal", tanggal_excel).execute()
                
                if response.data:
                    df_server = pd.DataFrame(response.data)
                    df_template = pd.DataFrame({"Nama Unit": UNIT_LIST})
                    df_merged = pd.merge(df_template, df_server, left_on="Nama Unit", right_on="nama_unit", how="left").fillna(0)
                    
                    st.session_state["daily_data"] = pd.DataFrame({
                        "Tanggal": [tanggal_excel] * len(UNIT_LIST),
                        "Nama Unit": UNIT_LIST,
                        "Rencana (m³)": df_merged["rencana"].astype(float),
                        "Realisasi (m³)": df_merged["realisasi"].astype(float),
                        "Deviasi (m³)": [0.0] * len(UNIT_LIST),
                        "Achv (%)": [0.0] * len(UNIT_LIST),
                        "Status": ["Critical"] * len(UNIT_LIST),
                        "Issue / Kendala": df_merged["kendala"].replace(0, ""),
                        "Aksi Mitigasi": df_merged["mitigasi"].replace(0, "")
                    })
                else:
                    st.session_state["daily_data"] = pd.DataFrame({
                        "Tanggal": [tanggal_excel] * len(UNIT_LIST),
                        "Nama Unit": UNIT_LIST,
                        "Rencana (m³)": [0.0] * len(UNIT_LIST),
                        "Realisasi (m³)": [0.0] * len(UNIT_LIST),
                        "Deviasi (m³)": [0.0] * len(UNIT_LIST),
                        "Achv (%)": [0.0] * len(UNIT_LIST),
                        "Status": ["Critical"] * len(UNIT_LIST),
                        "Issue / Kendala": [""] * len(UNIT_LIST),
                        "Aksi Mitigasi": [""] * len(UNIT_LIST)
                    })
            except Exception as e:
                st.error(f"Gagal mengambil data dari server: {e}")
                st.stop()
                
        st.session_state["last_date"] = tanggal_excel

    st.session_state["daily_data"]['Deviasi (m³)'] = st.session_state["daily_data"]['Realisasi (m³)'] - st.session_state["daily_data"]['Rencana (m³)']
    rencana_safe = st.session_state["daily_data"]['Rencana (m³)'].replace(0, pd.NA)
    st.session_state["daily_data"]['Achv (%)'] = (st.session_state["daily_data"]['Realisasi (m³)'] / rencana_safe * 100).fillna(0).astype(float)
    st.session_state["daily_data"]['Status'] = st.session_state["daily_data"].apply(
        lambda row: hitung_status(row['Rencana (m³)'], row['Realisasi (m³)'], row['Achv (%)']), axis=1
    )
    
    edited_df = st.data_editor(
        st.session_state["daily_data"],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "Tanggal": st.column_config.TextColumn(disabled=True),
            "Nama Unit": st.column_config.TextColumn(disabled=True),
            "Rencana (m³)": st.column_config.NumberColumn(default=0, min_value=0),
            "Realisasi (m³)": st.column_config.NumberColumn(default=0, min_value=0),
            "Deviasi (m³)": st.column_config.NumberColumn(disabled=True),
            "Achv (%)": st.column_config.NumberColumn(disabled=True, format="%.0f%%"),
            "Status": st.column_config.TextColumn(disabled=True),
            "Issue / Kendala": st.column_config.TextColumn(),
            "Aksi Mitigasi": st.column_config.TextColumn(),
        }
    )

    if not edited_df.equals(st.session_state["daily_data"]):
        st.session_state["daily_data"] = edited_df
        try: st.rerun()
        except AttributeError: st.experimental_rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    col_action1, col_action2 = st.columns(2)
    
    with col_action1:
        if st.button("☁️ Simpan ke Database Online", use_container_width=True):
            with st.spinner("Mengirim data ke Supabase..."):
                data_to_upsert = []
                for idx, row in edited_df.iterrows():
                    data_to_upsert.append({
                        "tanggal": row["Tanggal"],
                        "nama_unit": row["Nama Unit"],
                        "rencana": row["Rencana (m³)"],
                        "realisasi": row["Realisasi (m³)"],
                        "kendala": row["Issue / Kendala"],
                        "mitigasi": row["Aksi Mitigasi"]
                    })
                try:
                    supabase.table("report_produksi").upsert(data_to_upsert).execute()
                    st.success("✅ Data berhasil diamankan ke server Supabase!")
                except Exception as e:
                    st.error(f"❌ Gagal menyimpan ke server: {e}")

    with col_action2:
        if st.button("🚀 Proses & Tampilkan Dashboard", type="primary", use_container_width=True):
            st.session_state['df_hasil'] = edited_df
            st.session_state['tanggal_str'] = tanggal_str

    if 'df_hasil' in st.session_state:
        st.markdown("---")
        tampilkan_dashboard_dan_pdf(st.session_state['df_hasil'], st.session_state['tanggal_str'])


# =====================================================================
# MODE 2: CETAK DARI MASTER LAMA
# =====================================================================
elif mode == "📂 Cetak dari Master Excel Lama":
    st.title("📂 Generate Report dari File Excel Lama")
    uploaded_file = st.file_uploader("Upload File Master Excel", type=["xlsx"])
    if uploaded_file:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = [s for s in xls.sheet_names if "OKT" in s.upper() or "DATA" in s.upper()]
        if not sheet_names: st.warning("Tidak ada sheet yang mengandung format tanggal yang dikenali.")
        else:
            selected_sheet = st.selectbox("Pilih Sheet / Tanggal", sheet_names)
            try:
                df_raw = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
                df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=1) if 'Unnamed: 1' in df_raw.columns else df_raw
                df = df.dropna(subset=['Nama Unit'])
                df['Rencana (m³)'] = pd.to_numeric(df['Rencana (m³)'], errors='coerce').fillna(0)
                df['Realisasi (m³)'] = pd.to_numeric(df['Realisasi (m³)'], errors='coerce').fillna(0)
                if 'Deviasi (m³)' not in df.columns: df['Deviasi (m³)'] = df['Realisasi (m³)'] - df['Rencana (m³)']
                tampilkan_dashboard_dan_pdf(df, selected_sheet)
            except Exception as e: st.error(f"Terjadi kesalahan: {e}")