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
    df['Realisasi (m³)'] = pd.to_numeric(df['Realisasi (m³)'] , errors='coerce').fillna(0)
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
    # =========================================================
    html_dashboard = f"""
<style>
.waskita-dash {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; position: relative; padding: 40px; border-radius: 24px; background: #0f172a; overflow: hidden; margin-top: -20px; box-shadow: 0 20px 50px rgba(0,0,0,0.4); }}
.bubble {{ position: absolute; border-radius: 50%; filter: blur(60px); opacity: 0.5; z-index: 0; animation: float 10s ease-in-out infinite; }}
.bubble-1 {{ width: 400px; height: 400px; background: linear-gradient(135deg, #ec4899, #8b5cf6); top: -100px; left: -100px; }}
.bubble-2 {{ width: 500px; height: 500px; background: linear-gradient(135deg, #3b82f6, #06b6d4); bottom: -150px; right: -100px; animation-duration: 12s; animation-direction: reverse;}}
.bubble-3 {{ width: 350px; height: 350px; background: linear-gradient(135deg, #f59e0b, #ef4444); top: 30%; left: 35%; animation-duration: 15s; opacity: 0.35; }}
@keyframes float {{
0% {{ transform: translateY(0px) scale(1) rotate(0deg); }}
50% {{ transform: translateY(-30px) scale(1.05) rotate(5deg); }}
100% {{ transform: translateY(0px) scale(1) rotate(0deg); }}
}}
.content-wrapper {{ position: relative; z-index: 1; }}
.waskita-header {{ display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1px solid rgba(255, 255, 255, 0.15); padding-bottom: 20px; margin-bottom: 30px; }}
.waskita-title h2 {{ margin: 0; color: #ffffff; font-size: 32px; font-weight: 900; letter-spacing: 1px; text-shadow: 0 4px 10px rgba(0,0,0,0.3); }}
.waskita-title p {{ margin: 8px 0 0 0; color: #cbd5e1; font-size: 16px; font-weight: 500; }}
.waskita-date {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(15px); color: #ffffff; padding: 12px 30px; border-radius: 30px; font-weight: 800; font-size: 16px; border: 1px solid rgba(255,255,255,0.2); box-shadow: 0 8px 20px rgba(0,0,0,0.2); }}
.waskita-kpi-row {{ display: flex; gap: 25px; margin-bottom: 40px; flex-wrap: wrap; }}
.waskita-card {{ flex: 1; min-width: 200px; padding: 25px 25px; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.2); position: relative; overflow: hidden; transition: transform 0.3s ease; }}
.waskita-card:hover {{ transform: translateY(-8px); }}
.waskita-card h4 {{ margin: 0 0 10px 0; font-size: 13px; font-weight: 800; text-transform: uppercase; color: rgba(255,255,255,0.9); letter-spacing: 1px; }}
.waskita-card h2 {{ margin: 0; font-size: 42px; font-weight: 900; color: #ffffff; display: flex; align-items: baseline; gap: 5px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }}
.waskita-card h2 span {{ font-size: 20px; color: rgba(255,255,255,0.9); font-weight: 700; }}
.waskita-card p {{ margin: 12px 0 0 0; font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.8); }}
.card-rencana {{ background: linear-gradient(135deg, #2563eb, #60a5fa); border: 1px solid rgba(59, 130, 246, 0.5); }}
.card-realisasi {{ background: linear-gradient(135deg, #059669, #34d399); border: 1px solid rgba(16, 185, 129, 0.5); }}
.card-deviasi {{ background: linear-gradient(135deg, #dc2626, #f87171); border: 1px solid rgba(239, 68, 68, 0.5); }}
.card-achv {{ background: linear-gradient(135deg, #d97706, #fbbf24); border: 1px solid rgba(245, 158, 11, 0.5); }}
.waskita-table {{ width: 100%; border-collapse: separate; border-spacing: 0; font-size: 15px; border-radius: 16px; overflow: hidden; box-shadow: 0 15px 35px rgba(0,0,0,0.2); background: rgba(255,255,255,0.95); backdrop-filter: blur(15px); border: 1px solid rgba(255,255,255,0.5); }}
.waskita-table th {{ background: #1e293b; color: #ffffff; padding: 18px 20px; text-align: left; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid #334155; }}
.waskita-table td {{ padding: 16px 20px; border-bottom: 1px solid #e2e8f0; font-weight: 700; color: #0f172a; }}
.row-even {{ background: rgba(255, 255, 255, 0.6); }}
.row-odd {{ background: rgba(241, 245, 249, 0.8); }}
.row-alert {{ background: rgba(254, 226, 226, 0.9); }}
.row-success {{ background: rgba(220, 252, 231, 0.9); }}
.text-red {{ color: #dc2626 !important; font-weight: 900; }}
.text-green {{ color: #16a34a !important; font-weight: 900; }}
.text-gold {{ color: #d97706 !important; font-weight: 900; }}
.kendala-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 25px; margin-top: 25px; }}
@media (max-width: 1200px) {{ .kendala-grid {{ grid-template-columns: repeat(3, 1fr); }} }}
@media (max-width: 900px) {{ .kendala-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
@media (max-width: 600px) {{ .kendala-grid {{ grid-template-columns