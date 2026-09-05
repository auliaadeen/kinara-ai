"""Account settings and Parent ↔ Learner linking workflow."""
from __future__ import annotations

import streamlit as st

from src.services.firestore_service import FirestoreService, FirestoreUnavailableError
from src.ui import theme


def render_settings(db) -> None:
    fs = FirestoreService(db, st.session_state.uid)
    role = st.session_state.get("role", "parent")
    theme.hero("Zunara AI · Settings", "Account settings", "Manage your Zunara account and learning profile connection.")

    try:
        user = fs.get_user()
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return

    if role == "parent":
        theme.section_title("family_restroom", "Connect a learner")
        if user and user.linked_learner_uid:
            with st.container(border=True):
                st.success(f"Learner connected: {user.linked_learner_email or user.linked_learner_uid}")
                if user.linked_child_id:
                    child = fs.get_child(user.linked_child_id)
                    if child:
                        st.caption(f"Connected child profile: {child.name}")
            st.caption("To change the connection, generate a new code only after deciding which learner should own this profile.")

        try:
            children = fs.list_children()
        except FirestoreUnavailableError as exc:
            st.error(str(exc))
            return
        if not children:
            st.info("Create a child profile on Dashboard first. Then return here to connect the learner account.")
            return

        child_names = {c.child_id: c.name for c in children}
        default = user.linked_child_id if user and user.linked_child_id in child_names else children[0].child_id
        child_id = st.selectbox("Child profile", list(child_names), format_func=lambda cid: child_names[cid], index=list(child_names).index(default))
        if st.button("Generate learner linking code", type="primary", icon=":material/key:"):
            try:
                code = fs.create_link_code(child_id)
            except (FirestoreUnavailableError, ValueError) as exc:
                st.error(str(exc))
            else:
                st.session_state.generated_link_code = code

        if st.session_state.get("generated_link_code"):
            with st.container(border=True):
                st.markdown("#### Learner linking code")
                st.code(st.session_state.generated_link_code, language=None)
                st.caption("Share this code with the learner. It expires in 30 minutes and can be used once.")

    else:
        theme.section_title("link", "Connect to a parent")
        if user and user.linked_parent_uid and user.linked_child_id:
            st.success("Your learner account is connected.")
            parent_fs = FirestoreService(db, user.linked_parent_uid)
            try:
                child = parent_fs.get_child(user.linked_child_id)
            except FirestoreUnavailableError as exc:
                st.error(str(exc))
                return
            if child:
                st.info(f"Learning profile: {child.name} · {child.educational_level}")
            return

        st.write("Ask your parent to open Settings → Connect a learner and share the linking code with you.")
        with st.form("claim_learner_link"):
            code = st.text_input("Linking code", max_chars=8, placeholder="e.g. A1B2C3D4").strip().upper()
            submitted = st.form_submit_button("Connect account", type="primary", icon=":material/link:")
        if submitted:
            try:
                fs.claim_link_code(code)
            except (FirestoreUnavailableError, ValueError) as exc:
                st.error(str(exc))
            else:
                st.success("Your learner account is now connected to the parent profile.")
                st.rerun()
