# Integrar EnsembleData API - Todas las Plataformas

## Objetivo

Integrar EnsembleData API para añadir capacidades de scraping de redes sociales adicionales a las herramientas OSINT existentes. EnsembleData proporciona acceso a TikTok, Instagram, YouTube, Threads, Reddit, Twitter/X, Twitch y Snapchat.

## Información de API

- **Base URL**: `https://ensembledata.com/apis/`
- **API Key**: `KfOGyPW13S68MHUr`
- **Documentación**: https://ensembledata.com/apis/docs
- **Autenticación**: Token como parámetro `token` en las requests

## Plataformas a Integrar

1. **TikTok** (tt)
   - Keyword Posts API
   - Hashtag Posts API
   - User Information API
   - User Posts API
   - Post Information API
   - Comments API

2. **Instagram** (ig)
   - Hashtag Posts API
   - User Information API
   - User Posts API
   - Post Information API
   - Comments API

3. **YouTube** (yt)
   - Keyword Posts API
   - Hashtag Posts API
   - Channel Information API
   - Channel Videos API
   - Video Information API
   - Comments API

4. **Threads** (th)
   - Keyword Posts API
   - User Information API
   - User Posts API
   - Post Replies API

5. **Reddit** (rd) - Opción adicional a la existente
   - Subreddit Posts API
   - Comments API

6. **Twitter/X** (tw)
   - User Information API
   - User Tweets API
   - Post Information API

7. **Twitch** (tv)
   - Keyword Posts API
   - Followers API

8. **Snapchat** (sc)
   - User Information API

## Implementación

### 1. Crear Servicio de Integración (`backend/integrations/ensembledata_api.py`)

Crear clase `EnsembleDataAPIService` con métodos para cada plataforma:

```python
class EnsembleDataAPIService:
    def __init__(self):
        self.base_url = "https://ensembledata.com/apis"
        self.api_key = settings.ENSEMBLEDATA_API_KEY
    
    # TikTok methods
    async def tiktok_user_info(self, username: str)
    async def tiktok_user_posts(self, username: str, count: int = 30)
    async def tiktok_hashtag_posts(self, hashtag: str, count: int = 30)
    async def tiktok_keyword_posts(self, keyword: str, count: int = 30)
    async def tiktok_post_info(self, post_url: str)
    async def tiktok_comments(self, post_url: str, count: int = 30)
    
    # Instagram methods
    async def instagram_user_info(self, username: str)
    async def instagram_user_posts(self, username: str, count: int = 30)
    async def instagram_hashtag_posts(self, hashtag: str, count: int = 30)
    async def instagram_post_info(self, post_url: str)
    async def instagram_comments(self, post_url: str, count: int = 30)
    
    # YouTube methods
    async def youtube_channel_info(self, channel_id: str)
    async def youtube_channel_videos(self, channel_id: str, count: int = 30)
    async def youtube_keyword_posts(self, keyword: str, count: int = 30)
    async def youtube_video_info(self, video_id: str)
    async def youtube_comments(self, video_id: str, count: int = 30)
    
    # Threads methods
    async def threads_user_info(self, username: str)
    async def threads_user_posts(self, username: str, count: int = 30)
    async def threads_keyword_posts(self, keyword: str, count: int = 30)
    
    # Reddit methods (adicional)
    async def reddit_subreddit_posts(self, subreddit: str, count: int = 25)
    async def reddit_comments(self, post_url: str, count: int = 25)
    
    # Twitter/X methods
    async def twitter_user_info(self, username: str)
    async def twitter_user_tweets(self, username: str, count: int = 20)
    async def twitter_post_info(self, tweet_url: str)
    
    # Twitch methods
    async def twitch_keyword_posts(self, keyword: str, count: int = 30)
    
    # Snapchat methods
    async def snapchat_user_info(self, username: str)
```

### 2. Añadir API Key a Config (`backend/app/config.py`)

```python
# EnsembleData API (Social Media Scraping)
ENSEMBLEDATA_API_KEY: str = ""
```

### 3. Integrar en OSINTService (`backend/services/osint_service.py`)

- Importar `EnsembleDataAPIService`
- Añadir instancia en `__init__`
- Añadir casos en `execute_query` para cada tipo de query de EnsembleData

### 4. Añadir Endpoints (`backend/routers/osint_collection.py`)

Crear endpoints para cada plataforma con prefijo `ensembledata-`:

- `/ensembledata/tiktok/user-info`
- `/ensembledata/tiktok/user-posts`
- `/ensembledata/tiktok/hashtag-posts`
- `/ensembledata/tiktok/keyword-posts`
- `/ensembledata/instagram/user-info`
- `/ensembledata/instagram/user-posts`
- `/ensembledata/instagram/hashtag-posts`
- `/ensembledata/youtube/channel-info`
- `/ensembledata/youtube/channel-videos`
- `/ensembledata/youtube/keyword-posts`
- `/ensembledata/threads/user-info`
- `/ensembledata/threads/user-posts`
- `/ensembledata/reddit/subreddit-posts` (adicional)
- `/ensembledata/twitter/user-info`
- `/ensembledata/twitter/user-tweets`
- `/ensembledata/twitch/keyword-posts`
- `/ensembledata/snapchat/user-info`

Todos los endpoints deben:
- Aceptar `case_id` opcional
- Usar `OSINTService.execute_query`
- Retornar `OSINTResultResponse`

### 5. Actualizar Frontend (`frontend/src/components/OSINTCollection/OSINTCollection.tsx`)

Añadir nuevas herramientas al array `tools`:

```typescript
{
  id: 'ensembledata-tiktok',
  name: 'TikTok (EnsembleData)',
  description: 'Información de usuarios, posts y hashtags de TikTok',
  icon: '🎵',
},
{
  id: 'ensembledata-instagram',
  name: 'Instagram (EnsembleData)',
  description: 'Información de usuarios, posts y hashtags de Instagram',
  icon: '📷',
},
// ... etc para cada plataforma
```

### 6. Añadir Servicios en Frontend (`frontend/src/services/api.ts`)

Añadir métodos en `osintService` para cada endpoint de EnsembleData.

### 7. Crear Formularios en Frontend

Crear componentes de formulario para cada herramienta de EnsembleData (similar a los existentes).

## Estructura de Endpoints EnsembleData

Basado en la documentación, los endpoints siguen este patrón:
- TikTok: `/apis/tt/user/info`, `/apis/tt/user/posts`, `/apis/tt/hashtag/posts`, etc.
- Instagram: `/apis/ig/user/info`, `/apis/ig/user/posts`, etc.
- YouTube: `/apis/yt/channel/info`, `/apis/yt/channel/videos`, etc.

## Archivos a Modificar/Crear

1. **Nuevo**: `backend/integrations/ensembledata_api.py`
2. **Modificar**: `backend/app/config.py` - Añadir `ENSEMBLEDATA_API_KEY`
3. **Modificar**: `backend/services/osint_service.py` - Integrar servicio
4. **Modificar**: `backend/routers/osint_collection.py` - Añadir endpoints
5. **Modificar**: `frontend/src/components/OSINTCollection/OSINTCollection.tsx` - Añadir herramientas
6. **Modificar**: `frontend/src/services/api.ts` - Añadir métodos de servicio
7. **Modificar**: `backend/.env` - Añadir API key
8. **Modificar**: `backend/env.example` - Documentar nueva variable

## Consideraciones

- **Rate Limiting**: EnsembleData usa un sistema de "unidades". Monitorear uso.
- **Errores**: Manejar errores de API (401, 429, etc.) apropiadamente
- **Naming**: Usar prefijo `ensembledata-` para diferenciar de herramientas existentes
- **Compatibilidad**: Mantener herramientas existentes (Reddit, etc.) funcionando
- **Case Linking**: Todos los endpoints deben soportar `case_id` opcional

## Flujo de Datos

```
Usuario selecciona herramienta EnsembleData
  ↓
Frontend envía request con parámetros
  ↓
Backend endpoint recibe request
  ↓
OSINTService.execute_query con query_type específico
  ↓
EnsembleDataAPIService hace request a API externa
  ↓
Resultado se guarda en OSINTResult
  ↓
Respuesta retornada al frontend
  ↓
Datos aparecen en visualizaciones del caso (si case_id proporcionado)
```

## Beneficios

- **Más fuentes de datos**: Acceso a 8 plataformas adicionales
- **Datos en tiempo real**: APIs robustas y escalables
- **Sin autenticación**: No requiere credenciales de plataformas
- **Complementario**: Añade capacidades sin reemplazar herramientas existentes









