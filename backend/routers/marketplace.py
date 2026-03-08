from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import crud
import schemas
from database import get_db

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.post("/sell-playlist", response_model=schemas.MarketplaceOut)
def sell_playlist(payload: schemas.SellPlaylistRequest, db: Session = Depends(get_db)):
    seller = crud.get_user(db, payload.seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    listing = crud.create_marketplace_listing(db, payload)
    return listing


@router.get("", response_model=list[schemas.MarketplaceOut])
def get_marketplace(db: Session = Depends(get_db)):
    return crud.list_public_marketplace_items(db)


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
