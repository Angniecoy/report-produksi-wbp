import streamlit as st
import pandas as pd
from xhtml2pdf import pisa
from io import BytesIO
import os
import platform
from datetime import datetime
from supabase import create_client, Client

# Konfigurasi Halaman (Wide)
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
    
    # Hitung Rekap Status Unit
    unit_tercapai = sum((df['Realisasi (m³)'] >= df['Rencana (m³)']) & (df['Rencana (m³)'] > 0))
    unit_produksi = sum(df['Realisasi (m³)'] > 0)

    # =========================================================
    # UI DASHBOARD CUSTOM - COLORFUL BUBBLE & GLASSMORPHISM
    # (CSS dipisah ke string biasa agar terhindar dari SyntaxError)
    # =========================================================
    css_dashboard = """
<style>
.waskita-dash { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; position: relative; padding: 40px; border-radius: 24px; background: #0f172a; overflow: hidden; margin-top: -20px; box-shadow: 0 20px 50px rgba(0,0,0,0.4); }

/* SHAPE BUBBLES ANIMATION */
.bubble { position: absolute; border-radius: 50%; filter: blur(60px); opacity: 0.5; z-index: 0; animation: float 10s ease-in-out infinite; }
.bubble-1 { width: 400px; height: 400px; background: linear-gradient(135deg, #ec4899, #8b5cf6); top: -100px; left: -100px; }
.bubble-2 { width: 500px; height: 500px; background: linear-gradient(135deg, #3b82f6, #06b6d4); bottom: -150px; right: -100px; animation-duration: 12s; animation-direction: reverse;}
.bubble-3 { width: 350px; height: 350px; background: linear-gradient(135deg, #f59e0b, #ef4444); top: 30%; left: 35%; animation-duration: 15s; opacity: 0.35; }

@keyframes float {
    0% { transform: translateY(0px) scale(1) rotate(0deg); }
    50% { transform: translateY(-30px) scale(1.05) rotate(5deg); }
    100% { transform: translateY(0px) scale(1) rotate(0deg); }
}

.content-wrapper { position: relative; z-index: 1; }

/* HEADER */
.waskita-header { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1px solid rgba(255, 255, 255, 0.15); padding-bottom: 20px; margin-bottom: 30px; }
.waskita-title h2 { margin: 0; color: #ffffff; font-size: 32px; font-weight: 900; letter-spacing: 1px; text-shadow: 0 4px 10px rgba(0,0,0,0.3); }
.waskita-title p { margin: 8px 0 0 0; color: #cbd5e1; font-size: 16px; font-weight: 500; }
.waskita-date { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(15px); color: #ffffff; padding: 12px 30px; border-radius: 30px; font-weight: 800; font-size: 16px; border: 1px solid rgba(255,255,255,0.2); box-shadow: 0 8px 20px rgba(0,0,0,0.2); }

/* KPI CARDS */
.waskita-kpi-row { display: flex; gap: 25px; margin-bottom: 40px; flex-wrap: wrap; }
.waskita-card { flex: 1; min-width: 200px; padding: 25px 25px; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.2); position: relative; overflow: hidden; transition: transform 0.3s ease; }
.waskita-card:hover { transform: translateY(-8px); }
.waskita-card h4 { margin: 0 0 10px 0; font-size: 13px; font-weight: 800; text-transform: uppercase; color: rgba(255,255,255,0.9); letter-spacing: 1px; }
.waskita-card h2 { margin: 0; font-size: 42px; font-weight: 900; color: #ffffff; display: flex; align-items: baseline; gap: 5px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
.waskita-card h2 span { font-size: 20px; color: rgba(255,255,255,0.9); font-weight: 700; }
.waskita-card p { margin: 12px 0 0 0; font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.8); }

.card-rencana { background: linear-gradient(135deg, #2563eb, #60a5fa); border: 1px solid rgba(59, 130, 246, 0.5); }
.card-realisasi { background: linear-gradient(135deg, #059669, #34d399); border: 1px solid rgba(16, 185, 129, 0.5); }
.card-deviasi { background: linear-gradient(135deg, #dc2626, #f87171); border: 1px solid rgba(239, 68, 68, 0.5); }
.card-achv { background: linear-gradient(135deg, #d97706, #fbbf24); border: 1px solid rgba(245, 158, 11, 0.5); }

/* GLASS TABLE */
.waskita-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 15px; border-radius: 16px; overflow: hidden; box-shadow: 0 15px 35px rgba(0,0,0,0.2); background: rgba(255,255,255,0.95); backdrop-filter: blur(15px); border: 1px solid rgba(255,255,255,0.5); }
.waskita-table th { background: #1e293b; color: #ffffff; padding: 18px 20px; text-align: left; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid #334155; }
.waskita-table td { padding: 16px 20px; border-bottom: 1px solid #e2e8f0; font-weight: 700; color: #0f172a; }

.row-even { background: rgba(255, 255, 255, 0.6); }
.row-odd { background: rgba(241, 245, 249, 0.8); }
.row-alert { background: rgba(254, 226, 226, 0.9); }
.row-success { background: rgba(220, 252, 231, 0.9); }

.text-red { color: #dc2626 !important; font-weight: 900; }
.text-green { color: #16a34a !important; font-weight: 900; }
.text-gold { color: #d97706 !important; font-weight: 900; }

/* GRID KENDALA (HALAMAN 2) */
.kendala-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 25px; margin-top: 25px; }
@media (max-width: 1200px) { .kendala-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 900px) { .kendala-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .kendala-grid { grid-template-columns: 1fr; } }

.k-card { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(15px); border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.15); overflow: hidden; display: flex; flex-direction: column; transition: transform 0.3s ease; border: 1px solid rgba(255,255,255,0.6); }
.k-card:hover { transform: translateY(-8px); box-shadow: 0 20px 40px rgba(0,0,0,0.25); }
.k-header { padding: 18px 20px; color: white; font-weight: 900; font-size: 17px; display: flex; justify-content: space-between; align-items: center; text-shadow: 1px 1px 3px rgba(0,0,0,0.3); border-bottom: 2px solid rgba(0,0,0,0.1); }
.bg-green { background: linear-gradient(135deg, #059669, #34d399); }
.bg-yellow { background: linear-gradient(135deg, #d97706, #fbbf24); }
.bg-red { background: linear-gradient(135deg, #dc2626, #f87171); }

.k-body { padding: 20px; font-size: 14px; color: #1e293b; flex-grow: 1; display: flex; flex-direction: column; gap: 12px; }
.k-meta { color: #475569; margin-bottom: 5px; font-weight: 800; border-bottom: 2px dashed #cbd5e1; padding-bottom: 12px; font-size: 13px; }
.k-label { font-weight: 900; font-size: 11px; color: #0f172a; text-transform: uppercase; letter-spacing: 1.5px; background: #e2e8f0; padding: 6px 10px; border-radius: 6px; display: inline-block; margin-bottom: 5px; }
.k-text { line-height: 1.6; font-weight: 600; padding-left: 5px; }
.k-label-mitigasi { font-weight: 900; font-size: 11px; color: #ffffff; text-transform: uppercase; letter-spacing: 1.5px; background: linear-gradient(135deg, #3b82f6, #60a5fa); padding: 6px 10px; border-radius: 6px; display: inline-block; margin-top: 8px; margin-bottom: 5px; box-shadow: 0 4px 10px rgba(59,130,246,0.3); }

.k-summary-card { background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 20px; padding: 30px; display: flex; align-items: center; justify-content: center; text-align: center; box-shadow: 0 15px 35px rgba(99, 102, 241, 0.4); border: 1px solid rgba(255,255,255,0.3); }
.k-summary-text { color: white; font-weight: 900; font-size: 18px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); letter-spacing: 1px; }
.k-legend { font-size: 13px; color: #f8fafc; margin-top: 15px; line-height: 1.8; font-weight: 600; background: rgba(0,0,0,0.3); padding: 20px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); backdrop-filter: blur(10px); }
</style>
"""

    html_dashboard = css_dashboard + f"""
<div class="waskita-dash">
    <!-- SHAPE BUBBLES -->
    <div class="bubble bubble-1"></div>
    <div class="bubble bubble-2"></div>
    <div class="bubble bubble-3"></div>
    
    <div class="content-wrapper">
        <!-- HALAMAN 1 -->
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
            
        html_dashboard += f"""
            <tr class="{row_class}">
                <td>{unit}</td>
                <td>{str_rencana}</td>
                <td>{str_realisasi}</td>
                <td>{str_deviasi}</td>
                <td>{str_achv}</td>
            </tr>
        """
        
    html_dashboard += f"""
        </table>
        <p style="font-size: 12px; color: rgba(255,255,255,0.6); margin-top: 15px; margin-bottom: 60px; font-weight: 500;">
        *Catatan: Angka rencana/realisasi mengikuti data sumber. Deviasi total dihitung dari total rencana dikurangi realisasi.
        </p>

        <!-- HALAMAN 2: KENDALA DAN MITIGASI GRID -->
        <div class="waskita-header">
            <div class="waskita-title">
                <h2>DETAIL KENDALA OPERASIONAL & MITIGASI (11 UNIT)</h2>
                <p>Evaluasi kendala dan tindak lanjut per unit — Data {tanggal_str}</p>
            </div>
            <div class="waskita-date">{tanggal_str}</div>
        </div>

        <div class="kendala-grid">
"""
    
    unit_no = 1
    for idx, row in df.iterrows():
        unit = row.get('Nama Unit', '-')
        rencana = row.get('Rencana (m³)', 0)
        realisasi = row.get('Realisasi (m³)', 0)
        deviasi = row.get('Deviasi (m³)', 0)
        achv = row.get('Achv (%)', 0)
        kendala = str(row.get('Issue / Kendala', ''))
        mitigasi = str(row.get('Aksi Mitigasi', ''))
        
        if kendala == "nan" or kendala.strip() == "": kendala = "-"
        if mitigasi == "nan" or mitigasi.strip() == "": mitigasi = "-"
        
        if achv >= 100 and rencana > 0: bg_class = "bg-green"
        elif achv >= 50: bg_class = "bg-yellow"
        else: bg_class = "bg-red"
            
        str_dev = f"{deviasi:,.0f} m³" if (rencana > 0 or realisasi > 0) else "— m³"
        str_tgt = f"{rencana:,.0f} m³" if rencana > 0 else "— m³"
        
        html_dashboard += f"""
            <div class="k-card">
                <div class="k-header {bg_class}">
                    <span>{unit_no}. {unit}</span>
                    <span>{achv:.0f}%</span>
                </div>
                <div class="k-body">
                    <div class="k-meta">Deviasi: <span style="color:#0f172a;">{str_dev}</span> &nbsp;|&nbsp; Target: <span style="color:#0f172a;">{str_tgt}</span></div>
                    <div>
                        <div class="k-label">KENDALA</div>
                        <div class="k-text">{kendala}</div>
                    </div>
                    <div>
                        <div class="k-label-mitigasi">MITIGASI</div>
                        <div class="k-text">{mitigasi}</div>
                    </div>
                </div>
            </div>
        """
        unit_no += 1

    html_dashboard += f"""
            <div style="display: flex; flex-direction: column; gap: 20px;">
                <div class="k-summary-card">
                    <span class="k-summary-text">{unit_tercapai} UNIT CAPAI TARGET<br><br>{unit_produksi} UNIT DENGAN REALISASI</span>
                </div>
                <div class="k-legend">
                    <strong>Status Warna Kartu:</strong><br>
                    🟢 Hijau = Sesuai / Tercapai Target<br>
                    🟡 Kuning = Perlu Perhatian (Achv > 50%)<br>
                    🔴 Merah = Kendala Kritis / Defisit
                </div>
            </div>
        </div>
    </div> <!-- Tutup content-wrapper -->
</div> <!-- Tutup waskita-dash -->
"""
    st.markdown(html_dashboard, unsafe_allow_html=True)
    
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
            with st.spinner("Membangun file PDF (2 Halaman)..."):
                css_pdf = """
                    <style>
                        @page { size: A4 landscape; margin: 1cm; }
                        body { font-family: Helvetica, Arial, sans-serif; color: #333; }
                        .header { text-align: center; color: #1a457b; margin-bottom: 5px; font-size: 20px; }
                        .subheader { text-align: center; color: #666; margin-top: 0px; font-size: 13px; margin-bottom: 15px; }
                        .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 15px; border: none; }
                        .kpi-td { width: 33%; text-align: center; border: 1px solid #1a457b; padding: 10px; }
                        .data-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; }
                        .data-table th, .data-table td { border: 1px solid #ddd; padding: 6px; text-align: center; }
                        .data-table th { background-color: #1a457b; color: white; }
                        .page-break { page-break-before: always; }
                        .k-table-grid { width: 100%; border-collapse: separate; border-spacing: 10px; }
                        .k-card-td { border: 1px solid #cbd5e1; border-radius: 4px; vertical-align: top; width: 25%; font-size: 9px; padding: 0; }
                        .k-head-td { padding: 6px; color: white; font-weight: bold; font-size: 10px; }
                        .bg-green { background-color: #059669; }
                        .bg-yellow { background-color: #d97706; }
                        .bg-red { background-color: #dc2626; }
                        .k-body-td { padding: 8px; }
                        .k-meta-td { color: #64748b; margin-bottom: 4px; font-size: 8px; }
                        .k-label-td { font-weight: bold; color: #0f172a; margin-bottom: 2px; }
                        .k-label-mitigasi-td { font-weight: bold; color: #2563eb; margin-top: 4px; margin-bottom: 2px; }
                    </style>
                """
                
                html_pdf = f"""
                <html>
                <head>
                    <meta charset="UTF-8">
                    {css_pdf}
                </head>
                <body>
                    <!-- HALAMAN 1 PDF -->
                    <h2 class="header">DASHBOARD MONITORING PRODUKSI READYMIX & QUARRY</h2>
                    <p class="subheader">Rekapitulasi Harian Operasional - Data {tanggal_str}</p>
                    
                    <table class="kpi-table">
                        <tr>
                            <td class="kpi-td">
                                <h4 style="margin:0; color:#666;">TOTAL RENCANA</h4>
                                <h2 style="color:blue; margin:5px 0;">{total_rencana:,.0f} m&sup3;</h2>
                            </td>
                            <td class="kpi-td">
                                <h4 style="margin:0; color:#666;">REALISASI PRODUKSI</h4>
                                <h2 style="color:green; margin:5px 0;">{total_realisasi:,.0f} m&sup3;</h2>
                            </td>
                            <td class="kpi-td">
                                <h4 style="margin:0; color:#666;">TOTAL DEVIASI</h4>
                                <h2 style="color:red; margin:5px 0;">{total_deviasi:,.0f} m&sup3;</h2>
                            </td>
                        </tr>
                    </table>
                    
                    <h3 style="text-align:center; margin-top: 5px; margin-bottom: 10px;">OVERALL ACHIEVEMENT: {overall_achv:.1f}%</h3>
                    
                    <table class="data-table">
                        <tr>
                            <th style="width: 15%">NAMA UNIT</th>
                            <th>RENCANA</th>
                            <th>REALISASI</th>
                            <th>DEVIASI</th>
                            <th>ACHV</th>
                            <th>STATUS</th>
                            <th style="width: 25%">KENDALA</th>
                            <th style="width: 25%">MITIGASI</th>
                        </tr>
                """
                for idx, row in df.iterrows():
                    unit = row.get('Nama Unit', '-')
                    rencana = row.get('Rencana (m³)', 0)
                    realisasi = row.get('Realisasi (m³)', 0)
                    deviasi = row.get('Deviasi (m³)', 0)
                    achv = row.get('Achv (%)', 0)
                    status = row.get('Status', '-')
                    kendala = str(row.get('Issue / Kendala', '')).replace("nan", "")
                    mitigasi = str(row.get('Aksi Mitigasi', '')).replace("nan", "")
                    html_pdf += f"<tr><td>{unit}</td><td>{rencana:.0f}</td><td>{realisasi:.0f}</td><td>{deviasi:.0f}</td><td>{achv:.0f}%</td><td>{status}</td><td style='text-align:left;'>{kendala}</td><td style='text-align:left;'>{mitigasi}</td></tr>"
                
                html_pdf += "</table>"
                
                # HALAMAN 2 PDF
                html_pdf += f"""
                    <div class="page-break"></div>
                    <h2 class="header">DETAIL KENDALA OPERASIONAL & MITIGASI (11 UNIT)</h2>
                    <p class="subheader">Evaluasi kendala dan tindak lanjut per unit — Data {tanggal_str}</p>
                    <table class="k-table-grid">
                """
                
                col_count = 0
                html_pdf += "<tr>"
                unit_no = 1
                for idx, row in df.iterrows():
                    unit = row.get('Nama Unit', '-')
                    rencana = row.get('Rencana (m³)', 0)
                    realisasi = row.get('Realisasi (m³)', 0)
                    deviasi = row.get('Deviasi (m³)', 0)
                    achv = row.get('Achv (%)', 0)
                    kendala = str(row.get('Issue / Kendala', '')).replace("nan", "")
                    mitigasi = str(row.get('Aksi Mitigasi', '')).replace("nan", "")
                    if kendala.strip() == "": kendala = "-"
                    if mitigasi.strip() == "": mitigasi = "-"
                    
                    if achv >= 100 and rencana > 0: bg_class = "bg-green"
                    elif achv >= 50: bg_class = "bg-yellow"
                    else: bg_class = "bg-red"
                        
                    str_dev = f"{deviasi:,.0f} m&sup3;" if (rencana > 0 or realisasi > 0) else "&mdash; m&sup3;"
                    str_tgt = f"{rencana:,.0f} m&sup3;" if rencana > 0 else "&mdash; m&sup3;"
                    
                    if col_count == 4:
                        html_pdf += "</tr><tr>"
                        col_count = 0
                        
                    html_pdf += f"""
                        <td class="k-card-td">
                            <div class="k-head-td {bg_class}">
                                <span style="float:left;">{unit_no}. {unit}</span>
                                <span style="float:right;">{achv:.0f}%</span>
                                <div style="clear:both;"></div>
                            </div>
                            <div class="k-body-td">
                                <div class="k-meta-td">Deviasi: {str_dev} | Target: {str_tgt}</div>
                                <div class="k-label-td">KENDALA</div>
                                <div>{kendala}</div>
                                <div class="k-label-mitigasi-td">MITIGASI</div>
                                <div>{mitigasi}</div>
                            </div>
                        </td>
                    """
                    col_count += 1
                    unit_no += 1
                    
                if col_count == 4:
                    html_pdf += "</tr><tr>"
                
                html_pdf += f"""
                        <td class="k-card-td" style="border: none;">
                            <div style="border: 1px solid #fca5a5; background-color: #fef2f2; color: #dc2626; font-weight: bold; text-align: center; padding: 10px; border-radius: 4px; font-size: 10px;">
                                {unit_tercapai} UNIT CAPAI TARGET |<br>{unit_produksi} UNIT DGN REALISASI
                            </div>
                            <div style="color: #64748b; font-size: 8px; margin-top: 10px;">
                                Status warna:<br>
                                - hijau = sesuai/tercapai<br>
                                - kuning = perlu perhatian<br>
                                - merah = kendala kritis/defisit
                            </div>
                        </td>
                    </tr>
                    </table>
                </body>
                </html>
                """
                
                pdf_buffer = BytesIO()
                pisa_status = pisa.CreatePDF(html_pdf, dest=pdf_buffer)
                
                if not pisa_status.err:
                    st.download_button(
                        label="⬇️ Download Laporan PDF (2 Halaman)",
                        data=pdf_buffer.getvalue(),
                        file_name=f"Report_Produksi_{tanggal_str.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                    st.success("✅ PDF 2 Halaman berhasil dibuat! Silakan klik tombol Download di atas.")
                else:
                    st.error("❌ Terjadi kesalahan saat memproses pembuatan PDF.")

# =====================================================================
# MODE 1: INPUT DATA HARIAN BARU
# =====================================================================
if mode == "📝 Input Data Harian Baru":
    st.title("📝 Input Data Produksi Harian")
    
    tanggal_input = st.date_input("Pilih Tanggal Produksi")
    tanggal_str = tanggal_input.strftime("%d %b %Y").upper()
    tanggal_excel = tanggal_input.strftime("%m/%d/%Y")

    col_top1, col_top2 = st.columns([3, 1])
    with col_top2:
        if st.button("🔄 Tarik Data dari Database Server", use_container_width=True):
            st.session_state.pop("daily_data", None)
            st.session_state.pop("df_hasil", None)
            st.rerun()

    if "last_date" in st.session_state and st.session_state["last_date"] != tanggal_excel:
        st.session_state.pop("daily_data", None)
        st.session_state.pop("df_hasil", None)

    if "daily_data" not in st.session_state:
        with st.spinner("Memeriksa data di server Supabase..."):
            try:
                response = supabase.table("report_produksi").select("*").eq("tanggal", tanggal_excel).execute()
                
                if response.data:
                    df_server = pd.DataFrame(response.data)
                    df_server = df_server.drop_duplicates(subset=['nama_unit'], keep='last')
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
    
    st.markdown("💡 *Kolom Deviasi, Achv, dan Status akan terhitung otomatis saat Anda mengetik.*")
    
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
                    supabase.table("report_produksi").delete().eq("tanggal", tanggal_excel).execute()
                    supabase.table("report_produksi").insert(data_to_upsert).execute()
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
# MODE 2: CETAK DARI MASTER EXCEL LAMA
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
            
            if "last_sheet" in st.session_state and st.session_state["last_sheet"] != selected_sheet:
                st.session_state.pop("df_hasil", None)
            st.session_state["last_sheet"] = selected_sheet
            
            try:
                df_raw = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
                df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=1) if 'Unnamed: 1' in df_raw.columns else df_raw
                df = df.dropna(subset=['Nama Unit'])
                df['Rencana (m³)'] = pd.to_numeric(df['Rencana (m³)'], errors='coerce').fillna(0)
                df['Realisasi (m³)'] = pd.to_numeric(df['Realisasi (m³)'], errors='coerce').fillna(0)
                if 'Deviasi (m³)' not in df.columns: df['Deviasi (m³)'] = df['Realisasi (m³)'] - df['Rencana (m³)']
                
                if st.button("🚀 Proses & Tampilkan Dashboard", type="primary", use_container_width=True):
                    st.session_state['df_hasil'] = df
                    st.session_state['tanggal_str'] = selected_sheet
                
                if 'df_hasil' in st.session_state:
                    tampilkan_dashboard_dan_pdf(st.session_state['df_hasil'], st.session_state['tanggal_str'])
                    
            except Exception as e: st.error(f"Terjadi kesalahan: {e}")