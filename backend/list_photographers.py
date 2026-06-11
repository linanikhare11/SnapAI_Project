import sys
sys.path.insert(0, '.')
from models.database import db, Photographer
from app import app

with app.app_context():
    photographers = Photographer.query.all()
    with open('photographers_list.txt', 'w') as f:
        f.write(f'Total photographers: {len(photographers)}\n\n')
        for p in photographers:
            f.write(f'ID: {p.id}\n')
            f.write(f'Name: {p.name}\n')
            f.write(f'Email: {p.email}\n')
            f.write(f'Mobile: {p.mobile_number}\n')
            f.write('---\n')

print("Done - check photographers_list.txt")
