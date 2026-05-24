"""
Script para crear un usuario inicial
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from passlib.context import CryptContext

# Base para este script
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_initial_user():
    """Crear usuario inicial"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///./osint_platform.db",
        echo=False,
    )
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        # Verificar si ya existe
        result = await session.execute(
            select(User).where(User.email == "admin@osint.local")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.hashed_password = pwd_context.hash("admin123")
            existing.is_active = True
            await session.commit()
            print("✅ Contrasenya restablerta per admin@osint.local")
            print("\n📧 Credenciales de acceso:")
            print("   Email: admin@osint.local")
            print("   Contraseña: admin123")
            return
        
        # Crear usuario
        hashed_password = pwd_context.hash("admin123")
        new_user = User(
            email="admin@osint.local",
            hashed_password=hashed_password,
            full_name="Administrador",
            is_active=True,
            is_superuser=True,
        )
        
        session.add(new_user)
        await session.commit()
        
        print("✅ Usuario creado exitosamente!")
        print("\n📧 Credenciales de acceso:")
        print("   Email: admin@osint.local")
        print("   Contraseña: admin123")
        print("\n⚠️  IMPORTANTE: Cambia la contraseña después del primer inicio de sesión")

if __name__ == "__main__":
    try:
        asyncio.run(create_initial_user())
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Asegúrate de que:")
        print("   1. El backend se haya ejecutado al menos una vez (para crear la BD)")
        print("   2. Las dependencias estén instaladas: pip install -r requirements.txt")
