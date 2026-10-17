# Run from the project folder: python3 -m tools.set_role
from models.customer import ROLES, all_customers, set_role

# Show everyone and their role
print("Customers:")
for customer in all_customers():
    print(f"  {customer['customerID']}: {customer['customerName']} ({customer['email']}) = {customer['role']}")

customer_id = int(input("Customer number: "))
role = input(f"New role {ROLES}: ").strip().lower()

if role not in ROLES:
    print(f"Role must be one of {ROLES}")
elif set_role(customer_id, role):
    print(f"Customer {customer_id} is now {role}")
else:
    print(f"Customer {customer_id} not found")
