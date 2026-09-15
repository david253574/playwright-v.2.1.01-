with open("app.py", "r") as f:
    content = f.read()

old_code = """                            for p_id, profile_comms in communities_cache.items():
                                if profile_comms and selected_master_comm in profile_comms:
                                    # Assign this community (overwrite existing to ensure it's exactly this one)
                                    st.session_state[f"pool_{p_id}"] = [selected_master_comm]
                                    assigned_count += 1"""

new_code = """                            for p_id, profile_comms in communities_cache.items():
                                is_unassigned = True
                                if f"pool_{p_id}" in st.session_state and st.session_state[f"pool_{p_id}"]:
                                    is_unassigned = False
                                    
                                if is_unassigned and profile_comms and selected_master_comm in profile_comms:
                                    st.session_state[f"pool_{p_id}"] = [selected_master_comm]
                                    assigned_count += 1"""

content = content.replace(old_code, new_code)

with open("app.py", "w") as f:
    f.write(content)
