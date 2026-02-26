import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useCheckout } from './hooks/useCheckout'
import { useMarketplace } from './hooks/useMarketplace'
import { usePlayer } from './hooks/usePlayer'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8787'

const tracks = [
  {
    id: 1,
    title: 'Night Walk',
    artist: 'Astra Lane',
    cover:
      'https://images.unsplash.com/photo-1511379938547-c1f69419868d?auto=format&fit=crop&w=1200&q=80',
    audio: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
  },
  {
    id: 2,
    title: 'City Lights',
    artist: 'Mono Wave',
    cover:
      'https://images.unsplash.com/photo-1516280440614-37939bbacd81?auto=format&fit=crop&w=1200&q=80',
    audio: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3',
  },
  {
    id: 3,
    title: 'Sunday Loops',
    artist: 'Daydrift',
    cover:
      'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?auto=format&fit=crop&w=1200&q=80',
    audio: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3',
  },
]

const initialListings = [
  {
    id: 1,
    name: 'Lo-fi Focus Pack',
    creator: 'Nora',
    genre: 'Lo-fi',
    price: 8,
    cover:
      'https://images.unsplash.com/photo-1461784180009-21121b2f204c?auto=format&fit=crop&w=800&q=80',
  },
  {
    id: 2,
    name: 'Afrobeats Party Mix',
    creator: 'Kane',
    genre: 'Afrobeats',
    price: 12,
    cover:
      'https://images.unsplash.com/photo-1506157786151-b8491531f063?auto=format&fit=crop&w=800&q=80',
  },
]

const lyrics = [
  'City breathes in neon light',
  'Slow drums under midnight sky',
  'Every step becomes a rhythm',
  'Hold the moment, let it ride',
]

function formatTime(value) {
  if (!Number.isFinite(value)) return '0:00'
  const minutes = Math.floor(value / 60)
  const seconds = Math.floor(value % 60)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function TabIcon({ type }) {
  const common = 'h-4 w-4'
  if (type === 'Listen') {
    return (
      <svg viewBox="0 0 24 24" className={common} fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M8 18a2 2 0 1 0 0.01 0" />
        <path d="M10 18V6l9-2v12" />
        <path d="M17 16a2 2 0 1 0 0.01 0" />
      </svg>
    )
  }
  if (type === 'Browse') {
    return (
      <svg viewBox="0 0 24 24" className={common} fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="4" width="18" height="16" rx="3" />
        <path d="M3 10h18" />
      </svg>
    )
  }
  if (type === 'Radio') {
    return (
      <svg viewBox="0 0 24 24" className={common} fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="8" width="18" height="12" rx="3" />
        <path d="M8 12h7" />
        <path d="m3 8 5-4" />
      </svg>
    )
  }
  if (type === 'Store') {
    return (
      <svg viewBox="0 0 24 24" className={common} fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M4 7h16l-1 12H5L4 7Z" />
        <path d="M9 10a3 3 0 0 0 6 0" />
      </svg>
    )
  }
  return (
    <svg viewBox="0 0 24 24" className={common} fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.2-3.2" />
    </svg>
  )
}

function App() {
  const [activeTab, setActiveTab] = useState('Listen')
  const [sheetMode, setSheetMode] = useState('queue')
  const [isSheetOpen, setIsSheetOpen] = useState(false)

  const tabs = ['Listen', 'Browse', 'Radio', 'Store', 'Search']
  const {
    audioRef,
    currentTrack,
    currentIndex,
    isPlaying,
    progress,
    duration,
    setCurrentIndex,
    togglePlay,
    skipTrack,
    handleSeek,
  } = usePlayer(tracks)
  const {
    notice,
    setNotice,
    listings,
    songsCatalog,
    createdPlaylist,
    handleCreatePlaylist,
    handleSellPlaylist,
  } = useMarketplace(API_BASE, initialListings)
  const { checkoutLoadingId, handleCheckout } = useCheckout(API_BASE, setNotice)

  return (
    <main
      className="min-h-screen bg-[#f5f5f7] pb-40 text-zinc-900"
      style={{
        fontFamily:
          'SF Pro Text, SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif',
      }}
    >
      <audio ref={audioRef} preload="metadata" />

      <motion.section
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22 }}
        className="mx-auto max-w-6xl px-4 pt-8"
      >
        <header className="mb-6">
          <p className="text-sm font-medium text-zinc-500">Library</p>
          <h1 className="mt-1 text-4xl font-semibold tracking-tight">Listen Now</h1>
          {notice && <p className="mt-2 text-xs text-zinc-500">{notice}</p>}
        </header>

        <section className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
          <article className="rounded-[28px] border border-zinc-200 bg-white p-5 shadow-[0_8px_24px_rgba(0,0,0,0.04)]">
            <div>
              <img
                src={currentTrack.cover}
                alt={`${currentTrack.title} album art`}
                loading="lazy"
                className="aspect-square w-full rounded-3xl object-cover"
              />
            </div>

            <div className="mt-4">
              <h2 className="text-2xl font-semibold tracking-tight">{currentTrack.title}</h2>
              <p className="text-zinc-500">{currentTrack.artist}</p>
            </div>

            <div className="mt-4">
              <input
                type="range"
                min="0"
                max={duration || 0}
                step="0.1"
                value={progress}
                onChange={handleSeek}
                className="w-full accent-[#fa2d48]"
              />
              <div className="mt-1 flex justify-between text-xs text-zinc-500">
                <span>{formatTime(progress)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            <div className="mt-5 flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => skipTrack('prev')}
                aria-label="Previous track"
                className="rounded-full bg-zinc-100 p-2.5"
              >
                <svg
                  viewBox="0 0 24 24"
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M6 5v14" />
                  <path d="m18 6-8 6 8 6V6Z" />
                </svg>
              </button>
              <motion.button
                type="button"
                whileTap={{ scale: 0.97 }}
                onClick={togglePlay}
                aria-label={isPlaying ? 'Pause track' : 'Play track'}
                className="rounded-full bg-[#fa2d48] p-2.5 text-white"
              >
                {isPlaying ? (
                  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                    <rect x="7" y="5" width="3.5" height="14" rx="1" />
                    <rect x="13.5" y="5" width="3.5" height="14" rx="1" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                    <path d="M8 6v12l10-6-10-6Z" />
                  </svg>
                )}
              </motion.button>
              <button
                type="button"
                onClick={() => skipTrack('next')}
                aria-label="Next track"
                className="rounded-full bg-zinc-100 p-2.5"
              >
                <svg
                  viewBox="0 0 24 24"
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M18 5v14" />
                  <path d="m6 6 8 6-8 6V6Z" />
                </svg>
              </button>
            </div>
          </article>

          <aside className="space-y-5">
            <article className="rounded-[28px] border border-zinc-200 bg-white p-5 shadow-[0_8px_24px_rgba(0,0,0,0.04)]">
              <h3 className="text-lg font-semibold">Up Next</h3>
              <div className="mt-3 space-y-3">
                {tracks.map((track, index) => (
                  <button
                    key={track.id}
                    type="button"
                    onClick={() => setCurrentIndex(index)}
                    className="flex w-full items-center gap-3 rounded-2xl p-2 text-left hover:bg-zinc-50"
                  >
                    <img
                      src={track.cover}
                      alt={`${track.title} cover`}
                      loading="lazy"
                      className="h-12 w-12 rounded-xl object-cover"
                    />
                    <span>
                      <span className="block text-sm font-semibold">{track.title}</span>
                      <span className="block text-xs text-zinc-500">{track.artist}</span>
                    </span>
                  </button>
                ))}
              </div>
            </article>

            {activeTab === 'Store' && !createdPlaylist && (
              <article className="rounded-[28px] border border-zinc-200 bg-white p-5 shadow-[0_8px_24px_rgba(0,0,0,0.04)]">
                <h3 className="text-lg font-semibold">Create Playlist</h3>
                <p className="mt-1 text-xs text-zinc-500">
                  Include seller ID and at least one song, then list it.
                </p>
                <form
                  onSubmit={(event) => handleCreatePlaylist(event, () => setActiveTab('Store'))}
                  className="mt-4 grid gap-2.5"
                >
                  <input
                    name="name"
                    required
                    placeholder="Playlist name"
                    className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
                  />
                  <input
                    name="creator"
                    required
                    placeholder="Creator name"
                    className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
                  />
                  <input
                    name="genre"
                    required
                    placeholder="Genre"
                    className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
                  />
                  <input
                    name="cover"
                    type="url"
                    required
                    placeholder="Cover URL"
                    className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
                  />
                  <input
                    name="seller_user_id"
                    required
                    placeholder="Seller user ID (example: user_2)"
                    className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
                  />
                  {songsCatalog.length > 0 && (
                    <fieldset className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm">
                      <legend className="px-1 text-xs font-semibold text-zinc-600">Select songs</legend>
                      <div className="mt-1 grid gap-1.5">
                        {songsCatalog.slice(0, 12).map((song) => (
                          <label key={song.id} className="flex items-center gap-2 text-xs text-zinc-700">
                            <input type="checkbox" name="song_ids" value={song.id} />
                            <span>
                              #{song.id} {song.title} ({song.tier})
                            </span>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  )}
                  <input
                    name="song_ids_manual"
                    placeholder="Song IDs (comma-separated, e.g. 1,4,7)"
                    className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
                  />
                  <button
                    type="submit"
                    className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-semibold text-white"
                  >
                    Create Playlist
                  </button>
                </form>
              </article>
            )}

            {activeTab === 'Store' && createdPlaylist && (
              <article className="rounded-[28px] border border-zinc-200 bg-white p-5 shadow-[0_8px_24px_rgba(0,0,0,0.04)]">
                <h3 className="text-lg font-semibold">Sell Your Playlist</h3>
                <p className="mt-1 text-xs text-zinc-500">
                  {createdPlaylist.name} by {createdPlaylist.creator} | {createdPlaylist.song_ids.length} songs
                </p>
                <form onSubmit={handleSellPlaylist} className="mt-4 grid gap-2.5">
                  <input
                    name="price"
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    placeholder="Price"
                    className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
                  />
                  <button
                    type="submit"
                    className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-semibold text-white"
                  >
                    Add to Store
                  </button>
                </form>
              </article>
            )}
          </aside>
        </section>

        <section className="mt-7">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-xl font-semibold">Playlist Store</h3>
            <span className="text-sm text-zinc-500">{listings.length} items</span>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {listings.map((item) => (
              <article
                key={item.id}
                className="rounded-3xl border border-zinc-200 bg-white p-3 shadow-[0_8px_24px_rgba(0,0,0,0.04)]"
              >
                <img
                  src={item.cover}
                  alt={`${item.name} cover`}
                  loading="lazy"
                  className="h-40 w-full rounded-2xl object-cover"
                />
                <h4 className="mt-3 text-sm font-semibold leading-tight">{item.name}</h4>
                <p className="mt-1 text-xs text-zinc-500">{item.creator}</p>
                <div className="mt-3 flex items-center justify-between text-xs">
                  <span className="rounded-full bg-zinc-100 px-2.5 py-1">{item.genre}</span>
                  <span className="font-semibold">${item.price}</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleCheckout(item.id)}
                  disabled={checkoutLoadingId === item.id}
                  className="mt-3 w-full rounded-xl bg-[#fa2d48] px-3 py-2 text-xs font-semibold text-white disabled:opacity-60"
                >
                  {checkoutLoadingId === item.id ? 'Starting...' : 'Buy Playlist'}
                </button>
              </article>
            ))}
          </div>
        </section>
      </motion.section>

      <div className="fixed inset-x-0 bottom-[74px] z-20 mx-auto max-w-6xl px-4">
        <article className="flex items-center gap-3 rounded-2xl border border-zinc-200 bg-white/95 px-3 py-2 shadow-[0_8px_24px_rgba(0,0,0,0.06)] backdrop-blur">
          <img
            src={currentTrack.cover}
            alt={`${currentTrack.title} mini art`}
            loading="lazy"
            className="h-11 w-11 rounded-lg object-cover"
          />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">{currentTrack.title}</p>
            <p className="truncate text-xs text-zinc-500">{currentTrack.artist}</p>
          </div>
          <button
            type="button"
            onClick={() => {
              setSheetMode('lyrics')
              setIsSheetOpen(true)
            }}
            className="rounded-full bg-zinc-100 px-3 py-1.5 text-xs font-semibold"
          >
            Lyrics
          </button>
          <button
            type="button"
            onClick={() => {
              setSheetMode('queue')
              setIsSheetOpen(true)
            }}
            className="rounded-full bg-zinc-100 px-3 py-1.5 text-xs font-semibold"
          >
            Queue
          </button>
          <button
            type="button"
            onClick={togglePlay}
            aria-label={isPlaying ? 'Pause track' : 'Play track'}
            className="rounded-full bg-[#fa2d48] p-2 text-white"
          >
            {isPlaying ? (
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor">
                <rect x="7" y="5" width="3.5" height="14" rx="1" />
                <rect x="13.5" y="5" width="3.5" height="14" rx="1" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor">
                <path d="M8 6v12l10-6-10-6Z" />
              </svg>
            )}
          </button>
        </article>
      </div>

      <AnimatePresence>
        {isSheetOpen && (
          <>
            <motion.button
              type="button"
              aria-label="Close panel"
              onClick={() => setIsSheetOpen(false)}
              className="fixed inset-0 z-30 bg-black/25"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
            <motion.section
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ duration: 0.2 }}
              className="fixed inset-x-0 bottom-0 z-40 mx-auto max-w-2xl rounded-t-3xl bg-white p-5 shadow-2xl"
            >
              <div className="mb-4 flex items-center justify-between">
                <h4 className="text-lg font-semibold">{sheetMode === 'queue' ? 'Up Next' : 'Lyrics'}</h4>
                <button
                  type="button"
                  onClick={() => setIsSheetOpen(false)}
                  className="rounded-full bg-zinc-100 px-3 py-1 text-sm"
                >
                  Close
                </button>
              </div>
              {sheetMode === 'queue' ? (
                <div className="space-y-2">
                  {tracks.map((track, index) => (
                    <button
                      key={track.id}
                      type="button"
                      onClick={() => {
                        setCurrentIndex(index)
                        setIsSheetOpen(false)
                      }}
                      className="flex w-full items-center gap-3 rounded-xl p-2 text-left hover:bg-zinc-50"
                    >
                      <img
                        src={track.cover}
                        alt={`${track.title} queue art`}
                        loading="lazy"
                        className="h-10 w-10 rounded-lg object-cover"
                      />
                      <span className="text-sm">
                        <span className="block font-semibold">{track.title}</span>
                        <span className="block text-xs text-zinc-500">{track.artist}</span>
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="space-y-2 text-sm leading-relaxed text-zinc-700">
                  {lyrics.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
              )}
            </motion.section>
          </>
        )}
      </AnimatePresence>

      <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-zinc-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-around px-4 py-3">
          {tabs.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`flex flex-col items-center gap-1 text-[11px] font-medium ${
                activeTab === tab ? 'text-[#fa2d48]' : 'text-zinc-500'
              }`}
            >
              <TabIcon type={tab} />
              <span>{tab}</span>
            </button>
          ))}
        </div>
      </nav>
    </main>
  )
}

export default App

