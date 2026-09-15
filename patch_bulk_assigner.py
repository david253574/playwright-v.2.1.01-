import re

with open("app.py", "r") as f:
    content = f.read()

bulk_assigner_code = """
            st.divider()
            with st.expander(":material/group_add: Master Community Bulk Assigner", expanded=True):
                st.write("Assign a community to all accounts that are members of it. Accounts that are not members (or have no community selected) will be listed so you can assign a different one to them.")
                
                # Gather all unique communities across all accounts
                all_unique_comms = set()
                for p_id, profile_comms in communities_cache.items():
                    if profile_comms:
                        all_unique_comms.update(list(profile_comms.keys()))
                all_unique_comms = sorted(list(all_unique_comms))
                
                col_ass1, col_ass2, col_ass3 = st.columns([0.5, 0.25, 0.25])
                with col_ass1:
                    selected_master_comm = st.selectbox("Select a Community to Assign:", options=[""] + all_unique_comms, key="master_comm_select")
                with col_ass2:
                    st.write("") # spacing
                    st.write("")
                    if st.button("Assign to Eligible", use_container_width=True):
                        if selected_master_comm:
                            assigned_count = 0
                            for p_id, profile_comms in communities_cache.items():
                                if profile_comms and selected_master_comm in profile_comms:
                                    # Assign this community (overwrite existing to ensure it's exactly this one)
                                    st.session_state[f"pool_{p_id}"] = [selected_master_comm]
                                    assigned_count += 1
                            st.success(f"Assigned to {assigned_count} accounts!")
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("Select a community first.")
                with col_ass3:
                    st.write("")
                    st.write("")
                    if st.button("Clear All Selections", use_container_width=True):
                        for p_id in communities_cache.keys():
                            st.session_state[f"pool_{p_id}"] = []
                        st.success("Cleared all!")
                        import time
                        time.sleep(1)
                        st.rerun()
                
                # Show unassigned accounts
                # We consider an account unassigned if it's explicitly set to an empty list in session_state,
                # or if it hasn't been rendered yet but will be rendered soon.
                # Actually, to make it clear, let's just look at the session_state.
                unassigned = []
                for p_id in communities_cache.keys():
                    if f"pool_{p_id}" in st.session_state:
                        if not st.session_state[f"pool_{p_id}"]:
                            unassigned.append(p_id)
                    else:
                        # If we want the bulk assigner to be the main workflow, we should encourage users to 'Clear All' first
                        # or we can consider them 'unassigned' if we assume a fresh start.
                        # But by default they get 5 communities. We will list them if explicitly empty.
                        pass
                
                # Let's see if ANY pools are in session state to know if we've rendered the form below at least once
                rendered_once = any(f"pool_{p_id}" in st.session_state for p_id in communities_cache.keys())
                
                if rendered_once:
                    if unassigned:
                        st.warning(f"**Accounts with NO communities selected ({len(unassigned)}):** " + ", ".join(unassigned))
                        
                        # Show what communities these unassigned accounts actually have, to help the user choose the next one
                        unassigned_comms = set()
                        for p_id in unassigned:
                            if communities_cache.get(p_id):
                                unassigned_comms.update(list(communities_cache[p_id].keys()))
                        if unassigned_comms:
                            with st.expander("Available communities for the unassigned accounts"):
                                st.write(", ".join(sorted(list(unassigned_comms))))
                    else:
                        st.success("All accounts have at least one community selected!")

            uploaded_images = {}"""

# Replace "uploaded_images = {}" with the new block
content = content.replace("            uploaded_images = {}", bulk_assigner_code)

with open("app.py", "w") as f:
    f.write(content)
