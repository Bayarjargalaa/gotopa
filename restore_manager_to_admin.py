"""
MANAGER роль-ыг буцааж ерөнхий менежер болгох
menu_config.py-д role:MANAGER буцааж нэмэх
"""

# Read file
with open('main/menu_config.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add role:MANAGER back to inventory, counterparty, report sections
replacements = [
    ("'role:ACCOUNTANT', 'group:", "'role:MANAGER', 'role:ACCOUNTANT', 'group:"),
    ("'is_admin', 'role:ACCOUNTANT', 'group:", "'is_admin', 'role:MANAGER', 'role:ACCOUNTANT', 'group:"),
]

for old, new in replacements:
    content = content.replace(old, new)

# Write back
with open('main/menu_config.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ menu_config.py засагдлаа!")
print("   + Бараа материалд role:MANAGER нэмэгдлээ")
print("   + Харилцагчид role:MANAGER нэмэгдлээ")
print("   + Тайланд role:MANAGER нэмэгдлээ")
print("   MANAGER роль одоо бүх модуль удирдана!")
