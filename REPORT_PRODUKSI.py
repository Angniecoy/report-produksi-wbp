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
        if st.button("🔄 Tarik Data dari Server", use_container_width=True):
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
                    
                    # Tentukan status default berdasarkan data server jika ada
                    default_statuses = []
                    for _, row in df_merged.iterrows():
                        r = float(row.get("rencana", 0))
                        re = float(row.get("realisasi", 0))
                        ac = (re / r * 100) if r > 0 else 0
                        default_statuses.append(hitung_status(r, re, ac))

                    st.session_state["daily_data"] = pd.DataFrame({
                        "Tanggal": [tanggal_excel] * len(UNIT_LIST),
                        "Nama Unit": UNIT_LIST,
                        "Rencana (m³)": df_merged["rencana"].astype(float),
                        "Realisasi (m³)": df_merged["realisasi"].astype(float),
                        "Deviasi (m³)": [0.0] * len(UNIT_LIST),
                        "Achv (%)": [0.0] * len(UNIT_LIST),
                        "Status": default_statuses,
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

    if role_user == "Admin Unit / Plant":
        df_editable = st.session_state["daily_data"][st.session_state["daily_data"]["Nama Unit"] == selected_unit_filter].copy()
    else:
        df_editable = st.session_state["daily_data"]

    df_editable['Deviasi (m³)'] = df_editable['Realisasi (m³)'] - df_editable['Rencana (m³)']
    rencana_safe = df_editable['Rencana (m³)'].replace(0, pd.NA)
    df_editable['Achv (%)'] = (df_editable['Realisasi (m³)'] / rencana_safe * 100).fillna(0).astype(float)
    
    # Status otomatis dihitung, tetapi jika user sudah mengubahnya secara manual di data_editor, pertahankan pilihan user
    # (Streamlit data_editor akan menangkap perubahan dari kolom Status jika tidak di-disable)
    
    st.markdown(f"💡 *Anda sedang mengisi data untuk tanggal **{tanggal_str}**.*")
    
    edited_df_part = st.data_editor(
        df_editable,
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
            # Kolom Status diubah menjadi Selectbox agar bisa diedit secara manual (Optimal, Warning, Critical)
            "Status": st.column_config.SelectboxColumn(
                options=["Optimal", "Warning", "Critical"],
                required=True
            ),
            "Issue / Kendala": st.column_config.TextColumn(),
            "Aksi Mitigasi": st.column_config.TextColumn(),
        }
    )