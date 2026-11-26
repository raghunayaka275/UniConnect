
import streamlit as st
import database
import core

# Initialise the application
st.set_page_config(
    page_title="UniConnect",
    page_icon="🎓",
    layout="wide"
)

database.init_db()
core.load_graph()

st.title("🎓 UniConnect")
st.caption("Connect. Collaborate. Create.")

# Session management
if "user" not in st.session_state:
    st.session_state.user = None


# ---------------- AUTHENTICATION ----------------

if st.session_state.user is None:

    st.subheader("Welcome to UniConnect")

    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        st.subheader("Login")

        username = st.text_input("Username", key="login_username")
        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button("Login"):
            if database.login_user(username, password):
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with signup_tab:
        st.subheader("Create an account")

        new_username = st.text_input("Choose a username")
        new_name = st.text_input("Your full name")
        new_password = st.text_input(
            "Choose a password",
            type="password"
        )
        confirm_password = st.text_input(
            "Confirm password",
            type="password"
        )

        if st.button("Create Account"):
            if not new_username or not new_name or not new_password:
                st.warning("Please fill in all fields.")

            elif new_password != confirm_password:
                st.error("Passwords do not match.")

            elif database.register_user(
                new_username.strip(),
                new_password,
                new_name.strip()
            ):
                core.load_graph()
                st.success("Account created! You can now log in.")

            else:
                st.error("That username is already taken.")


# ---------------- MAIN APPLICATION ----------------

else:

    username = st.session_state.user

    st.sidebar.title("Navigation")
    st.sidebar.write(f"Logged in as **{username}**")

    page = st.sidebar.radio(
        "Go to",
        ["Home", "My Profile", "Connections", "Explore"]
    )

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # ---------------- HOME ----------------

    if page == "Home":

        st.header("Your Home Feed")

        friends = set(core.get_connections(username))
        friends.add(username)

        posts = database.get_all_posts()

        feed = [
            post for post in posts
            if post[1] in friends
        ]

        if not feed:
            st.info("No posts yet. Connect with students or create a post!")

        for post_id, author, content, created_at in feed:

            with st.container(border=True):
                st.write(f"**@{author}**")
                st.caption(created_at)
                st.write(content)

                if author == username:
                    if st.button("Delete Post", key=f"delete_{post_id}"):
                        database.delete_post(post_id, username)
                        st.rerun()

        st.divider()
        st.subheader("Share something!")

        with st.form("create_post_form"):
            content = st.text_area(
                "What are you working on?",
                placeholder="Share your project, idea or achievement..."
            )

            submitted = st.form_submit_button("Publish Post")

            if submitted:
                if content.strip():
                    database.create_post(username, content.strip())
                    st.success("Post published!")
                    st.rerun()
                else:
                    st.warning("Write something before publishing.")


    # ---------------- MY PROFILE ----------------

    elif page == "My Profile":

        st.header("My Profile")

        profile = database.get_profile(username)

        if profile:

            _, name, programme, study_year, bio, skills = profile

            with st.form("profile_form"):

                name = st.text_input("Full Name", value=name or "")
                programme = st.text_input(
                    "Programme",
                    value=programme or ""
                )
                study_year = st.text_input(
                    "Year of Study",
                    value=study_year or ""
                )
                bio = st.text_area("Short Bio", value=bio or "")
                skills = st.text_input(
                    "Skills (comma separated)",
                    value=skills or ""
                )

                if st.form_submit_button("Save Profile"):

                    database.update_profile(
                        username,
                        name,
                        programme,
                        study_year,
                        bio,
                        skills
                    )

                    st.success("Profile updated!")
                    st.rerun()

            st.divider()
            st.write("**Username:**", username)
            st.write("**Connections:**", core.get_degree(username))


    # ---------------- CONNECTIONS ----------------

    elif page == "Connections":

        st.header("My Connections")

        st.subheader("Your Connections")

        friends = core.get_connections(username)

        if not friends:
            st.info("You haven't connected with anyone yet.")

        for friend in friends:

            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"👤 **{friend}**")

            with col2:
                if st.button("Remove", key=f"remove_{friend}"):

                    database.remove_connection(username, friend)
                    core.load_graph()
                    st.rerun()

        st.divider()

        st.subheader("Incoming Requests")

        incoming = database.get_incoming_requests(username)

        if not incoming:
            st.info("No pending requests.")

        for request_id, sender in incoming:

            st.write(f"**{sender}** wants to connect.")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Accept", key=f"accept_{request_id}"):

                    database.accept_request(request_id)
                    core.load_graph()
                    st.success("Connection accepted!")
                    st.rerun()

            with col2:
                if st.button("Reject", key=f"reject_{request_id}"):

                    database.reject_request(request_id)
                    st.rerun()

        st.divider()

        st.subheader("People You May Know")

        recommendations = core.recommend_students(username)

        if not recommendations:
            st.info("No recommendations available yet.")

        for person in recommendations:
            st.write(
                f"👤 **{person}** — "
                f"{len(core.get_mutual_connections(username, person))} "
                "mutual connections"
            )


    # ---------------- EXPLORE ----------------

    elif page == "Explore":

        st.header("Explore Students")

        search = st.text_input(
            "Search by name or username",
            placeholder="Start typing..."
        )

        all_users = database.get_all_users()

        results = []

        for person in all_users:

            if person == username:
                continue

            profile = database.get_profile(person)

            if not profile:
                continue

            name = profile[1] or ""

            if (
                person.lower().startswith(search.lower())
                or name.lower().startswith(search.lower())
            ):
                results.append(profile)

        if not search:
            st.caption("Start typing to find students.")

        for profile in results:

            person, name, programme, year, bio, skills = profile

            with st.container(border=True):

                st.subheader(name or person)
                st.write(f"**Username:** @{person}")
                st.write(f"**Programme:** {programme or 'Not added'}")
                st.write(f"**Year:** {year or 'Not added'}")
                st.write(f"**Bio:** {bio or 'No bio yet'}")
                st.write(f"**Skills:** {skills or 'Not added'}")

                mutual = core.get_mutual_connections(
                    username,
                    person
                )

                st.write(f"**Mutual connections:** {len(mutual)}")

                path = core.shortest_path(username, person)

                if path:
                    st.write(
                        "**Connection path:** "
                        + " → ".join(path)
                    )

                if person in core.get_connections(username):

                    st.success("Already connected")

                else:

                    if st.button(
                        "Connect",
                        key=f"connect_{person}"
                    ):

                        if database.send_request(username, person):
                            st.success("Connection request sent!")
                            st.rerun()
                        else:
                            st.warning(
                                "A request already exists or you are connected."
                            )

        if search and not results:
            st.info("No matching students found.")
