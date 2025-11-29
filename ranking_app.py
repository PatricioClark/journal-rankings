import streamlit as st

from journal_ranking import get_journal_categories, get_scimago_ranking

# --- UI Layout ---
st.set_page_config(page_title="SJR Scraper", page_icon="📚")
st.title("📚 Journal Ranking Finder")
st.markdown("Get specific ranking and percentiles from SCImago.")

# Data entry
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    j_name = st.text_input("Journal Name", placeholder="e.g. IEEE Transactions on...")
with col2:
    j_cate = st.text_input("Category id", help="Run 'Get Category' to view categories' id's for selected journal")
with col3:
    j_year = st.text_input("Year", help="Leave empty for latest")

# Buttons and display
col1, col2 = st.columns(2)
data = False
cats = False
rank = False
with col1:
    if st.button("Get Categories", type="primary"):
        cats = True
        if j_name:
            journal, data = get_journal_categories(j_name)
        else:
            st.warning("Please enter a journal name.")

with col2:
    if st.button("Get Rankings", type="primary"):
        rank = True
        if j_name:
            data = get_scimago_ranking(j_name, j_cate, j_year)
        else:
            st.warning("Please enter a journal name.")

if data and cats:
    st.write(f'Showing categories for "{journal}"')
    st.dataframe(data,
                 hide_index=True,
                 use_container_width=True)

if data and rank:
    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
    )
