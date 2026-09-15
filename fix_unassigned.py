import re

with open("app.py", "r") as f:
    content = f.read()

# We need to replace the unassigned block
old_block = """                unassigned = []
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
                        st.success("All accounts have at least one community selected!")"""

new_block = """                unassigned = []
                for p_id in communities_cache.keys():
                    if f"pool_{p_id}" in st.session_state:
                        if not st.session_state[f"pool_{p_id}"]:
                            unassigned.append(p_id)
                    else:
                        # Since default_selections is now [], it will be empty initially
                        unassigned.append(p_id)
                
                if unassigned:
                    st.warning(f"**Accounts with NO communities selected ({len(unassigned)}):** " + ", ".join(unassigned))
                    
                    unassigned_comms = set()
                    for p_id in unassigned:
                        if communities_cache.get(p_id):
                            unassigned_comms.update(list(communities_cache[p_id].keys()))
                    if unassigned_comms:
                        with st.expander("Available communities for the unassigned accounts"):
                            st.write(", ".join(sorted(list(unassigned_comms))))
                else:
                    st.success("All accounts have at least one community selected!")"""

content = content.replace(old_block, new_block)

with open("app.py", "w") as f:
    f.write(content)
