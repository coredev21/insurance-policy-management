# Insurance Policy Management System

A Streamlit application for managing insurance policies with Snowflake database integration.

## Features

- 🔍 **Smart Policy Search**: Autocomplete search with all available policy references
- 📖 **Read-Only Main Policy Data**: View complete policy information from the main POLICY table (non-editable)
- ✏️ **Editable Enriched Data**: Update PRI, TSI_SUBLIMIT, UPLIFT_PD, and UPLIFT_BI values
- ➕ **Create New Enriched Entries**: Add enriched data even for policies not yet in the main table
- 🔄 **Automatic Timestamps**: Tracks creation and update times

## Database Schema

### POLICY Table (Read-Only)
Contains main policy information including insured name, policy references, dates, underwriter details, broker information, and financial data.

### POLICY_ENRICHED Table (Editable)
Contains supplementary policy data:
- `POLICY_REF` - Policy reference (links to POLICY table)
- `PRI` - Premium Rate Index
- `TSI_SUBLIMIT` - Total Sum Insured Sublimit
- `UPLIFT_PD` - Uplift for Property Damage
- `UPLIFT_BI` - Uplift for Business Interruption
- `CREATED_AT` - Record creation timestamp
- `UPDATED_AT` - Last update timestamp

## Setup Instructions

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure Snowflake Connection

Edit `.streamlit/secrets.toml` with your Snowflake credentials:

```toml
[snowflake]
user = "your_username"
password = "your_password"
account = "your_account"  # e.g., "xy12345.us-east-1"
warehouse = "your_warehouse"
database = "INSURANCE"
schema = "PUBLIC"
```

**Note**: Never commit `secrets.toml` to version control. Add it to `.gitignore`.

### 3. Run the Application

```powershell
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`.

## Usage

### Searching for a Policy

1. **Using Autocomplete**: Select a policy reference from the dropdown list
2. **Manual Entry**: Type a policy reference in the "Or enter manually" field
3. Click "Load Policy" to retrieve the data

### Viewing Policy Information

- **Left Panel**: Displays read-only information from the main POLICY table
- **Right Panel**: Shows editable fields from POLICY_ENRICHED table

### Updating Enriched Data

1. Search for a policy
2. Modify the editable fields in the right panel:
   - PRI
   - TSI Sublimit
   - Uplift PD
   - Uplift BI
3. Click "Save Enriched Data"

### Creating New Enriched Entries

If a policy doesn't exist in the main POLICY table yet:
1. Enter the policy reference manually
2. Click "Load Policy"
3. You'll see a warning that the policy isn't in the main database
4. Fill in the enriched data fields
5. Click "Save Enriched Data" to create a new entry

This creates an entry in POLICY_ENRICHED that will be linked automatically when the policy is added to the main POLICY table later.

## Security Notes

- Store sensitive credentials in `.streamlit/secrets.toml` (local development)
- For production deployment on Streamlit Cloud, use the Secrets Management feature
- Ensure proper Snowflake role-based access control (RBAC) is configured
- The application requires SELECT permissions on POLICY table and SELECT/INSERT/UPDATE on POLICY_ENRICHED table

## Troubleshooting

### Connection Issues
- Verify Snowflake credentials in `secrets.toml`
- Check network connectivity to Snowflake
- Ensure the warehouse is running
- Verify database and schema names

### No Policies Showing
- Ensure the POLICY and POLICY_ENRICHED tables contain data
- Check that POLICY_REF values are not null
- Verify user has SELECT permissions

### Cannot Update Data
- Ensure user has INSERT and UPDATE permissions on POLICY_ENRICHED table
- Check that policy reference is valid

## Support

For issues or questions, please contact your system administrator.
