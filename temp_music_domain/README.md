# Music Domain

A completely isolated music domain that handles songs, playlists, marketplace, and social features without any coupling to payment logic.

## Overview

The music domain provides comprehensive music functionality that can be used across multiple applications. It's completely isolated from payment logic and integrates with the payment domain through clean interfaces.

## Features

### Core Features
- **Song Management**: Upload, organize, and manage music files
- **Playlist Creation**: Create and manage user playlists
- **Marketplace**: Buy and sell playlists and songs
- **Social Features**: Likes, follows, and social signals
- **Search & Discovery**: Advanced search and recommendations
- **Analytics**: Playback tracking and user insights
- **Artist Management**: Artist profiles and releases

### Integration Features
- **Payment Domain Integration**: Clean separation with payment processing
- **External Services**: Navidrome integration for music library
- **File Storage**: Configurable storage backends
- **Content Moderation**: Automated and manual moderation

## Architecture

### Domain Structure
```
music_domain/
├── models.py              # Database models (isolated from payment)
├── schemas.py             # API schemas for all music operations
├── services.py            # Business logic layer
├── api.py                 # FastAPI routers
├── config.py              # Configuration management
├── main.py                # Application entry point
└── README.md              # This documentation
```

### Key Concepts

#### Song Model
Complete song management with metadata:
```python
{
    "title": "Song Title",
    "artist": "Artist Name",
    "album": "Album Name",
    "genre": "Pop",
    "duration_seconds": 240,
    "file_path": "/path/to/song.mp3",
    "is_public": true,
    "owner_id": "user_123"
}
```

#### Playlist Model
User-created collections with ordering:
```python
{
    "name": "My Playlist",
    "description": "Favorite songs",
    "owner_id": "user_123",
    "is_public": true,
    "song_count": 25
}
```

#### Marketplace Integration
Clean integration with payment domain:
```python
# Music domain handles the item
listing = marketplace_service.create_listing(
    item_type="playlist",
    item_id=playlist.id,
    price=99.99,
    seller_id=user.id
)

# Payment domain handles the transaction
payment_intent = payment_service.create_payment_intent(
    PaymentIntentCreate(
        app_name="music_platform",
        object_type="marketplace_item",
        object_id=listing.id,
        amount=listing.price,
        customer_id=buyer.id
    )
)
```

## Quick Start

### 1. Configuration

Add music domain settings to your `.env` file:

```bash
# File storage
MUSIC_STORAGE_PATH=./music_files
MAX_FILE_SIZE_MB=100
ALLOWED_AUDIO_FORMATS=mp3,flac,wav,aac

# Features
SEARCH_ENABLED=true
MARKETPLACE_ENABLED=true
SUBSCRIPTIONS_ENABLED=true
SOCIAL_FEATURES_ENABLED=true

# Limits
MAX_PLAYLIST_SONGS=1000
MAX_LISTING_PRICE=10000
MARKETPLACE_FEE_PERCENTAGE=5.0
```

### 2. Database Setup

The music domain uses SQLAlchemy models. Run migrations to create tables:

```python
from shared.db import create_tables
create_tables()
```

### 3. Basic Usage

```python
from temp_music_domain.services import SongService, PlaylistService

# Create a song
song_service = SongService(db)
song = song_service.create_song(
    title="My Song",
    artist="My Artist",
    file_path="/path/to/song.mp3",
    uploader_id=user.id,
    owner_id=user.id
)

# Create a playlist
playlist_service = PlaylistService(db)
playlist = playlist_service.create_playlist(
    name="My Playlist",
    owner_id=user.id
)
```

## API Endpoints

### Songs
- `POST /api/v1/music/songs` - Create song
- `GET /api/v1/music/songs/{id}` - Get song
- `GET /api/v1/music/songs` - List songs
- `PUT /api/v1/music/songs/{id}` - Update song
- `DELETE /api/v1/music/songs/{id}` - Delete song
- `POST /api/v1/music/songs/{id}/playback` - Record playback
- `POST /api/v1/music/songs/{id}/signals/{type}` - Add social signal

### Playlists
- `POST /api/v1/music/playlists` - Create playlist
- `GET /api/v1/music/playlists/{id}` - Get playlist
- `GET /api/v1/music/playlists` - List playlists
- `POST /api/v1/music/playlists/{id}/songs` - Add song to playlist
- `DELETE /api/v1/music/playlists/{id}/songs/{song_id}` - Remove song

### Marketplace
- `POST /api/v1/music/marketplace/listings` - Create listing
- `GET /api/v1/music/marketplace/listings` - List listings

### Search
- `GET /api/v1/music/search` - Search music content

## Configuration

### File Storage
```python
# Storage configuration
music_config = get_music_config()
music_config.music_storage_path = "./music_files"
music_config.max_file_size_mb = 100
music_config.allowed_audio_formats = ["mp3", "flac", "wav"]
```

### Feature Flags
```python
# Enable/disable features
music_config.search_enabled = True
music_config.marketplace_enabled = True
music_config.subscriptions_enabled = True
music_config.social_features_enabled = True
```

### Limits and Constraints
```python
# Configure limits
music_config.max_playlist_songs = 1000
music_config.max_listing_price = 10000.0
music_config.marketplace_fee_percentage = 5.0
```

## Integration with Payment Domain

### Clean Separation
The music domain is completely isolated from payment logic:

```python
# Music domain - handles music operations
song = song_service.create_song(...)

# Payment domain - handles payment operations
payment_intent = payment_service.create_payment_intent(
    PaymentIntentCreate(
        app_name="music_platform",
        object_type="song_purchase",
        object_id=song.id,
        amount=price,
        customer_id=user.id
    )
)

# Link through purchase record
purchase = marketplace_service.create_purchase(
    buyer_id=user.id,
    seller_id=song.owner_id,
    item_type="song",
    item_id=song.id,
    price=price,
    payment_intent_id=payment_intent.id
)
```

### Marketplace Flow
1. **Create Listing**: Music domain creates marketplace listing
2. **Initiate Payment**: Payment domain handles payment processing
3. **Complete Purchase**: Music domain records purchase with payment_intent_id
4. **Access Content**: User gets access after payment verification

## Security Considerations

### File Upload Security
- File format validation
- File size limits
- MIME type checking
- Virus scanning (configurable)

### Access Control
- User ownership validation
- Public/private content separation
- Permission-based access

### Content Moderation
- Automated content filtering
- Manual review workflows
- Blocked word filtering

## Performance Features

### Caching
- Configurable cache TTL
- Memory-based caching
- Cache invalidation strategies

### Search Optimization
- Full-text search indexing
- Faceted search support
- Search result ranking

### Analytics
- Playback event tracking
- User behavior analysis
- Performance metrics

## Testing

### Unit Tests
```python
import pytest
from temp_music_domain.services import SongService

def test_create_song():
    service = SongService(db)
    song = service.create_song(
        title="Test Song",
        artist="Test Artist",
        file_path="/test/path.mp3",
        uploader_id="test_user",
        owner_id="test_user"
    )
    assert song.title == "Test Song"
    assert song.artist == "Test Artist"
```

### Integration Tests
```python
def test_song_payment_integration():
    # Create song
    song = song_service.create_song(...)
    
    # Create payment intent
    payment_intent = payment_service.create_payment_intent(...)
    
    # Create purchase
    purchase = marketplace_service.create_purchase(
        payment_intent_id=payment_intent.id,
        ...
    )
    
    assert purchase.payment_intent_id == payment_intent.id
```

## Monitoring

### Health Checks
- `/health` - Basic health check
- `/health/ready` - Readiness check with configuration validation
- `/health/live` - Liveness check

### Metrics
- Song upload counts
- Playlist creation metrics
- Marketplace transaction volume
- Search query performance
- User engagement metrics

### Logging
- Structured JSON logs
- Request tracing with IDs
- Error tracking and alerting
- Performance monitoring

## Deployment

### Docker Configuration
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8002

CMD ["uvicorn", "temp_music_domain.main:app", "--host", "0.0.0.0", "--port", "8002"]
```

### Environment Variables
See configuration section for all available options.

### Database Migration
```python
from shared.db import create_tables
create_tables()
```

## Extending the Domain

### Adding New Features
1. Add model to `models.py`
2. Create service in `services.py`
3. Add API endpoints in `api.py`
4. Update configuration in `config.py`
5. Add tests and documentation

### Custom Providers
```python
class CustomStorageProvider:
    def store_file(self, file_data, metadata):
        # Custom storage logic
        pass
    
    def retrieve_file(self, file_path):
        # Custom retrieval logic
        pass
```

## Contributing

1. Follow the existing code structure
2. Add comprehensive tests
3. Update documentation
4. Ensure security best practices
5. Add proper error handling

## License

This music domain is part of the larger music platform project and follows the same licensing terms.
