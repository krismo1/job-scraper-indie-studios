"""
Test de conexión a Supabase
"""
from models import SessionLocal, Job
from datetime import datetime

def test_connection():
    print("🔌 Probando conexión a Supabase...")

    try:
        db = SessionLocal()

        # Contar jobs
        count = db.query(Job).count()
        print(f"✅ Conexión exitosa!")
        print(f"📊 Total de jobs en BD: {count}")

        # Mostrar algunos jobs
        jobs = db.query(Job).limit(3).all()
        print("\n📋 Primeros 3 jobs:")
        for job in jobs:
            print(f"   • {job.title} - {job.company} ({job.platform})")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_connection()