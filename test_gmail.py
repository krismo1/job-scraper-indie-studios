"""
Test de conexión Gmail
"""
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

def test_gmail():
    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

    print("="*50)
    print("🔍 VERIFICANDO CONFIGURACIÓN")
    print("="*50)
    print(f"Host: {EMAIL_HOST}")
    print(f"Port: {EMAIL_PORT}")
    print(f"User: {EMAIL_USER}")
    print(f"Password: {'*' * len(EMAIL_PASSWORD)} ({len(EMAIL_PASSWORD)} caracteres)")
    print("="*50)

    if not all([EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD]):
        print("❌ ERROR: Faltan variables en el .env")
        return False

    if len(EMAIL_PASSWORD) != 16:
        print(f"⚠️  WARNING: El App Password debería tener 16 caracteres, tienes {len(EMAIL_PASSWORD)}")

    try:
        print("\n🔌 Conectando a Gmail...")

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
            print("✅ Conectado al servidor SMTP")

            print("🔐 Iniciando TLS...")
            server.starttls()
            print("✅ TLS iniciado")

            print("🔑 Autenticando...")
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            print("✅ Autenticación exitosa!")

            print("\n📧 Enviando email de prueba...")

            msg = MIMEMultipart('alternative')
            msg['Subject'] = "✅ JobScraper - Test Email"
            msg['From'] = EMAIL_USER
            msg['To'] = EMAIL_USER

            html = """
            <html>
                <body style="font-family: Arial; padding: 20px; background: #f0f0f0;">
                    <div style="background: white; padding: 30px; border-radius: 10px; max-width: 600px;">
                        <h1 style="color: #00d4ff;">🎮 JobScraper</h1>
                        <h2 style="color: #333;">¡Email configurado correctamente!</h2>
                        <p style="color: #666;">
                            Si recibes este email, significa que tu configuración de Gmail 
                            está funcionando perfectamente. 🎉
                        </p>
                        <p style="color: #666;">
                            Ya puedes usar el sistema de emails en JobScraper.
                        </p>
                        <hr style="border: 1px solid #eee; margin: 20px 0;">
                        <p style="color: #999; font-size: 12px;">
                            Test enviado desde JobScraper
                        </p>
                    </div>
                </body>
            </html>
            """

            html_part = MIMEText(html, 'html')
            msg.attach(html_part)

            server.send_message(msg)
            print("✅ Email enviado correctamente!")

        print("\n" + "="*50)
        print("✅ TODO FUNCIONA CORRECTAMENTE")
        print("="*50)
        print(f"📬 Revisa tu email: {EMAIL_USER}")
        print("="*50)

        return True

    except smtplib.SMTPAuthenticationError:
        print("\n❌ ERROR DE AUTENTICACIÓN")
        print("="*50)
        print("Posibles causas:")
        print("1. App Password incorrecto")
        print("2. No copiaste los 16 caracteres completos")
        print("3. Copiaste los espacios (debes quitarlos)")
        print("4. No activaste 'Verificación en 2 pasos'")
        print("\nSolución:")
        print("1. Ve a: https://myaccount.google.com/apppasswords")
        print("2. Genera un NUEVO App Password")
        print("3. Cópialo SIN espacios al .env")
        return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTipo de error:", type(e).__name__)
        return False

if __name__ == "__main__":
    test_gmail()