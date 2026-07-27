import { useEffect, useRef } from 'react'
import { isVideo, posterForMedia } from '../themes'

export function MemeMedia({ source, className = '', alt = '', eager = false, animate = false }: {
  source: string
  className?: string
  alt?: string
  eager?: boolean
  animate?: boolean
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const video = isVideo(source)
  const poster = posterForMedia(source)

  useEffect(() => {
    const element = videoRef.current
    if (!video || !animate || !element) return
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    let isVisible = false

    const syncPlayback = () => {
      if (isVisible && !document.hidden && !reducedMotion.matches) {
        void element.play().catch(() => undefined)
      } else {
        element.pause()
      }
    }
    const observer = new IntersectionObserver(([entry]) => {
      isVisible = entry.isIntersecting
      syncPlayback()
    }, { threshold: 0.12 })
    observer.observe(element)
    document.addEventListener('visibilitychange', syncPlayback)
    reducedMotion.addEventListener('change', syncPlayback)
    return () => {
      observer.disconnect()
      document.removeEventListener('visibilitychange', syncPlayback)
      reducedMotion.removeEventListener('change', syncPlayback)
      element.pause()
    }
  }, [animate, source, video])

  if (video && !animate && poster) {
    return <img className={className} src={poster} alt={alt} loading={eager ? 'eager' : 'lazy'} />
  }
  if (video) {
    return <video
      ref={videoRef}
      className={className}
      src={source}
      poster={poster}
      muted
      loop
      playsInline
      disablePictureInPicture
      preload={eager ? 'metadata' : 'none'}
      aria-label={alt || undefined}
      aria-hidden={alt ? undefined : true}
    />
  }
  return <img className={className} src={source} alt={alt} loading={eager ? 'eager' : 'lazy'} />
}
