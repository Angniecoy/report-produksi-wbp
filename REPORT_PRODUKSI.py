import streamlit as st
import pandas as pd
from xhtml2pdf import pisa
from io import BytesIO
import os
import platform
import base64
import urllib.parse
from datetime import datetime
from supabase import create_client, Client

# Konfigurasi Halaman (Wide)
st.set_page_config(page_title="Report Produksi Readymix & Quarry", layout="wide", initial_sidebar_state="collapsed")

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

# --- FUNGSI HELPER UNTUK BASE64 GAMBAR ---
def get_image_base64(filepath):
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8")
    return ""

# =====================================================================
# SISTEM HAK AKSES DENGAN PASSWORD ADMIN PUSAT
# =====================================================================
st.sidebar.title("🔐 Hak Akses & Login")
role_user = st.sidebar.selectbox("Pilih Peran (Role):", ["Admin Pusat / QSHE", "Admin Unit / Plant"])

if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

selected_unit_filter = "Semua Unit"

if role_user == "Admin Pusat / QSHE":
    if not st.session_state["admin_authenticated"]:
        password_input = st.sidebar.text_input("Masukkan Password Pusat:", type="password")
        if st.sidebar.button("Login"):
            if password_input == "Waskita2026": 
                st.session_state["admin_authenticated"] = True
                st.sidebar.success("Login Berhasil!")
                st.rerun()
            else:
                st.sidebar.error("Password Salah!")
        st.stop()
    else:
        st.sidebar.success("Anda masuk sebagai: **Admin Pusat / QSHE** (Akses Penuh)")
        if st.sidebar.button("Logout"):
            st.session_state["admin_authenticated"] = False
            st.rerun()
elif role_user == "Admin Unit / Plant":
    st.session_state["admin_authenticated"] = False
    selected_unit_filter = st.sidebar.selectbox("Pilih Unit Anda:", UNIT_LIST)
    st.sidebar.warning(f"Anda masuk sebagai pengelola unit: **{selected_unit_filter}**")

st.sidebar.markdown("---")
st.sidebar.title("Navigasi Menu")
mode = st.sidebar.radio("Pilih Mode Aplikasi:", [
    "📝 Input Data Harian Baru", 
    "📈 Grafik Analitik & Tren", 
    "📂 Arsip & Riwayat Laporan",
    "📂 Cetak dari Master Excel Lama"
])
st.sidebar.markdown("---")
st.sidebar.info("Aplikasi Report Produksi Readymix & Quarry - Waskita Beton Precast")

def hitung_status(rencana, realisasi, achv):
    if rencana == 0 and realisasi == 0: return "Critical"
    elif realisasi >= rencana: return "Optimal"
    elif achv >= 50: return "Warning"
    else: return "Critical"

def tampilkan_dashboard_dan_pdf(df, tanggal_str):
    df['Rencana (m³)'] = pd.to_numeric(df['Rencana (m³)'], errors='coerce').fillna(0)
    df['Realisasi (m³)'] = pd.to_numeric(df['Realisasi (m³)'] , errors='coerce').fillna(0)
    if 'Deviasi (m³)' not in df.columns:
        df['Deviasi (m³)'] = df['Realisasi (m³)'] - df['Rencana (m³)']
    
    total_rencana = df['Rencana (m³)'].sum()
    total_realisasi = df['Realisasi (m³)'] .sum()
    total_deviasi = total_realisasi - total_rencana
    overall_achv = (total_realisasi / total_rencana * 100) if total_rencana > 0 else 0
    
    unit_tercapai = sum((df['Realisasi (m³)'] >= df['Rencana (m³)']) & (df['Rencana (m³)'] > 0))
    unit_produksi = sum(df['Realisasi (m³)'] > 0)

    css_dashboard = """
<style>
.waskita-dash { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; position: relative; padding: 40px; border-radius: 24px; background: #0f172a; overflow: hidden; margin-top: -20px; box-shadow: 0 20px 50px rgba(0,0,0,0.4); }
.bubble { position: absolute; border-radius: 50%; filter: blur(60px); opacity: 0.5; z-index: 0; animation: float 10s ease-in-out infinite; }
.bubble-1 { width: 400px; height: 400px; background: linear-gradient(135deg, #ec4899, #8b5cf6); top: -100px; left: -100px; }
.bubble-2 { width: 500px; height: 500px; background: linear-gradient(135deg, #3b82f6, #06b6d4); bottom: -150px; right: -100px; animation-duration: 12s; animation-direction: reverse;}
.bubble-3 { width: 350px; height: 350px; background: linear-gradient(135deg, #f59e0b, #ef4444); top: 30%; left: 35%; animation-duration: 15s; opacity: 0.35; }
@keyframes float { 0% { transform: translateY(0px) scale(1) rotate(0deg); } 50% { transform: translateY(-30px) scale(1.05) rotate(5deg); } 100% { transform: translateY(0px) scale(1) rotate(0deg); } }
.content-wrapper { position: relative; z-index: 1; }
.waskita-kpi-row { display: flex; gap: 25px; margin-bottom: 40px; flex-wrap: wrap; margin-top: 20px; }
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
.kendala-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 25px; margin-top: 25px; }
@media (max-width: 1200px) { .kendala-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 900px) { .kendala-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .kendala-grid { grid-template-columns: 1fr; } }
.k-card { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(15px); border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.15); overflow: hidden; display: flex; flex-direction: column; border: 1px solid rgba(255,255,255,0.6); }
.k-header { padding: 18px 20px; color: white; font-weight: 900; font-size: 17px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid rgba(0,0,0,0.1); }
.bg-green { background: linear-gradient(135deg, #059669, #34d399); }
.bg-yellow { background: linear-gradient(135deg, #d97706, #fbbf24); }
.bg-red { background: linear-gradient(135deg, #dc2626, #f87171); }
.k-body { padding: 20px; font-size: 14px; color: #1e293b; flex-grow: 1; display: flex; flex-direction: column; gap: 12px; }
.k-meta { color: #475569; margin-bottom: 5px; font-weight: 800; border-bottom: 2px dashed #cbd5e1; padding-bottom: 12px; font-size: 13px; }
.k-label { font-weight: 900; font-size: 11px; color: #0f172a; text-transform: uppercase; background: #e2e8f0; padding: 6px 10px; border-radius: 6px; display: inline-block; margin-bottom: 5px; }
.k-text { line-height: 1.6; font-weight: 600; padding-left: 5px; }
.k-label-mitigasi { font-weight: 900; font-size: 11px; color: #ffffff; text-transform: uppercase; background: linear-gradient(135deg, #3b82f6, #60a5fa); padding: 6px 10px; border-radius: 6px; display: inline-block; margin-top: 8px; margin-bottom: 5px; }
.k-summary-card { background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 20px; padding: 30px; display: flex; align-items: center; justify-content: center; text-align: center; }
.k-summary-text { color: white; font-weight: 900; font-size: 18px; letter-spacing: 1px; }
.k-legend { font-size: 13px; color: #f8fafc; margin-top: 15px; line-height: 1.8; font-weight: 600; background: rgba(0,0,0,0.3); padding: 20px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); }
</style>
"""

    if os.path.exists("header_1.png"):
        st.image("header_1.png", use_container_width=True)
    else:
        st.info("💡 Tip: Upload file 'header_1.png' dan 'header_2.png' ke repository GitHub Anda.")

    html_dashboard = css_dashboard + f"""
<div class="waskita-dash">
<div class="bubble bubble-1"></div>
<div class="bubble bubble-2"></div>
<div class="bubble bubble-3"></div>
<div class="content-wrapper">
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
</div>
</div>
</div>
"""
    st.markdown(html_dashboard, unsafe_allow_html=True)

    if os.path.exists("header_2.png"):
        st.image("header_2.png", use_container_width=True)

    html_grid_kendala = f"""
<style>
.kendala-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 25px; margin-top: 25px; }}
@media (max-width: 1200px) {{ .kendala-grid {{ grid-template-columns: repeat(3, 1fr); }} }}
@media (max-width: 900px) {{ .kendala-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
@media (max-width: 600px) {{ .kendala-grid {{ grid-template-columns: 1fr; }} }}
.k-card {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(15px); border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.15); overflow: hidden; display: flex; flex-direction: column; border: 1px solid rgba(255,255,255,0.6); }}
.k-header {{ padding: 18px 20px; color: white; font-weight: 900; font-size: 17px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid rgba(0,0,0,0.1); }}
.bg-green {{ background: linear-gradient(135deg, #059669, #34d399); }}
.bg-yellow {{ background: linear-gradient(135deg, #d97706, #fbbf24); }}
.bg-red {{ background: linear-gradient(135deg, #dc2626, #f87171); }}
.k-body {{ padding: 20px; font-size: 14px; color: #1e293b; flex-grow: 1; display: flex; flex-direction: column; gap: 12px; }}
.k-meta {{ color: #475569; margin-bottom: 5px; font-weight: 800; border-bottom: 2px dashed #cbd5e1; padding-bottom: 12px; font-size: 13px; }}
.k-label {{ font-weight: 900; font-size: 11px; color: #0f172a; text-transform: uppercase; background: #e2e8f0; padding: 6px 10px; border-radius: 6px; display: inline-block; margin-bottom: 5px; }}
.k-text {{ line-height: 1.6; font-weight: 600; padding-left: 5px; }}
.k-label-mitigasi {{ font-weight: 900; font-size: 11px; color: #ffffff; text-transform: uppercase; background: linear-gradient(135deg, #3b82f6, #60a5fa); padding: 6px 10px; border-radius: 6px; display: inline-block; margin-top: 8px; margin-bottom: 5px; }}
.k-summary-card {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 20px; padding: 30px; display: flex; align-items: center; justify-content: center; text-align: center; }}
.k-summary-text { color: white; font-weight: 900; font-size: 18px; letter-spacing: 1px; }
.k-legend { font-size: 13px; color: #f8fafc; margin-top: 15px; line-height: 1.8; font-weight: 600; background: rgba(0,0,0,0.3); padding: 20px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); }
</style>
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
        
        html_grid_kendala += f"""
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

    html_grid_kendala += f"""
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
"""
    st.markdown(html_grid_kendala, unsafe_allow_html=True)
    
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
    
    col_dl1, col_dl2, col_dl3 = st.columns(3)
    with col_dl1:
        with open(excel_file, "rb") as file:
            st.download_button(
                label="💾 Download Excel",
                data=file,
                file_name=excel_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )