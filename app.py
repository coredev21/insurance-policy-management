import streamlit as st
import snowflake.connector
from datetime import datetime
import pandas as pd
from typing import Optional, Dict, Any, List

# Page configuration
st.set_page_config(
    page_title="Insurance Policy Management",
    page_icon="📋",
    layout="wide"
)

# Initialize session state
if 'policy_data' not in st.session_state:
    st.session_state.policy_data = None
if 'enriched_data' not in st.session_state:
    st.session_state.enriched_data = None
if 'policy_exists_in_main' not in st.session_state:
    st.session_state.policy_exists_in_main = False


@st.cache_resource
def get_snowflake_connection():
    """Create and return a Snowflake connection."""
    try:
        conn = snowflake.connector.connect(
            user=st.secrets["snowflake"]["user"],
            password=st.secrets["snowflake"]["password"],
            account=st.secrets["snowflake"]["account"],
            warehouse=st.secrets["snowflake"]["warehouse"],
            database=st.secrets["snowflake"]["database"],
            schema=st.secrets["snowflake"]["schema"]
        )
        return conn
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {str(e)}")
        return None


def get_all_policy_refs() -> List[str]:
    """Fetch all policy reference numbers from both tables for autocomplete."""
    conn = get_snowflake_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        # Get policy refs from both tables
        query = """
        SELECT DISTINCT POLICY_REF 
        FROM (
            SELECT POLICY_REF FROM INSURANCE.PUBLIC.POLICY
            UNION
            SELECT POLICY_REF FROM INSURANCE.PUBLIC.POLICY_ENRICHED
        )
        WHERE POLICY_REF IS NOT NULL
        ORDER BY POLICY_REF
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        
        return [row[0] for row in results]
    except Exception as e:
        st.error(f"Error fetching policy references: {str(e)}")
        return []


def fetch_policy_data(policy_ref: str) -> tuple:
    """
    Fetch policy data from both tables.
    Returns: (policy_main_data, enriched_data, exists_in_main_table)
    """
    conn = get_snowflake_connection()
    if not conn:
        return None, None, False
    
    try:
        cursor = conn.cursor()
        
        # Fetch from main POLICY table
        query_main = """
        SELECT * FROM INSURANCE.PUBLIC.POLICY
        WHERE POLICY_REF = %s
        """
        cursor.execute(query_main, (policy_ref,))
        main_result = cursor.fetchone()
        main_columns = [desc[0] for desc in cursor.description]
        
        policy_main_data = None
        exists_in_main = False
        
        if main_result:
            policy_main_data = dict(zip(main_columns, main_result))
            exists_in_main = True
        
        # Fetch from POLICY_ENRICHED table
        query_enriched = """
        SELECT * FROM INSURANCE.PUBLIC.POLICY_ENRICHED
        WHERE POLICY_REF = %s
        """
        cursor.execute(query_enriched, (policy_ref,))
        enriched_result = cursor.fetchone()
        enriched_columns = [desc[0] for desc in cursor.description]
        
        enriched_data = None
        if enriched_result:
            enriched_data = dict(zip(enriched_columns, enriched_result))
        else:
            # Initialize with empty values if no enriched data exists
            enriched_data = {
                'POLICY_REF': policy_ref,
                'PRI': None,
                'TSI_SUBLIMIT': None,
                'UPLIFT_PD': None,
                'UPLIFT_BI': None,
                'CREATED_AT': None,
                'UPDATED_AT': None
            }
        
        cursor.close()
        return policy_main_data, enriched_data, exists_in_main
        
    except Exception as e:
        st.error(f"Error fetching policy data: {str(e)}")
        return None, None, False


def update_enriched_policy(policy_ref: str, enriched_data: Dict[str, Any]) -> bool:
    """Update or insert enriched policy data."""
    conn = get_snowflake_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if record exists
        check_query = """
        SELECT COUNT(*) FROM INSURANCE.PUBLIC.POLICY_ENRICHED
        WHERE POLICY_REF = %s
        """
        cursor.execute(check_query, (policy_ref,))
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            # Update existing record
            update_query = """
            UPDATE INSURANCE.PUBLIC.POLICY_ENRICHED
            SET PRI = %s,
                TSI_SUBLIMIT = %s,
                UPLIFT_PD = %s,
                UPLIFT_BI = %s,
                UPDATED_AT = CURRENT_TIMESTAMP()
            WHERE POLICY_REF = %s
            """
            cursor.execute(update_query, (
                enriched_data['PRI'],
                enriched_data['TSI_SUBLIMIT'],
                enriched_data['UPLIFT_PD'],
                enriched_data['UPLIFT_BI'],
                policy_ref
            ))
        else:
            # Insert new record
            insert_query = """
            INSERT INTO INSURANCE.PUBLIC.POLICY_ENRICHED
            (POLICY_REF, PRI, TSI_SUBLIMIT, UPLIFT_PD, UPLIFT_BI, CREATED_AT, UPDATED_AT)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
            """
            cursor.execute(insert_query, (
                policy_ref,
                enriched_data['PRI'],
                enriched_data['TSI_SUBLIMIT'],
                enriched_data['UPLIFT_PD'],
                enriched_data['UPLIFT_BI']
            ))
        
        conn.commit()
        cursor.close()
        return True
        
    except Exception as e:
        st.error(f"Error updating enriched policy data: {str(e)}")
        return False


def display_policy_form(policy_ref: str):
    """Display the policy form with main (read-only) and enriched (editable) fields."""
    
    # Fetch data
    policy_main, enriched, exists_in_main = fetch_policy_data(policy_ref)
    
    st.session_state.policy_data = policy_main
    st.session_state.enriched_data = enriched
    st.session_state.policy_exists_in_main = exists_in_main
    
    # Display status
    if exists_in_main:
        st.success(f"✅ Policy {policy_ref} found in main database")
    else:
        st.warning(f"⚠️ Policy {policy_ref} not found in main database. You can still create enriched data.")
    
    # Create two columns for better layout
    col1, col2 = st.columns([1, 1])
    
    # Main Policy Data (Read-only)
    with col1:
        st.subheader("📄 Main Policy Information (Read-Only)")
        
        if policy_main:
            with st.container(border=True):
                # Display key fields from main policy table
                st.text_input("Insured Name", value=policy_main.get('INSURED_NAME', ''), disabled=True)
                st.text_input("Policy Reference", value=policy_main.get('POLICY_REF', ''), disabled=True)
                st.text_input("Old Policy Reference", value=policy_main.get('OLD_POLICY_REF', ''), disabled=True)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.text_input("Renewal Date", value=policy_main.get('RENEWAL_DATE', ''), disabled=True)
                with col_b:
                    st.text_input("Expiry Date", value=policy_main.get('EXPIRY_DATE', ''), disabled=True)
                
                st.text_input("Underwriter", value=policy_main.get('UNDERWRITER', ''), disabled=True)
                st.text_input("Team", value=policy_main.get('TEAM', ''), disabled=True)
                st.text_input("Placement", value=policy_main.get('PLACEMENT', ''), disabled=True)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.number_input("Share %", value=float(policy_main.get('SHARE_PERCENTAGE', 0) or 0), disabled=True)
                with col_b:
                    st.number_input("Share Prev %", value=float(policy_main.get('SHARE_PREV_PERCENTAGE', 0) or 0), disabled=True)
                
                st.text_input("Broker", value=policy_main.get('BROKER', ''), disabled=True)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.number_input("Brokerage %", value=float(policy_main.get('BROKERAGE_PERCENTAGE', 0) or 0), disabled=True)
                with col_b:
                    st.number_input("Brokerage Prev %", value=float(policy_main.get('BROKERAGE_PREV_PERCENTAGE', 0) or 0), disabled=True)
                
                with st.expander("📊 Additional Details"):
                    st.text_input("Business Description", value=policy_main.get('BUSINESS_DESCRIPTION', ''), disabled=True)
                    st.text_input("Coverage", value=policy_main.get('COVERAGE', ''), disabled=True)
                    st.number_input("Total Property Exposure (GBP)", value=float(policy_main.get('TOTAL_PROPERTY_EXPOSURE_GBP', 0) or 0), disabled=True)
                    st.number_input("Top Risk Exposure (GBP)", value=float(policy_main.get('TOP_RISK_EXPOSURE_GBP', 0) or 0), disabled=True)
                    st.number_input("TSI (GBP)", value=float(policy_main.get('TSI_GBP', 0) or 0), disabled=True)
                    st.number_input("Final Renewal Premium (GBP)", value=float(policy_main.get('FINAL_RENEWAL_PREMIUM_GBP', 0) or 0), disabled=True)
        else:
            st.info("No main policy data available. This policy will be added to the enriched table only.")
    
    # Enriched Data (Editable)
    with col2:
        st.subheader("✏️ Enriched Policy Data (Editable)")
        
        with st.container(border=True):
            st.text_input("Policy Reference (Read-Only)", value=policy_ref, disabled=True, key=f"enriched_policy_ref_{policy_ref}")
            
            # Editable fields with form
            with st.form(key=f"enriched_form_{policy_ref}"):
                pri = st.number_input(
                    "PRI",
                    value=float(enriched.get('PRI', 0.0) or 0.0),
                    format="%.2f",
                    help="Premium Rate Index"
                )
                
                tsi_sublimit = st.number_input(
                    "TSI Sublimit",
                    value=float(enriched.get('TSI_SUBLIMIT', 0.0) or 0.0),
                    format="%.2f",
                    help="Total Sum Insured Sublimit"
                )
                
                uplift_pd = st.number_input(
                    "Uplift PD",
                    value=float(enriched.get('UPLIFT_PD', 0.0) or 0.0),
                    format="%.2f",
                    help="Uplift for Property Damage"
                )
                
                uplift_bi = st.number_input(
                    "Uplift BI",
                    value=float(enriched.get('UPLIFT_BI', 0.0) or 0.0),
                    format="%.2f",
                    help="Uplift for Business Interruption"
                )
                
                # Display timestamps if they exist
                if enriched.get('CREATED_AT'):
                    st.info(f"Created: {enriched['CREATED_AT']}")
                if enriched.get('UPDATED_AT'):
                    st.info(f"Last Updated: {enriched['UPDATED_AT']}")
                
                # Submit button
                submit_button = st.form_submit_button(
                    label="💾 Save Enriched Data",
                    use_container_width=True,
                    type="primary"
                )
                
                if submit_button:
                    # Prepare enriched data
                    updated_enriched = {
                        'PRI': pri,
                        'TSI_SUBLIMIT': tsi_sublimit,
                        'UPLIFT_PD': uplift_pd,
                        'UPLIFT_BI': uplift_bi
                    }
                    
                    # Update or insert
                    if update_enriched_policy(policy_ref, updated_enriched):
                        st.success("✅ Enriched policy data saved successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to save enriched policy data.")


def main():
    """Main application function."""
    
    st.title("🏢 Insurance Policy Management System")
    st.markdown("---")
    
    # Sidebar for connection info
    with st.sidebar:
        st.header("ℹ️ System Information")
        st.info("""
        **Features:**
        - 🔍 Search policies with autocomplete
        - 📖 View main policy data (read-only)
        - ✏️ Edit enriched policy data
        - ➕ Create enriched data for new policies
        """)
        
        if st.button("🔄 Refresh Policy List"):
            st.cache_resource.clear()
            st.rerun()
    
    # Policy search section
    st.subheader("🔍 Search Policy")
    
    # Get all policy refs for autocomplete
    policy_refs = get_all_policy_refs()
    
    # Single unified search field
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # Initialize session state for custom policy input
        if 'use_custom_policy' not in st.session_state:
            st.session_state.use_custom_policy = False
        
        # Main policy selection/input
        if not st.session_state.use_custom_policy:
            # Selectbox for existing policies
            selected_policy = st.selectbox(
                "Select or Type Policy Reference",
                options=[""] + policy_refs,
                index=0,
                help="Start typing to filter existing policies, or click 'Type New Policy' to enter a policy that doesn't exist yet"
            )
            policy_ref_to_search = selected_policy
        else:
            # Text input for new policy
            policy_ref_to_search = st.text_input(
                "Enter New Policy Reference",
                placeholder="Type the new policy reference...",
                help="Enter a policy reference that doesn't exist in the database yet",
                key="new_policy_input"
            )
        
        # Toggle button to switch between modes
        col_a, col_b = st.columns([1, 3])
        with col_a:
            if st.button("📝 Type New Policy" if not st.session_state.use_custom_policy else "📋 Select Existing", 
                        use_container_width=True):
                st.session_state.use_custom_policy = not st.session_state.use_custom_policy
                st.rerun()
    
    with col2:
        st.write("")  # Spacer
    
    # Search button
    if st.button("🔍 Load Policy", type="primary", disabled=not policy_ref_to_search):
        if policy_ref_to_search:
            st.markdown("---")
            display_policy_form(policy_ref_to_search)
    
    # If we already have loaded data, display it
    elif st.session_state.enriched_data and st.session_state.enriched_data.get('POLICY_REF'):
        st.markdown("---")
        policy_ref = st.session_state.enriched_data.get('POLICY_REF')
        display_policy_form(policy_ref)


if __name__ == "__main__":
    main()
