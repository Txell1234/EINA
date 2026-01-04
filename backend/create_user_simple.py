"""
Script simple para crear usuario usando la API
"""
import requests
import json

API_URL = "http://localhost:8000"

def create_user():
    """Crear usuario usando la API"""
    url = f"{API_URL}/api/auth/register"
    
    user_data = {
        "email": "admin@osint.local",
        "password": "admin123",
        "full_name": "Administrador"
    }
    
    try:
        response = requests.post(url, json=user_data)
        
        if response.status_code == 201:
            print("Usuario creado exitosamente!")
            print("\nCredenciales de acceso:")
            print("   Email: admin@osint.local")
            print("   Contrasena: admin123")
            print("\nIMPORTANTE: Cambia la contrasena despues del primer inicio de sesion")
        elif response.status_code == 400:
            data = response.json()
            if "already registered" in data.get("detail", "").lower():
                print("El usuario admin@osint.local ya existe")
                print("\nUsa estas credenciales:")
                print("   Email: admin@osint.local")
                print("   Contrasena: admin123")
            else:
                print(f"Error: {data.get('detail', 'Error desconocido')}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except requests.exceptions.ConnectionError:
        print("ERROR: No se puede conectar al servidor")
        print("Asegurate de que el backend este ejecutandose en http://localhost:8000")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_user()









