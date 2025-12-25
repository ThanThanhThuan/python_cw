import pyodbc

def get_cw_reference_data():
    """
    Connects to SQL Server and returns a dictionary:
    { 'CWName': ExercisePrice, ... }
    """
    # UPDATE THIS CONNECTION STRING
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=PC3\\SQLEXPRESS;"
        "DATABASE=CW;"
        "Trusted_Connection=yes;" # Use this if using Windows Auth, remove UID/PWD
        )
#  "UID=YOUR_USERNAME;"
#         "PWD=YOUR_PASSWORD;"
#         "Trusted_Connection=yes;" # Use this if using Windows Auth, remove UID/PWD
    cw_map = {}
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Select relevant columns
        cursor.execute("SELECT CWName, ExercisePrice FROM [dbo].[CWMain] Where [RecordDate] in (Select top 1 [RecordDate] from [dbo].[CWMain] order by [RecordDate] desc)")
        rows = cursor.fetchall()
        
        for row in rows:
            # Create a lookup dictionary: Key=Symbol, Value=Price
            # We use .strip() to remove any SQL padding spaces
            if row.CWName:
                cw_map[row.CWName.strip()] = row.ExercisePrice if row.ExercisePrice else 0.0
                
        conn.close()
        print(f"Loaded {len(cw_map)} records from SQL Server.")
        
    except Exception as e:
        print(f"Error connecting to SQL Server: {e}")
        # Return empty dict so app doesn't crash
        return {}

    return cw_map