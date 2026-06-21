import streamlit as st
import sqlite3
import pandas as pd
import bcrypt
from datetime import datetime

st.set_page_config(page_title="Opportunity Tracker SaaS", layout="wide")

# ================= DATABASE =================
conn = sqlite3.connect("opportunities.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    title TEXT,
    type TEXT,
    link TEXT,
    deadline TEXT,
    status TEXT
)
""")

conn.commit()

# ================= AUTH =================
def create_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    try:
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed),
        )
        conn.commit()
        return True
    except:
        return False


def verify_user(username, password):
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    row = c.fetchone()
    if row:
        return bcrypt.checkpw(password.encode(), row[0])
    return False


# ================= SESSION =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None


# ================= HELPERS =================
def days_left(deadline):
    try:
        d = pd.to_datetime(deadline)
        return (d - pd.to_datetime(datetime.today())).days
    except:
        return None


# ================= DATABASE OPS =================
def get_data(user):
    return pd.read_sql_query(
        "SELECT * FROM opportunities WHERE username=?",
        conn,
        params=(user,),
    )


def add_data(user, title, type_, link, deadline, status):
    c.execute(
        """
        INSERT INTO opportunities (username, title, type, link, deadline, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user, title, type_, link, str(deadline), status),
    )
    conn.commit()


def delete_data(row_id):
    c.execute("DELETE FROM opportunities WHERE id=?", (row_id,))
    conn.commit()


def update_status(row_id, new_status):
    c.execute(
        "UPDATE opportunities SET status=? WHERE id=?",
        (new_status, row_id),
    )
    conn.commit()


# ================= AUTH UI =================
def auth_page():
    st.title("🔐 Opportunity Tracker SaaS")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):
            if verify_user(u, p):
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")

        if st.button("Create Account"):
            if len(nu) < 3 or len(np) < 4:
                st.error("Too short username/password")
            else:
                if create_user(nu, np):
                    st.success("Account created!")
                else:
                    st.error("Username already exists")


# ================= LOGOUT =================
def logout():
    st.sidebar.button(
        "🚪 Logout",
        on_click=lambda: st.session_state.update(
            {"logged_in": False, "user": None}
        ),
    )


# ================= APP =================
def app():
    user = st.session_state.user

    st.sidebar.title(f"👤 {user}")
    page = st.sidebar.radio("Menu", ["Dashboard", "Add", "Analytics"])

    logout()

    # ================= DASHBOARD =================
    if page == "Dashboard":
        st.title("📊 Dashboard")

        df = get_data(user)

        st.metric("Total Opportunities", len(df))
        st.markdown("---")

        if df.empty:
            st.info("No opportunities added yet")

        else:
            for _, row in df.iterrows():

                dl = days_left(row["deadline"])

                if dl is None:
                    badge = "⚪ No deadline"
                    color = "#888"
                elif dl < 0:
                    badge = f"🔴 Overdue ({abs(dl)}d)"
                    color = "#ff4b4b"
                elif dl <= 3:
                    badge = f"🟠 Urgent ({dl}d left)"
                    color = "#ff9800"
                else:
                    badge = f"🟢 {dl}d left"
                    color = "#4caf50"

                col1, col2 = st.columns([6, 2])

                with col1:
                    st.markdown(
                        f"""
                        <div style="
                            padding:12px;
                            border:1px solid #ddd;
                            border-radius:10px;
                            margin-bottom:10px;
                        ">
                            <h4>🎯 {row['title']}</h4>
                            <p><b>Type:</b> {row['type']}</p>
                            <p><b>Status:</b> {row['status']}</p>
                            <p style="color:{color};font-weight:600;">
                                {badge}
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with col2:
                    new_status = st.selectbox(
                        "Status",
                        ["Not Applied", "Applied", "Completed"],
                        index=["Not Applied", "Applied", "Completed"].index(
                            row["status"]
                        ),
                        key=f"status_{row['id']}",
                    )

                    if st.button("💾 Save", key=f"save_{row['id']}"):
                        update_status(row["id"], new_status)
                        st.rerun()

                    if st.button("🗑️ Delete", key=f"del_{row['id']}"):
                        delete_data(row["id"])
                        st.rerun()

    # ================= ADD =================
    elif page == "Add":
        st.title("➕ Add Opportunity")

        title = st.text_input("Title")
        type_ = st.selectbox(
            "Type", ["Internship", "Hackathon", "Course", "Scholarship"]
        )
        link = st.text_input("Link")
        deadline = st.date_input("Deadline")
        status = st.selectbox(
            "Status", ["Not Applied", "Applied", "Completed"]
        )

        if st.button("Save"):
            if title.strip() == "":
                st.error("Title required")
            else:
                add_data(user, title, type_, link, deadline, status)
                st.success("Saved successfully!")
                st.rerun()

    # ================= ANALYTICS =================
    elif page == "Analytics":
        st.title("📈 Analytics")

        df = get_data(user)

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="opportunities.csv",
            mime="text/csv",
        )

        if df.empty:
            st.info("No data yet")
        else:
            col1, col2 = st.columns(2)

            col1.metric("Total", len(df))
            col2.metric("Types", df["type"].nunique())

            st.bar_chart(df["type"].value_counts())
            st.bar_chart(df["status"].value_counts())


# ================= RUN APP =================
if st.session_state.logged_in:
    app()
else:
    auth_page()
