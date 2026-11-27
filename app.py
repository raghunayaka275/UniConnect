
import streamlit as st
import database
import core

# ---------------- SETUP ----------------

st.set_page_config(page_title="UniConnect", page_icon="🎓", layout="wide")
@st.cache_resource
def initialise_database():
    database.init_db()
    return True


initialise_database()

if "graph_loaded" not in st.session_state:
    core.load_graph()
    st.session_state.graph_loaded = True

if "user" not in st.session_state:
    st.session_state.user = None
# ---------------- FLASH MESSAGES ----------------

def show_flash_message():
    message = st.session_state.pop("flash_message", None)
    message_type = st.session_state.pop("flash_type", "success")

    if message:
        if message_type == "success":
            st.success(message)
        elif message_type == "error":
            st.error(message)
        elif message_type == "warning":
            st.warning(message)
        else:
            st.info(message)


def set_flash_message(message, message_type="success"):
    st.session_state.flash_message = message
    st.session_state.flash_type = message_type

show_flash_message()


# ---------------- DESIGN ----------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.stApp {background:var(--background-color);color:var(--text-color);}
h1,h2,h3,h4,p,label,li {color:var(--text-color);}
[data-testid="stSidebar"] {background:#101c35;}
[data-testid="stSidebar"] * {color:#edf3ff !important;}


[data-testid="stTabs"] {
    background: var(--secondary-background-color);
    padding: 18px;
    border-radius: 16px;
}

[data-testid="stForm"] {
    background: var(--secondary-background-color);
    padding: 22px;
    border-radius: 15px;
    border: 1px solid rgba(128,150,180,.25);
}

[data-testid="stMarkdownContainer"] p {
    color: var(--text-color);
}
/* Consistent login contrast in light and dark themes */

[data-testid="stForm"] {
    background: transparent;
    border: 1px solid rgba(128,150,180,.3);
    border-radius: 14px;
    padding: 20px;
}

[data-testid="stForm"] label,
[data-testid="stTabs"] button,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
    color: var(--text-color) !important;
}

.stTextInput input {
    background: var(--secondary-background-color) !important;
    color: var(--text-color) !important;
    -webkit-text-fill-color: var(--text-color) !important;
}

.stTextInput input::placeholder {
    color: var(--text-color);
    opacity: .55;
}

.stFormSubmitButton button[kind="primary"] {
    background: var(--primary-color) !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)



# ---------------- REUSABLE FUNCTIONS ----------------

def hero(title, subtitle):
    st.markdown(f"""
    <div class="hero">
        <div>UNICONNECT • STUDENT NETWORK</div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=60)
def student_name(username):
    profile = database.get_profile(username)
    return profile[1] or username if profile else username


def student_card(username, subtitle=None):
    with st.container(border=True):
        st.markdown(f"**👤 {student_name(username)}**")
        st.caption(f"@{username}" + (f" • {subtitle}" if subtitle else ""))


def connection_button(username, person, key):
    if st.button("🤝 Connect", key=key, type="primary"):
        if database.send_request(username, person):
            st.success("Connection request sent!")
            st.rerun()
        else:
            st.warning("A pending request already exists.")


# ---------------- LOGIN / SIGNUP ----------------

if st.session_state.user is None:

    st.markdown("""
    <div style="text-align:center;padding:35px 10px 20px;">
        <div style="font-size:48px;">🎓</div>
        <h1 style="font-size:40px;margin-bottom:0;">UniConnect</h1>
        <p style="opacity:.75;">Your campus. Your community. Your connections.</p>
    </div>
    """, unsafe_allow_html=True)

    login_tab, signup_tab = st.tabs(["🔐 Login", "✨ Create Account"])

    with login_tab:
        st.subheader("Welcome back!")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.form_submit_button("Login", type="primary", use_container_width=True):
                if database.login_user(username.strip(), password):
                    st.session_state.user = username.strip()
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    with signup_tab:
        st.subheader("Join the community")
        with st.form("signup_form"):
            new_username = st.text_input("Choose a username")
            new_name = st.text_input("Your full name")
            new_password = st.text_input("Choose a password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")

            if st.form_submit_button("Create Account", type="primary", use_container_width=True):
                if not new_username.strip() or not new_name.strip() or not new_password:
                    st.warning("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif database.register_user(new_username.strip(), new_password, new_name.strip()):
                   core.load_graph()
                   set_flash_message("Account created successfully! You can now log in.")
                   st.rerun()
                else:
                    st.error("That username is already taken.")

# ---------------- MAIN APP ----------------

else:
    username = st.session_state.user
    display_name = student_name(username)

    with st.sidebar:
        st.markdown("""
        <div style="padding:12px 4px 25px;">
            <div style="font-size:34px;">🎓</div>
            <div style="font-size:24px;font-weight:800;">UniConnect</div>
            <div style="font-size:12px;color:#a9c8ff;">CONNECT • COLLABORATE • CREATE</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.caption("YOUR CAMPUS")
        page = st.radio(
            "Navigation",
            ["🏠 Home", "👤 My Profile", "🤝 Connections", "🔎 Explore"],
            label_visibility="collapsed"
        )
        st.markdown("---")
        st.write(f"**{display_name}**")
        st.caption(f"@{username}")

        if st.button("↪ Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()

        st.markdown("---")
        st.caption("Made for students, by students.")

    # ---------------- HOME ----------------

    if page == "🏠 Home":
        friends = set(core.get_connections(username)) | {username}
        feed = [p for p in database.get_all_posts() if p[1] in friends]

        hero(f"Hey, {display_name.split()[0]} 👋",
             "Here's what's happening in your campus community.")

        c1, c2, c3 = st.columns(3)
        c1.metric("My Connections", core.get_degree(username))
        c2.metric("People in UniConnect", len(database.get_all_users()))
        c3.metric("Posts in Your Feed", len(feed))

        st.subheader("📝 Share an update")
        with st.form("create_post_form"):
            content = st.text_area(
                "What's on your mind?",
                placeholder="Share a project, idea, achievement or campus update...",
                height=100
            )
            if st.form_submit_button("Publish Post", type="primary"):
                if content.strip():
                    database.create_post(username, content.strip())
                    st.success("Your post is live!")
                    st.rerun()
                else:
                    st.warning("Write something before publishing.")

        st.divider()
        st.subheader("🌐 Your Community Feed")

        if not feed:
            st.info("Your feed is waiting for its first post. Share an update or connect with more students!")

        for post_id, author, content, created_at in feed:
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"**👤 {student_name(author)}**")
                    st.caption(f"@{author} • {created_at}")
                with c2:
                    if author == username and st.button("Delete", key=f"delete_{post_id}"):
                        database.delete_post(post_id, username)
                        st.rerun()
                st.write(content)

    # ---------------- PROFILE ----------------

    elif page == "👤 My Profile":
        hero("Your Profile", "Let other students know who you are and what you do.")
        profile = database.get_profile(username)

        if profile:
            _, name, programme, year, bio, skills = profile
            st.markdown(f"### 👤 {name or username}")
            st.caption(f"@{username}")
            st.metric("Connections", core.get_degree(username))
            st.divider()
            st.subheader("Edit your information")

            with st.form("profile_form"):
                name = st.text_input("Full Name", value=name or "")
                programme = st.text_input("Programme", value=programme or "")
                year = st.text_input("Year of Study", value=year or "")
                bio = st.text_area("About Me", value=bio or "")
                skills = st.text_input("Skills (comma separated)", value=skills or "")

                if st.form_submit_button("Save Changes", type="primary"):
                    database.update_profile(username, name, programme, year, bio, skills)
                    st.success("Profile updated successfully!")
                    st.rerun()

    # ---------------- CONNECTIONS ----------------

    elif page == "🤝 Connections":
        hero("Your Network", "Build meaningful connections with fellow students.")
        friends = core.get_connections(username)
        incoming = database.get_incoming_requests(username)
        outgoing = database.get_outgoing_requests(username)

        c1, c2 = st.columns(2)
        c1.metric("Connected Students", len(friends))
        c2.metric("Pending Incoming Requests", len(incoming))

        st.divider()
        st.subheader("🤝 My Connections")

        if not friends:
            st.info("You haven't connected with anyone yet. Explore students!")

        for friend in friends:
            c1, c2 = st.columns([4, 1])
            with c1:
                student_card(friend)
            with c2:
                if st.button("Remove", key=f"remove_{friend}"):
                    database.remove_connection(username, friend)
                    core.load_graph()
                    st.rerun()

        st.divider()
        st.subheader("📩 Incoming Requests")

        if not incoming:
            st.caption("No pending incoming requests.")

        for request_id, sender in incoming:
            student_card(sender, "wants to connect with you")
            c1, c2 = st.columns(2)

            with c1:
                if st.button("Accept", key=f"accept_{request_id}", type="primary", use_container_width=True):
                    database.accept_request(request_id)
                    core.load_graph()
                    st.success("Connection accepted!")
                    st.rerun()

            with c2:
                if st.button("Reject", key=f"reject_{request_id}", use_container_width=True):
                    database.reject_request(request_id)
                    st.rerun()

        st.divider()
        st.subheader("📤 Outgoing Requests")

        if not outgoing:
            st.caption("You have no pending outgoing requests.")

        for request_id, receiver in outgoing:
            c1, c2 = st.columns([4, 1])
            with c1:
                student_card(receiver, "Request pending")
            with c2:
                if st.button("Cancel", key=f"cancel_{request_id}"):
                    database.cancel_request(username, receiver)
                    st.rerun()

        st.divider()
        st.subheader("✨ People You May Know")
        recommendations = core.recommend_students(username)

        if not recommendations:
            st.info("Connect with more students to discover recommendations.")

        for person in recommendations:
            mutual = len(core.get_mutual_connections(username, person))
            student_card(person, f"{mutual} mutual connections")
            connection_button(username, person, f"recommend_{person}")

    # ---------------- EXPLORE ----------------


    elif page == "🔎 Explore":
        hero("Discover Students", "Find people, share interests and grow your campus network.")

        search = st.text_input(
            "🔎 Search by name or username",
            placeholder="Start typing a name or username..."
        ).strip().lower()

        if not search:
            st.info("Start typing to discover students by name or username.")

        else:
            results = []

            for profile in database.get_all_profiles():
                person, name, programme, year, bio, skills = profile

                if person == username:
                    continue

                name = name or ""

                if person.lower().startswith(search) or name.lower().startswith(search):
                    results.append(profile)

            if not results:
                st.warning("No matching students found.")

            for profile in results:
                person, name, programme, year, bio, skills = profile
                mutual = core.get_mutual_connections(username, person)

                with st.container(border=True):
                    st.markdown(f"### 👤 {name or person}")
                    st.caption(f"@{person}")

                    c1, c2 = st.columns(2)
                    c1.write(f"**Programme:** {programme or 'Not added'}")
                    c1.write(f"**Year:** {year or 'Not added'}")
                    c2.write(f"**Mutual connections:** {len(mutual)}")
                    c2.write(f"**Skills:** {skills or 'Not added'}")

                    st.write(f"**About:** {bio or 'No bio yet'}")

                    path = core.shortest_path(username, person)
                    if path:
                        st.success("Connection path: " + " → ".join(path))

                    if person in core.get_connections(username):
                        st.success("✓ Already connected")
                    else:
                        connection_button(username, person, f"connect_{person}")
