import os

with open('database/seed.py', 'r', encoding='utf-8') as f:
    text = f.read()

replacements = {
    "Madhya Pradesh": "Tamil Nadu",
    "Bhopal": "Chennai",
    "Indore": "Coimbatore",
    "Jabalpur": "Madurai",
    "BMC-MP": "GCC-TN",
    "IMC-MP": "CMC-TN",
    "JMC-MP": "MMC-TN",
    "bmc.gov.in": "chennaicorporation.gov.in",
    "Kolar WTP": "Chembarambakkam WTP",
    "Misrod": "Velachery",
    "Yeshwant Sagar": "Siruvani",
    "Ranital": "Arasaradi",
    "Narmada": "Vaigai",
    "23.2599": "13.0827",
    "77.4126": "80.2707",
    "23.174": "13.012",
    "77.452": "80.234",
    "22.7196": "11.0168",
    "75.8577": "76.9558",
    "22.65": "10.98",
    "75.77": "76.92",
    "23.1815": "9.9252",
    "79.9864": "78.1198",
    "23.155": "9.89",
    "79.94": "78.08"
}

for k, v in replacements.items():
    text = text.replace(k, v)

with open('database/seed.py', 'w', encoding='utf-8') as f:
    f.write(text)

if os.path.exists('instance/rmmv.db'):
    os.remove('instance/rmmv.db')
    print("Database deleted. It will be recreated on next run.")
