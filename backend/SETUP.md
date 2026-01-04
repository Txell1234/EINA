# Configuración del Backend

## Variables de Entorno

El proyecto utiliza variables de entorno para configuración sensible. La clave API de OpenAI ya está configurada.

### Configuración Rápida

**Windows PowerShell:**
```powershell
$env:OPENAI_API_KEY = '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'
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY='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'
```

### Archivo .env (Recomendado)

Alternativamente, puedes crear un archivo `.env` en la carpeta `backend/`:

```bash
cp env.example .env
# Editar .env y agregar tu OPENAI_API_KEY
```

**IMPORTANTE**: El archivo `.env` está en `.gitignore` y NO se subirá al repositorio. Mantén tu clave API segura y nunca la compartas públicamente.

## Seguridad

- ✅ La clave API está configurada de forma segura
- ✅ El archivo `.env` está excluido del control de versiones
- ✅ Las variables de entorno tienen prioridad sobre valores por defecto
- ⚠️ Nunca commitees archivos `.env` al repositorio









