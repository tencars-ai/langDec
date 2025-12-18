import streamlit as st
import psycopg

st.set_page_config(page_title="Language Prototype", layout="centered")
st.title("Languagr Prototype ✅")
st.write("Hello World – Streamlit + Supabase Postgres")

db_url = st.secrets.get("DATABASE_URL")
if not db_url:
    st.error("DATABASE_URL fehlt in st.secrets.")
    st.stop()

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("select message from hello order by id desc limit 1;")
            row = cur.fetchone()
    st.success("DB connection: OK ✅")
    st.write("Nachricht aus DB:", row[0] if row else "(keine Daten)")
except Exception as e:
    st.error("DB connection failed ❌")
    st.exception(e)
