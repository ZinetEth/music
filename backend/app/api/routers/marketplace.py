from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.services import crud

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.post("/sell-playlist", response_model=schemas.MarketplaceOut)
def sell_playlist(payload: schemas.SellPlaylistRequest, db: Session = Depends(get_db)):
    seller = crud.get_user(db, payload.seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    listing = crud.create_marketplace_listing(db, payload)
    return listing


@router.post("/sell-song", response_model=schemas.MarketplaceSongOut)
def sell_song(payload: schemas.SellSongRequest, db: Session = Depends(get_db)):
    seller = crud.get_user(db, payload.seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    try:
        crud.create_song_marketplace_listing(db, payload)
    except ValueError as exc:
        if str(exc) == "song_not_found":
            raise HTTPException(status_code=404, detail="Song not found") from exc
        raise

    songs = crud.list_public_song_marketplace_items(db)
    match = next((song for song in songs if song.song_id == payload.song_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Song not found")
    return match


@router.get("", response_model=list[schemas.MarketplacePlaylistOut])
def get_marketplace(db: Session = Depends(get_db)):
    return crud.list_public_marketplace_items(db)


@router.get("/playlists", response_model=list[schemas.MarketplacePlaylistOut])
def get_marketplace_playlists(db: Session = Depends(get_db)):
    return crud.list_public_marketplace_items(db)


@router.get("/songs", response_model=list[schemas.MarketplaceSongOut])
def get_marketplace_songs(db: Session = Depends(get_db)):
    return crud.list_public_song_marketplace_items(db)


@router.post("/buy-playlist", response_model=schemas.BuyPlaylistResponse)
def buy_playlist(payload: schemas.BuyPlaylistRequest, db: Session = Depends(get_db)):
    buyer = crud.get_user(db, payload.buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")

    try:
        listing, _purchase = crud.buy_playlist(db, payload)
    except ValueError as exc:
        if str(exc) == "playlist_not_found":
            raise HTTPException(status_code=404, detail="Playlist not found") from exc
        raise

    return {
        "playlist_id": listing.playlist_id,
        "buyer_id": payload.buyer_id,
        "sales_count": listing.sales_count,
        "purchased": True,
    }


@router.post("/buy-song", response_model=schemas.BuySongResponse)
def buy_song(payload: schemas.BuySongRequest, db: Session = Depends(get_db)):
    buyer = crud.get_user(db, payload.buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")

    try:
        listing, _purchase = crud.buy_song(db, payload)
    except ValueError as exc:
        if str(exc) == "song_not_found":
            raise HTTPException(status_code=404, detail="Song not found") from exc
        raise

    return {
        "song_id": listing.song_id,
        "buyer_id": payload.buyer_id,
        "sales_count": listing.sales_count,
        "purchased": True,
    }


@router.post("/buy", response_model=schemas.BuyPlaylistResponse)
def buy_playlist_compat(
    payload: schemas.BuyPlaylistRequest,
    db: Session = Depends(get_db),
):
    return buy_playlist(payload, db)


@router.post("/save-playlist", response_model=schemas.SavePlaylistResponse)
def save_playlist(payload: schemas.SavePlaylistRequest, db: Session = Depends(get_db)):
    buyer = crud.get_user(db, payload.user_id)
    if not buyer:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        return crud.save_playlist(db, payload)
    except ValueError as exc:
        if str(exc) == "playlist_not_found":
            raise HTTPException(status_code=404, detail="Playlist not found") from exc
        raise


@router.get(
    "/secure-access/{playlist_id}",
    response_model=schemas.SecurePlaylistAccessResponse,
)
def secure_playlist_access(
    playlist_id: str, user_id: int, db: Session = Depends(get_db)
):
    try:
        return crud.secure_playlist_access(db, playlist_id, user_id)
    except ValueError as exc:
        if str(exc) == "playlist_not_found":
            raise HTTPException(status_code=404, detail="Playlist not found") from exc
        raise


@router.get(
    "/secure-song-access/{song_id}",
    response_model=schemas.SecureSongAccessResponse,
)
def secure_song_access(song_id: str, user_id: int, db: Session = Depends(get_db)):
    try:
        return crud.secure_song_access(db, song_id, user_id)
    except ValueError as exc:
        if str(exc) == "song_not_found":
            raise HTTPException(status_code=404, detail="Song not found") from exc
        raise
