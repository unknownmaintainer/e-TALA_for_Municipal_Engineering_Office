import sqlite3

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Set role to staff and designation to Municipal Engineer for user 7
c.execute("UPDATE permits_customuser SET role = 'staff', designation = 'Municipal Engineer' WHERE id = 7")

# Set designations for staff users
c.execute("UPDATE permits_customuser SET designation = 'Computer Operator / Data Encoder' WHERE id = 2")
c.execute("UPDATE permits_customuser SET designation = 'Records Management Officer' WHERE id = 12")
c.execute("UPDATE permits_customuser SET designation = 'CAD Operator / Draftsman' WHERE id = 13")

# Set designation for admins
c.execute("UPDATE permits_customuser SET designation = 'Engineering Office Head' WHERE id IN (1, 8, 9, 10, 11)")

conn.commit()
conn.close()
print("Sample user designations updated successfully!")
