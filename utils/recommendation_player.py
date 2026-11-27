"""Self-contained browser audio player for recommendation tracks."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

import streamlit as st

PLAYER_FRAME_HEIGHT = 170

PLAYER_COMPONENT_HTML = r"""
<!doctype html>
<html lang="id">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Pemutar TuneCluster</title>
    <style>
        * { box-sizing: border-box; }
        html, body {
            width: 100%;
            height: 100%;
            margin: 0;
            overflow: hidden;
            background: transparent;
        }
        body {
            color: #f5f5f5;
            font: 13px/1.3 Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        #tc-recommendation-player {
            display: grid;
            grid-template-columns: 48px minmax(100px, 1fr) auto minmax(140px, 1.15fr) 220px;
            grid-template-areas: "cover info controls progress volume" "status status status status status";
            align-items: center;
            gap: 8px 12px;
            width: 100%;
            padding: 12px 16px;
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 16px;
            background: rgba(15, 15, 15, 0.97);
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.42);
        }
        #tc-recommendation-player[hidden],
        #tc-recommendation-player [hidden] {
            display: none !important;
        }
        .tc-player-cover {
            grid-area: cover;
            display: block;
            width: 48px;
            height: 48px;
            border-radius: 8px;
            object-fit: cover;
            background: #070707;
        }
        .tc-player-info { min-width: 0; grid-area: info; }
        .tc-player-title, .tc-player-artist {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .tc-player-title { color: #fff; font-size: 13px; font-weight: 650; }
        .tc-player-artist { margin-top: 4px; color: #a0a0a0; font-size: 11px; }
        .tc-player-controls {
            grid-area: controls;
            display: flex;
            align-items: center;
            gap: 2px;
        }
        .tc-icon-button, .tc-mute-button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 44px;
            width: 44px;
            height: 44px;
            padding: 0;
            border: 0;
            border-radius: 50%;
            background: transparent;
            color: #f5f5f5;
            cursor: pointer;
        }
        .tc-icon-surface {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: #242424;
        }
        .tc-icon-button:hover .tc-icon-surface,
        .tc-mute-button:hover { background: #343434; }
        .tc-player-toggle { flex-basis: 48px; width: 48px; height: 48px; }
        .tc-player-toggle .tc-icon-surface {
            width: 40px;
            height: 40px;
            background: #1db954;
            color: #06160b;
        }
        .tc-player-toggle:hover .tc-icon-surface { background: #35cf6c; }
        .tc-icon-button:focus-visible, .tc-mute-button:focus-visible,
        .tc-player-volume input:focus-visible, .tc-player-progress input:focus-visible {
            outline: 2px solid #fff;
            outline-offset: 2px;
        }
        .tc-icon-button svg, .tc-mute-button svg {
            display: block;
            width: 19px;
            height: 19px;
            fill: currentColor;
        }
        .tc-player-toggle svg { width: 20px; height: 20px; }
        .tc-player-progress {
            grid-area: progress;
            display: grid;
            grid-template-columns: 34px minmax(40px, 1fr) 34px;
            align-items: center;
            gap: 6px;
            min-width: 0;
        }
        .tc-player-time {
            color: #b7b7b7;
            font-size: 10px;
            font-variant-numeric: tabular-nums;
            text-align: center;
        }
        .tc-player-progress input, .tc-player-volume input {
            height: 20px;
            margin: 0;
            accent-color: #1db954;
            cursor: pointer;
        }
        .tc-player-progress input { width: 100%; min-width: 40px; }
        .tc-player-volume {
            grid-area: volume;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 6px;
            min-width: 220px;
            color: #b7b7b7;
            font-size: 10px;
        }
        .tc-player-volume-label { flex: 0 0 auto; }
        .tc-player-volume input {
            flex: 0 0 96px;
            width: 96px;
            min-width: 96px;
        }
        .tc-mute-button {
            flex-basis: 32px;
            width: 32px;
            height: 36px;
            color: #e6e6e6;
        }
        .tc-mute-button svg { width: 18px; height: 18px; }
        .tc-player-volume-value {
            flex: 0 0 34px;
            color: #d3d3d3;
            font-variant-numeric: tabular-nums;
            text-align: right;
        }
        .tc-player-status {
            grid-area: status;
            min-width: 0;
            color: #d0d0d0;
            font-size: 11px;
        }
        .tc-player-status a {
            margin-left: 8px;
            color: #75d895;
            text-decoration: underline;
        }
        @media (max-width: 760px) {
            #tc-recommendation-player {
                grid-template-columns: 40px minmax(0, 1fr) auto;
                grid-template-areas: "cover info controls" "progress progress progress" "volume volume volume" "status status status";
                gap: 6px 8px;
                padding: 10px 12px;
                border-radius: 14px;
            }
            .tc-player-cover { width: 40px; height: 40px; }
            .tc-player-controls { gap: 0; }
            .tc-icon-button { flex-basis: 42px; width: 42px; height: 44px; }
            .tc-player-toggle { flex-basis: 46px; width: 46px; height: 46px; }
            .tc-player-progress { grid-template-columns: 34px minmax(0, 1fr) 34px; }
            .tc-player-volume {
                justify-content: flex-end;
                width: 100%;
                min-width: 0;
            }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { scroll-behavior: auto !important; }
        }
    </style>
</head>
<body>
    <main id="tc-recommendation-player" role="region" aria-label="Pemutar lagu" hidden>
        <img class="tc-player-cover" data-player-cover alt="">
        <div class="tc-player-info">
            <div class="tc-player-title" data-player-title></div>
            <div class="tc-player-artist" data-player-artist></div>
        </div>
        <div class="tc-player-controls">
            <button class="tc-icon-button" type="button" data-player-action="prev"
                    aria-label="Lagu sebelumnya" title="Lagu sebelumnya">
                <span class="tc-icon-surface" aria-hidden="true">
                    <svg viewBox="0 0 24 24"><path d="M6 5v14H4V5h2zm14 0v14L9 12l11-7z"></path></svg>
                </span>
            </button>
            <button class="tc-icon-button tc-player-toggle" type="button"
                    data-player-action="toggle" aria-label="Putar" title="Putar">
                <span class="tc-icon-surface" data-player-toggle-icon aria-hidden="true"></span>
            </button>
            <button class="tc-icon-button" type="button" data-player-action="next"
                    aria-label="Lagu berikutnya" title="Lagu berikutnya">
                <span class="tc-icon-surface" aria-hidden="true">
                    <svg viewBox="0 0 24 24"><path d="M18 5v14h2V5h-2zM4 5v14l11-7L4 5z"></path></svg>
                </span>
            </button>
        </div>
        <div class="tc-player-progress">
            <span class="tc-player-time" data-player-current-time>0:00</span>
            <input type="range" min="0" max="100" step="0.1" value="0"
                   data-player-seek aria-label="Posisi lagu" disabled>
            <span class="tc-player-time" data-player-duration>0:00</span>
        </div>
        <div class="tc-player-volume">
            <span class="tc-player-volume-label">Volume</span>
            <input type="range" min="0" max="1" step="0.01" value="0.8"
                   data-player-volume aria-label="Volume">
            <button class="tc-mute-button" type="button" data-player-mute
                    aria-label="Bisukan audio" title="Bisukan audio">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M3 9v6h4l5 5V4L7 9H3z"></path>
                    <path data-volume-wave d="M16.5 12a4.5 4.5 0 0 0-2.5-4.03v8.05a4.5 4.5 0 0 0 2.5-4.02z"></path>
                    <path data-volume-mute d="M16 9l5 6m0-6l-5 6"
                          fill="none" stroke="currentColor" stroke-width="2" hidden></path>
                </svg>
            </button>
            <span class="tc-player-volume-value" data-player-volume-value>80%</span>
        </div>
        <div class="tc-player-status" data-player-status aria-live="polite" hidden>
            <span data-player-status-text></span>
            <a data-player-link target="_blank" rel="noopener noreferrer" hidden>Buka di Spotify</a>
        </div>
    </main>
    <script>
    (() => {
        "use strict";
        const tracks = __TRACKS_JSON__;
        const defaultTrackId = __DEFAULT_TRACK_ID__;
        const player = document.getElementById("tc-recommendation-player");
        const audio = new Audio();
        audio.preload = "metadata";
        audio.setAttribute("aria-label", "Preview lagu");
        document.body.appendChild(audio);

        const refs = {
            cover: player.querySelector("[data-player-cover]"),
            title: player.querySelector("[data-player-title]"),
            artist: player.querySelector("[data-player-artist]"),
            previous: player.querySelector('[data-player-action="prev"]'),
            toggle: player.querySelector('[data-player-action="toggle"]'),
            toggleIcon: player.querySelector("[data-player-toggle-icon]"),
            next: player.querySelector('[data-player-action="next"]'),
            currentTime: player.querySelector("[data-player-current-time]"),
            duration: player.querySelector("[data-player-duration]"),
            seek: player.querySelector("[data-player-seek]"),
            volume: player.querySelector("[data-player-volume]"),
            mute: player.querySelector("[data-player-mute]"),
            volumeValue: player.querySelector("[data-player-volume-value]"),
            volumeWave: player.querySelector("[data-volume-wave]"),
            volumeMute: player.querySelector("[data-volume-mute]"),
            status: player.querySelector("[data-player-status]"),
            statusText: player.querySelector("[data-player-status-text]"),
            statusLink: player.querySelector("[data-player-link]"),
        };
        let currentTrack = tracks.find((track) => track.track_id === defaultTrackId)
            || tracks[0]
            || null;
        let playRequestId = 0;
        let recovery = null;
        let lastAudibleVolume = 0.8;
        player.hidden = !currentTrack;

        function formatTime(seconds) {
            if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
            const total = Math.floor(seconds);
            return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
        }

        function showStatus(message, href = "") {
            refs.statusText.textContent = message;
            refs.statusLink.hidden = !href;
            if (href) refs.statusLink.href = href;
            refs.status.hidden = !message;
        }

        function saveVolume() {
            try {
                window.localStorage.setItem("tc_volume", String(audio.volume));
                window.localStorage.setItem("tc_muted", String(audio.muted));
            } catch (error) {
                console.warn("[TuneCluster player] volume preference could not be saved", error);
            }
        }

        function renderVolume() {
            const audible = audio.volume > 0 && !audio.muted;
            refs.volume.value = String(audio.volume);
            refs.volumeValue.textContent = `${Math.round(audio.volume * 100)}%`;
            refs.volumeWave.hidden = !audible;
            refs.volumeMute.hidden = audible;
            const label = audible ? "Bisukan audio" : "Nyalakan audio";
            refs.mute.setAttribute("aria-label", label);
            refs.mute.title = label;
        }

        function setVolume(value) {
            const parsed = Number(value);
            const volume = Number.isFinite(parsed) ? Math.min(1, Math.max(0, parsed)) : 0.8;
            audio.volume = volume;
            audio.muted = volume === 0;
            if (volume > 0) lastAudibleVolume = volume;
            renderVolume();
            saveVolume();
        }

        function restoreVolume() {
            try {
                const storedVolumeValue = window.localStorage.getItem("tc_volume");
                const storedVolume = storedVolumeValue === null
                    ? NaN
                    : Number(storedVolumeValue);
                const volume = Number.isFinite(storedVolume)
                    ? Math.min(1, Math.max(0, storedVolume))
                    : 0.8;
                const storedMuted = window.localStorage.getItem("tc_muted") === "true";
                audio.volume = volume;
                audio.muted = storedMuted || volume === 0;
                lastAudibleVolume = volume > 0 ? volume : 0.8;
            } catch (error) {
                audio.volume = 0.8;
                audio.muted = false;
                lastAudibleVolume = 0.8;
                console.warn("[TuneCluster player] volume preference could not be read", error);
            }
            renderVolume();
        }

        function toggleMute() {
            if (audio.muted || audio.volume === 0) {
                audio.volume = lastAudibleVolume > 0 ? lastAudibleVolume : 0.8;
                audio.muted = false;
            } else {
                lastAudibleVolume = audio.volume;
                audio.muted = true;
            }
            renderVolume();
            saveVolume();
        }

        function render() {
            if (!currentTrack) return;
            player.hidden = false;
            const cover = currentTrack.cover_url || "";
            if (cover) refs.cover.src = cover;
            else refs.cover.removeAttribute("src");
            refs.cover.alt = `Sampul ${currentTrack.track_name}`;
            refs.title.textContent = currentTrack.track_name || "Tanpa Judul";
            refs.artist.textContent = currentTrack.artists || "Artis tidak diketahui";
            const playing = !audio.paused && !audio.ended;
            refs.toggle.setAttribute("aria-label", playing ? "Jeda" : "Putar");
            refs.toggle.title = playing ? "Jeda" : "Putar";
            refs.toggleIcon.innerHTML = playing
                ? '<svg viewBox="0 0 24 24"><path d="M7 5h4v14H7zM15 5h4v14h-4z"></path></svg>'
                : '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7L8 5z"></path></svg>';
            refs.currentTime.textContent = formatTime(audio.currentTime);
            refs.duration.textContent = formatTime(audio.duration);
            refs.seek.value = Number.isFinite(audio.duration) && audio.duration > 0
                ? String((audio.currentTime / audio.duration) * 100)
                : "0";
            refs.seek.disabled = !Number.isFinite(audio.duration) || audio.duration <= 0;
            renderVolume();
        }

        function normalize(value) {
            return String(value || "")
                .normalize("NFKC")
                .toLocaleLowerCase()
                .replace(/[^\p{L}\p{N}]+/gu, " ")
                .trim();
        }

        function primaryArtist(artists) {
            return String(artists || "").split(/[;,]/, 1)[0].trim();
        }

        async function fetchFreshITunesPreview(track) {
            const query = encodeURIComponent(
                `${track.track_name || ""} ${primaryArtist(track.artists)}`.trim(),
            );
            const controller = new AbortController();
            const timeout = window.setTimeout(() => controller.abort(), 4500);
            try {
                const response = await fetch(
                    `https://itunes.apple.com/search?term=${query}&entity=song&limit=3`,
                    {
                        cache: "no-store",
                        headers: { Accept: "application/json" },
                        signal: controller.signal,
                    },
                );
                if (!response.ok) throw new Error(`iTunes returned HTTP ${response.status}`);
                const payload = await response.json();
                const requestedTitle = normalize(track.track_name);
                const requestedArtist = normalize(primaryArtist(track.artists));
                const records = Array.isArray(payload.results) ? payload.results : [];
                const candidates = records
                    .filter((record) => (
                        typeof record.previewUrl === "string"
                        && record.previewUrl.startsWith("https://audio-ssl.itunes.apple.com/")
                    ))
                    .map((record) => {
                        const resultTitle = normalize(record.trackName);
                        const resultArtist = normalize(record.artistName);
                        const titleMatch = resultTitle === requestedTitle
                            || resultTitle.includes(requestedTitle)
                            || requestedTitle.includes(resultTitle);
                        const artistMatch = resultArtist === requestedArtist
                            || resultArtist.includes(requestedArtist);
                        return {
                            previewUrl: record.previewUrl,
                            score: Number(titleMatch) * 2 + Number(artistMatch),
                        };
                    })
                    .filter((record) => record.score > 0)
                    .sort((left, right) => right.score - left.score);
                return candidates[0]?.previewUrl || null;
            } finally {
                window.clearTimeout(timeout);
            }
        }

        function finishPlaybackFailure(track, message = "Preview tidak tersedia") {
            audio.pause();
            showStatus(message, track.spotify_url || "");
            render();
        }

        function recoverPreview(track, requestId, failedUrl) {
            if (
                !recovery
                || recovery.requestId !== requestId
                || requestId !== playRequestId
                || recovery.pending
            ) return;
            recovery.pending = true;
            showStatus("Memuat preview...");
            void (async () => {
                if (!recovery.refreshed) {
                    recovery.refreshed = true;
                    try {
                        const freshUrl = await fetchFreshITunesPreview(track);
                        if (requestId !== playRequestId) return;
                        if (freshUrl && freshUrl !== failedUrl) {
                            track.preview_url = freshUrl;
                            recovery.pending = false;
                            loadAndPlay(track, freshUrl, requestId);
                            return;
                        }
                    } catch (error) {
                        if (requestId !== playRequestId) return;
                        console.warn("[TuneCluster player] fresh iTunes lookup failed", {
                            track: track.track_name,
                            error,
                        });
                    }
                }
                if (requestId !== playRequestId) return;
                const fallbackUrl = track.fallback_preview_url;
                if (
                    fallbackUrl
                    && fallbackUrl !== failedUrl
                    && !recovery.fallbackAttempted
                ) {
                    recovery.fallbackAttempted = true;
                    recovery.pending = false;
                    showStatus("Memuat preview cadangan...");
                    loadAndPlay(track, fallbackUrl, requestId);
                    return;
                }
                recovery.pending = false;
                finishPlaybackFailure(track);
            })();
        }

        function loadAndPlay(track, previewUrl, requestId) {
            if (requestId !== playRequestId) return;
            audio.pause();
            audio.currentTime = 0;
            audio.src = previewUrl;
            audio.load();
            restoreVolume();
            render();
            const playRequest = audio.play();
            if (playRequest && typeof playRequest.catch === "function") {
                playRequest.catch((error) => {
                    if (requestId !== playRequestId || error.name === "AbortError") return;
                    if (error.name === "NotAllowedError") {
                        finishPlaybackFailure(track, "Browser memblokir audio. Tekan Putar lagi.");
                        return;
                    }
                    recoverPreview(track, requestId, previewUrl);
                });
            }
        }

        function playTrack(track) {
            currentTrack = track;
            const requestId = ++playRequestId;
            console.log("[TuneCluster player] play", {
                track: track.track_name,
                preview_url: track.preview_url || "",
            });
            recovery = {
                requestId,
                refreshed: false,
                fallbackAttempted: false,
                pending: false,
            };
            showStatus("Memuat preview...");
            render();
            if (track.preview_url) {
                loadAndPlay(track, track.preview_url, requestId);
            } else {
                recoverPreview(track, requestId, "");
            }
        }

        function skip(offset) {
            if (!tracks.length) return;
            const currentIndex = tracks.findIndex(
                (track) => track.track_id === currentTrack?.track_id,
            );
            const nextIndex = currentIndex < 0
                ? (offset > 0 ? 0 : tracks.length - 1)
                : (currentIndex + offset + tracks.length) % tracks.length;
            playTrack(tracks[nextIndex]);
        }

        refs.previous.addEventListener("click", () => skip(-1));
        refs.toggle.addEventListener("click", () => {
            if (!currentTrack) return;
            if (audio.paused || audio.ended) playTrack(currentTrack);
            else audio.pause();
        });
        refs.next.addEventListener("click", () => skip(1));
        refs.seek.addEventListener("input", () => {
            if (Number.isFinite(audio.duration) && audio.duration > 0) {
                audio.currentTime = (Number(refs.seek.value) / 100) * audio.duration;
                refs.currentTime.textContent = formatTime(audio.currentTime);
            }
        });
        refs.volume.addEventListener("input", () => setVolume(refs.volume.value));
        refs.volume.addEventListener("change", () => setVolume(refs.volume.value));
        refs.mute.addEventListener("click", toggleMute);
        audio.addEventListener("play", () => {
            showStatus("");
            render();
        });
        audio.addEventListener("playing", render);
        audio.addEventListener("pause", render);
        audio.addEventListener("timeupdate", render);
        audio.addEventListener("loadedmetadata", render);
        audio.addEventListener("ended", render);
        audio.addEventListener("volumechange", renderVolume);
        audio.addEventListener("error", () => {
            if (!currentTrack || !audio.src || (audio.error && audio.error.code === 1)) return;
            recoverPreview(currentTrack, playRequestId, audio.src);
        });
        restoreVolume();
        render();
    })();
    </script>
</body>
</html>
"""


def _serialize_script_json(value: object) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def serialize_player_tracks(tracks: Sequence[Mapping[str, object]]) -> str:
    """Serialize track data safely for the isolated browser player."""
    payload = []
    for track in tracks:
        raw_card_keys = track.get("card_keys")
        card_keys = (
            raw_card_keys
            if isinstance(raw_card_keys, (list, tuple))
            else [track.get("track_id")]
        )
        payload.append(
            {
                "track_id": str(track.get("track_id") or ""),
                "track_name": str(track.get("track_name") or "Tanpa Judul"),
                "artists": str(track.get("artists") or "Artis tidak diketahui"),
                "cover_url": str(track.get("cover_url") or ""),
                "preview_url": (
                    str(track.get("preview_url")).strip()
                    if track.get("preview_url")
                    else None
                ),
                "fallback_preview_url": (
                    str(track.get("fallback_preview_url")).strip()
                    if track.get("fallback_preview_url")
                    else None
                ),
                "spotify_url": str(track.get("spotify_url") or ""),
                "card_keys": [str(key) for key in card_keys if key],
            }
        )
    return _serialize_script_json(payload)


def render_recommendation_player(
    tracks: Sequence[Mapping[str, object]],
    *,
    default_track_id: str | None = None,
) -> None:
    """Render the audio controls in one self-contained iframe."""
    if not tracks:
        return
    component_html = PLAYER_COMPONENT_HTML.replace(
        "__TRACKS_JSON__",
        serialize_player_tracks(tracks),
    ).replace(
        "__DEFAULT_TRACK_ID__",
        _serialize_script_json(default_track_id or ""),
    )
    with st.container(key="tc-recommendation-player-host"):
        st.components.v1.html(
            component_html,
            height=PLAYER_FRAME_HEIGHT,
            scrolling=False,
        )
