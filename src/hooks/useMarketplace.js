import { useEffect, useState } from 'react'

export function useMarketplace(apiBase, initialListings) {
  const [notice, setNotice] = useState('')
  const [listings, setListings] = useState(initialListings)
  const [songsCatalog, setSongsCatalog] = useState([])
  const [createdPlaylist, setCreatedPlaylist] = useState(null)

  useEffect(() => {
    const loadListings = async () => {
      try {
        const response = await fetch(`${apiBase}/api/playlists`)
        if (!response.ok) return
        const data = await response.json()
        if (Array.isArray(data.listings)) {
          setListings(data.listings)
        }
      } catch (_error) {
        setNotice('Marketplace is in offline mode. Start backend for live listings.')
      }
    }

    const loadSongsCatalog = async () => {
      try {
        const response = await fetch(`${apiBase}/api/catalog/songs`)
        if (!response.ok) return
        const data = await response.json()
        if (Array.isArray(data.songs)) {
          setSongsCatalog(data.songs)
        }
      } catch (_error) {
        // Keep form usable with manual song IDs.
      }
    }

    loadListings()
    loadSongsCatalog()
  }, [apiBase])

  const handleCreatePlaylist = (event, onCreated) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const selectedSongIds = form
      .getAll('song_ids')
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value > 0)
    const manualSongIds = form
      .get('song_ids_manual')
      ?.toString()
      .split(',')
      .map((value) => Number(value.trim()))
      .filter((value) => Number.isInteger(value) && value > 0)
    const songIds = selectedSongIds.length > 0 ? selectedSongIds : (manualSongIds ?? [])

    const draft = {
      name: form.get('name')?.toString().trim(),
      creator: form.get('creator')?.toString().trim(),
      genre: form.get('genre')?.toString().trim(),
      cover: form.get('cover')?.toString().trim(),
      seller_user_id: form.get('seller_user_id')?.toString().trim(),
      song_ids: songIds,
    }

    if (!draft.name || !draft.creator || !draft.genre || !draft.cover || !draft.seller_user_id) {
      setNotice('Fill all required fields, including seller user ID.')
      return
    }
    if (draft.song_ids.length === 0) {
      setNotice('Select at least one song or enter valid song IDs (example: 1,4,7).')
      return
    }

    setCreatedPlaylist(draft)
    setNotice('Playlist draft created. Set price and submit to list it.')
    onCreated?.()
    event.currentTarget.reset()
  }

  const handleSellPlaylist = async (event) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const price = Number(form.get('price'))

    if (!createdPlaylist || !Number.isFinite(price) || price < 0) {
      setNotice('Enter a valid price (0 or greater).')
      return
    }

    const payload = {
      ...createdPlaylist,
      price,
    }

    try {
      const response = await fetch(`${apiBase}/api/playlists`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        setNotice(typeof data.detail === 'string' ? data.detail : 'Could not list playlist.')
        return
      }
      if (!data.listing) {
        setNotice('Playlist created, but response format was unexpected.')
        return
      }
      setListings((prev) => [data.listing, ...prev])
      setNotice('Playlist listed successfully.')
      setCreatedPlaylist(null)
      event.currentTarget.reset()
    } catch (_error) {
      setNotice('Could not reach backend. Start backend server and try again.')
    }
  }

  return {
    notice,
    setNotice,
    listings,
    songsCatalog,
    createdPlaylist,
    handleCreatePlaylist,
    handleSellPlaylist,
  }
}
