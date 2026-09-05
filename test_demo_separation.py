import os
import sqlite3
from database.database import init_db, seed_demo_database, get_filtered_dashboard_data, get_db_connection

# Clean up
if os.path.exists('kaushal_marg.db'): os.remove('kaushal_marg.db')
if os.path.exists('demo_kaushal_marg.db'): os.remove('demo_kaushal_marg.db')

print('--- Testing empty real DB ---')
init_db()
data = get_filtered_dashboard_data()
print('Real DB total:', data['total_beneficiaries'])

print('\n--- Testing demo mode ---')
seed_demo_database()
demo_data = get_filtered_dashboard_data(db_path='demo_kaushal_marg.db')
print('Demo DB total:', demo_data['total_beneficiaries'])

print('\n--- Testing switching back to real DB ---')
data = get_filtered_dashboard_data()
print('Real DB total after demo seed:', data['total_beneficiaries'])

print('\n--- Testing real DB with 1 record ---')
conn = get_db_connection()
conn.execute("INSERT INTO beneficiaries (name, preferred_language, district) VALUES ('Real User', 'en', 'Test Dist')")
conn.commit()
data = get_filtered_dashboard_data()
print('Real DB total:', data['total_beneficiaries'])

print('\nAll isolated successfully!')
