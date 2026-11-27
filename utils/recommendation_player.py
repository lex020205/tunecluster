"""Browser-side direct playback controls for recommendation cards."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

import streamlit as st

PLAYER_COMPONENT_HTML = r"""
<script>
(() => {
    const incomingTracks = __TRACKS_JSON__;
    const incomingDefaultTrackId = __DEFAULT_TRACK_ID__;
    const host = window.parent;
    const doc = host.document;
    const playerVersion = 9;
    let player = host.__tcRecommendationPlayer;

    if (player && player.version > playerVersion) return;

    if (
        player
        && (
            player.version !== playerVersion
            || !doc.getElementById("tc-recommendation-player")
            || !doc.getElementById("tc-recommendation-audio")
        )
    ) {
        if (typeof player.dispose === "function") player.dispose();
        doc.getElementById("tc-recommendation-player")?.remove();
        doc.getElementById("tc-recommendation-audio")?.remove();
        doc.querySelector('audio[aria-hidden="true"]')?.remove();
        doc.getElementById("tc-recommendation-player-styles")?.remove();
        player = null;
    }

    if (!player) {
        const style = doc.createElement("style");
        style.id = "tc-recommendation-player-styles";
        style.textContent = `
            body:not(:has(.tc-rec-scope-marker)) #tc-recommendation-player {
                display: none !important;
            }
            #tc-recommendation-player {
                position: fixed;
                z-index: 99999;
                left: calc((100vw + 16rem) / 2);
                bottom: calc(16px + env(safe-area-inset-bottom));
                transform: translateX(-50%);
                display: grid;
                grid-template-columns: 48px minmax(110px, 1fr) auto minmax(150px, 1.2fr) 100px;
                grid-template-areas: "cover info controls progress volume" "status status status status status";
                align-items: center;
                gap: 8px 12px;
                width: min(760px, calc(100vw - 16rem - 32px));
                padding: 12px 16px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
                background: rgba(15, 15, 15, 0.96);
                color: #f5f5f5;
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.55);
                font: 13px/1.3 Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                backdrop-filter: blur(18px);
            }
            #tc-recommendation-player[hidden],
            #tc-recommendation-player [hidden] {
                display: none !important;
            }
            #tc-recommendation-player .tc-player-cover {
                grid-area: cover;
                width: 48px;
                height: 48px;
                border-radius: 8px;
                object-fit: cover;
                background: #070707;
            }
            #tc-recommendation-player .tc-player-info {
                grid-area: info;
                min-width: 0;
            }
            #tc-recommendation-player .tc-player-title,
            #tc-recommendation-player .tc-player-artist {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            #tc-recommendation-player .tc-player-title {
                color: #fff;
                font-size: 13px;
                font-weight: 650;
            }
            #tc-recommendation-player .tc-player-artist {
                margin-top: 4px;
                color: #929292;
                font-size: 11px;
            }
            #tc-recommendation-player .tc-player-controls {
                grid-area: controls;
                display: flex;
                align-items: center;
                gap: 5px;
            }
            #tc-recommendation-player button {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 34px;
                height: 34px;
                padding: 0 8px;
                border: 1px solid rgba(255, 255, 255, 0.13);
                border-radius: 999px;
                background: #202020;
                color: #f5f5f5;
                font: inherit;
                cursor: pointer;
            }
            #tc-recommendation-player button:hover {
                background: #303030;
            }
            #tc-recommendation-player button:focus {
                outline: none;
            }
            #tc-recommendation-player button:focus-visible {
                outline: 2px solid rgba(255, 255, 255, 0.72);
                outline-offset: 2px;
            }
            #tc-recommendation-player .tc-player-toggle {
                min-width: 42px;
                border-color: rgba(29, 185, 84, 0.65);
                background: #123321;
                color: #d7ffe5;
                font-weight: 600;
            }
            #tc-recommendation-player .tc-player-progress {
                grid-area: progress;
                display: grid;
                grid-template-columns: 34px minmax(40px, 1fr) 34px;
                align-items: center;
                gap: 6px;
            }
            #tc-recommendation-player .tc-player-time {
                color: #969696;
                font-size: 10px;
                font-variant-numeric: tabular-nums;
                text-align: center;
            }
            #tc-recommendation-player input[type="range"] {
                width: 100%;
                height: 4px;
                accent-color: #1db954;
                cursor: pointer;
            }
            #tc-recommendation-player .tc-player-volume {
                grid-area: volume;
                display: flex;
                align-items: center;
                gap: 7px;
                color: #969696;
                font-size: 10px;
            }
            #tc-recommendation-player .tc-player-volume input {
                min-width: 0;
            }
            #tc-recommendation-player .tc-player-volume-indicator {
                display: inline-flex;
                align-items: center;
                justify-content: flex-end;
                gap: 3px;
                min-width: 42px;
                color: #b7b7b7;
                font-variant-numeric: tabular-nums;
                text-align: right;
            }
            #tc-recommendation-player .tc-player-volume-indicator svg {
                width: 14px;
                height: 14px;
                flex: none;
                fill: currentColor;
            }
            #tc-recommendation-player .tc-player-status {
                grid-area: status;
                color: #b7b7b7;
                font-size: 11px;
            }
            #tc-recommendation-player .tc-player-status a {
                margin-left: 8px;
                color: #75d895;
            }
            .tc-rec-playing [data-testid="stButton"] button {
                border-color: #1db954 !important;
                background: rgba(18, 51, 33, 0.94) !important;
            }
            .tc-rec-playing [data-testid="stIconMaterial"] {
                color: #1db954 !important;
            }
            @media (max-width: 760px) {
                #tc-recommendation-player {
                    left: 50%;
                    width: calc(100vw - 32px);
                    grid-template-columns: 40px minmax(40px, 1fr) auto;
                    grid-template-areas: "cover info controls" "progress progress progress" "volume volume volume" "status status status";
                    gap: 8px 10px;
                    padding: 10px 12px;
                    border-radius: 16px;
                }
                #tc-recommendation-player .tc-player-cover {
                    width: 40px;
                    height: 40px;
                }
                #tc-recommendation-player .tc-player-controls {
                    gap: 4px;
                }
                #tc-recommendation-player .tc-player-controls button {
                    min-width: 31px;
                    height: 32px;
                    padding: 0 6px;
                    font-size: 11px;
                }
                #tc-recommendation-player .tc-player-toggle {
                    min-width: 40px !important;
                }
                #tc-recommendation-player .tc-player-volume {
                    justify-self: end;
                    width: 100%;
                    justify-content: flex-end;
                }
                #tc-recommendation-player .tc-player-volume input {
                    width: min(120px, 40vw);
                }
            }
        `;
        doc.head.appendChild(style);

        const bar = doc.createElement("div");
        bar.id = "tc-recommendation-player";
        bar.hidden = true;
        bar.setAttribute("role", "region");
        bar.setAttribute("aria-label", "Pemutar lagu");
        bar.innerHTML = `
            <img class="tc-player-cover" data-player-cover alt="">
            <div class="tc-player-info">
                <div class="tc-player-title" data-player-title></div>
                <div class="tc-player-artist" data-player-artist></div>
            </div>
            <div class="tc-player-controls">
                <button type="button" data-player-action="prev" aria-label="Lagu sebelumnya">Prev</button>
                <button class="tc-player-toggle" type="button" data-player-action="toggle"
                        aria-label="Putar atau jeda">Play</button>
                <button type="button" data-player-action="next" aria-label="Lagu berikutnya">Next</button>
            </div>
            <div class="tc-player-progress">
                <span class="tc-player-time" data-player-current-time>0:00</span>
                <input type="range" min="0" max="100" step="0.1" value="0"
                       data-player-seek aria-label="Posisi lagu">
                <span class="tc-player-time" data-player-duration>0:00</span>
            </div>
            <label class="tc-player-volume">
                <span>Volume</span>
                <input type="range" min="0" max="1" step="0.01" value="0.8"
                       data-player-volume aria-label="Volume">
                <span class="tc-player-volume-indicator" data-player-volume-indicator
                      aria-live="polite">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M3 9v6h4l5 5V4L7 9H3z"></path>
                        <path data-player-volume-wave
                              d="M16.5 12a4.5 4.5 0 0 0-2.5-4.03v8.05a4.5 4.5 0 0 0 2.5-4.02z"></path>
                        <path data-player-volume-mute d="M15 9l6 6m0-6l-6 6"
                              fill="none" stroke="currentColor" stroke-width="2"></path>
                    </svg>
                    <span data-player-volume-value>80%</span>
                </span>
            </label>
            <div class="tc-player-status" data-player-status hidden>
                <span data-player-status-text></span>
                <a data-player-link target="_blank" rel="noopener noreferrer" hidden>Buka di Spotify</a>
            </div>
        `;
        doc.body.appendChild(bar);

        const audio = doc.createElement("audio");
        audio.id = "tc-recommendation-audio";
        audio.preload = "none";
        audio.hidden = true;
        audio.setAttribute("aria-hidden", "true");
        audio.playsInline = true;
        doc.body.appendChild(audio);
        const refs = {
            cover: bar.querySelector("[data-player-cover]"),
            title: bar.querySelector("[data-player-title]"),
            artist: bar.querySelector("[data-player-artist]"),
            previous: bar.querySelector('[data-player-action="prev"]'),
            toggle: bar.querySelector('[data-player-action="toggle"]'),
            next: bar.querySelector('[data-player-action="next"]'),
            currentTime: bar.querySelector("[data-player-current-time]"),
            duration: bar.querySelector("[data-player-duration]"),
            seek: bar.querySelector("[data-player-seek]"),
            volume: bar.querySelector("[data-player-volume]"),
            volumeIndicator: bar.querySelector("[data-player-volume-indicator]"),
            volumeValue: bar.querySelector("[data-player-volume-value]"),
            volumeWave: bar.querySelector("[data-player-volume-wave]"),
            volumeMute: bar.querySelector("[data-player-volume-mute]"),
            status: bar.querySelector("[data-player-status]"),
            statusText: bar.querySelector("[data-player-status-text]"),
            statusLink: bar.querySelector("[data-player-link]"),
        };
        let tracks = [];
        let currentTrack = null;
        let defaultTrackId = "";
        let statusMessage = "";
        let statusLink = "";
        let active = true;
        let reservedBlock = null;
        let originalPadding = "";
        let playRequestId = 0;

        function reserveSpace(enabled) {
            const block = doc.querySelector('[data-testid="stMainBlockContainer"]');
            if (reservedBlock && reservedBlock !== block) {
                reservedBlock.style.paddingBottom = originalPadding;
                reservedBlock = null;
            }
            if (enabled && block) {
                if (!reservedBlock) {
                    reservedBlock = block;
                    originalPadding = block.style.paddingBottom;
                }
                block.style.paddingBottom = "110px";
            } else if (reservedBlock) {
                reservedBlock.style.paddingBottom = originalPadding;
                reservedBlock = null;
            }
        }

        function formatTime(seconds) {
            if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
            const total = Math.floor(seconds);
            return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
        }

        function showStatus(message, href = "") {
            statusMessage = message;
            statusLink = href;
            if (refs.statusText.textContent !== message) {
                refs.statusText.textContent = message;
            }
            refs.statusLink.hidden = !href;
            if (href && refs.statusLink.href !== href) {
                refs.statusLink.href = href;
            }
            refs.status.hidden = !message;
        }

        function setVolume(value, persist = true) {
            const parsedVolume = Number(value);
            const volume = Number.isFinite(parsedVolume)
                ? Math.min(1, Math.max(0, parsedVolume))
                : 0.8;
            audio.volume = volume;
            audio.muted = volume === 0;
            refs.volume.value = String(volume);
            refs.volumeValue.textContent = `${Math.round(volume * 100)}%`;
            refs.volumeWave.hidden = volume === 0;
            refs.volumeMute.hidden = volume !== 0;
            refs.volumeIndicator.setAttribute(
                "aria-label",
                volume === 0 ? "Audio dibisukan" : `Volume ${Math.round(volume * 100)} persen`,
            );
            if (persist) {
                try {
                    host.localStorage.setItem("tc_volume", String(volume));
                } catch (error) {
                    console.warn("Volume preference could not be saved.", error);
                }
            }
        }

        function restoreVolume() {
            let savedVolume = 0.8;
            try {
                const storedValue = host.localStorage.getItem("tc_volume");
                if (storedValue !== null && Number.isFinite(Number(storedValue))) {
                    savedVolume = Number(storedValue);
                }
            } catch (error) {
                console.warn("Volume preference could not be read.", error);
            }
            setVolume(savedVolume, false);
        }

        function syncCards() {
            const prefix = "st-key-play_recommended_track_";
            doc.querySelectorAll('div[class*="st-key-play_recommended_track_"]').forEach((wrapper) => {
                const key = Array.from(wrapper.classList).find((name) => name.startsWith(prefix));
                const cardKey = key ? key.slice(prefix.length) : "";
                const cardTrack = tracks.find((track) => (
                    track.track_id === cardKey
                    || (Array.isArray(track.card_keys) && track.card_keys.includes(cardKey))
                ));
                const button = wrapper.querySelector('[data-testid="stButton"] button');
                if (!button) return;
                const isCurrent = Boolean(
                    currentTrack && cardTrack && cardTrack.track_id === currentTrack.track_id
                );
                const isPlaying = isCurrent && !audio.paused;
                wrapper.classList.toggle("tc-rec-playing", isPlaying);
                if (button.getAttribute("aria-pressed") !== String(isPlaying)) {
                    button.setAttribute("aria-pressed", String(isPlaying));
                }
                const label = isPlaying
                    ? `Jeda ${currentTrack.track_name}`
                    : `Putar ${isCurrent ? currentTrack.track_name : ""}`.trim();
                if (button.getAttribute("aria-label") !== label) {
                    button.setAttribute("aria-label", label);
                    button.title = label;
                }
                const icon = button.querySelector('[data-testid="stIconMaterial"]');
                const iconName = isPlaying ? "pause" : "play_arrow";
                if (icon && icon.textContent.trim() !== iconName) {
                    icon.textContent = iconName;
                }
            });
        }

        function render() {
            if (!currentTrack) {
                bar.hidden = true;
                reserveSpace(false);
                syncCards();
                return;
            }
            bar.hidden = !active;
            reserveSpace(active);
            const coverUrl = currentTrack.cover_url || "";
            if (refs.cover.getAttribute("src") !== coverUrl) {
                if (coverUrl) refs.cover.setAttribute("src", coverUrl);
                else refs.cover.removeAttribute("src");
            }
            refs.cover.alt = `Sampul ${currentTrack.track_name}`;
            if (refs.title.textContent !== currentTrack.track_name) {
                refs.title.textContent = currentTrack.track_name;
            }
            if (refs.artist.textContent !== currentTrack.artists) {
                refs.artist.textContent = currentTrack.artists;
            }
            const toggleLabel = audio.paused ? "Play" : "Pause";
            if (refs.toggle.textContent !== toggleLabel) {
                refs.toggle.textContent = toggleLabel;
            }
            const toggleAriaLabel = audio.paused ? "Putar" : "Jeda";
            if (refs.toggle.getAttribute("aria-label") !== toggleAriaLabel) {
                refs.toggle.setAttribute("aria-label", toggleAriaLabel);
            }
            const currentTime = formatTime(audio.currentTime);
            const duration = formatTime(audio.duration);
            if (refs.currentTime.textContent !== currentTime) {
                refs.currentTime.textContent = currentTime;
            }
            if (refs.duration.textContent !== duration) {
                refs.duration.textContent = duration;
            }
            refs.seek.value = Number.isFinite(audio.duration) && audio.duration > 0
                ? String((audio.currentTime / audio.duration) * 100)
                : "0";
            refs.seek.disabled = !Number.isFinite(audio.duration) || audio.duration <= 0;
            refs.volume.value = String(audio.volume);
            showStatus(statusMessage, statusLink);
            syncCards();
        }

        function primaryPreviewUrl(track) {
            return track.preview_url || track.fallback_preview_url || "";
        }

        function tryFallbackPreview(track, requestId) {
            const fallbackUrl = track.fallback_preview_url;
            if (
                !track.preview_url
                || !fallbackUrl
                || fallbackUrl === track.preview_url
                || requestId !== playRequestId
                || audio.getAttribute("src") !== track.preview_url
            ) {
                return false;
            }
            console.info("[TuneCluster player] retrying with fallback preview", {
                track: track.track_name,
                preview_url: fallbackUrl,
            });
            audio.pause();
            audio.currentTime = 0;
            audio.src = fallbackUrl;
            audio.load();
            showStatus("Memuat preview cadangan...");
            render();
            const fallbackRequest = audio.play();
            if (fallbackRequest && typeof fallbackRequest.catch === "function") {
                fallbackRequest.catch((error) => {
                    if (
                        requestId !== playRequestId
                        || (error && error.name === "AbortError")
                        || audio.getAttribute("src") !== fallbackUrl
                    ) {
                        return;
                    }
                    console.error("[TuneCluster player] fallback audio.play() failed", {
                        track: track.track_name,
                        preview_url: fallbackUrl,
                        error,
                    });
                    audio.pause();
                    showStatus("Preview audio tidak tersedia untuk lagu ini", track.spotify_url);
                    render();
                });
            }
            return true;
        }

        function playTrack(track, restart = true) {
            currentTrack = track;
            const requestId = ++playRequestId;
            const previewUrl = primaryPreviewUrl(track);
            console.log("[TuneCluster player] play requested", {
                track: track.track_name,
                preview_url: previewUrl || null,
                fallback_preview_url: track.fallback_preview_url || null,
            });
            if (!previewUrl) {
                audio.pause();
                audio.currentTime = 0;
                audio.removeAttribute("src");
                audio.load();
                restoreVolume();
                showStatus("Preview audio tidak tersedia untuk lagu ini", track.spotify_url);
                render();
                return;
            }
            restoreVolume();
            showStatus("Memuat preview...");
            const sourceChanged = audio.getAttribute("src") !== previewUrl;
            if (restart || sourceChanged) {
                audio.pause();
                audio.currentTime = 0;
                audio.src = previewUrl;
                audio.load();
            }
            render();
            const playRequest = audio.play();
            if (playRequest && typeof playRequest.catch === "function") {
                playRequest.catch((error) => {
                    if (requestId !== playRequestId) return;
                    if (error && error.name === "AbortError") {
                        console.info("[TuneCluster player] play request aborted", {
                            track: track.track_name,
                            preview_url: previewUrl,
                        });
                        return;
                    }
                    if (audio.getAttribute("src") !== previewUrl) return;
                    if (tryFallbackPreview(track, requestId)) return;
                    console.error("[TuneCluster player] audio.play() failed", {
                        track: track.track_name,
                        preview_url: previewUrl,
                        error,
                    });
                    audio.pause();
                    showStatus("Preview audio tidak tersedia untuk lagu ini", track.spotify_url);
                    render();
                });
            }
        }

        function skip(offset) {
            if (!currentTrack || !tracks.length) return;
            const currentIndex = tracks.findIndex((track) => track.track_id === currentTrack.track_id);
            const nextIndex = currentIndex < 0
                ? (offset > 0 ? 0 : tracks.length - 1)
                : (currentIndex + offset + tracks.length) % tracks.length;
            playTrack(tracks[nextIndex]);
        }

        function handleCardClick(event, button) {
            const wrapper = button.closest('div[class*="st-key-play_recommended_track_"]');
            if (!wrapper) return;
            const prefix = "st-key-play_recommended_track_";
            const key = Array.from(wrapper.classList).find((name) => name.startsWith(prefix));
            const cardKey = key ? key.slice(prefix.length) : "";
            const track = tracks.find((item) => (
                item.track_id === cardKey
                || (Array.isArray(item.card_keys) && item.card_keys.includes(cardKey))
            ));
            if (!active || !track) return;
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            if (currentTrack && currentTrack.track_id === track.track_id && !audio.paused) {
                audio.pause();
            } else {
                playTrack(track);
            }
        }

        function handleDocumentClick(event) {
            const target = event.target instanceof host.Element ? event.target : null;
            if (!target) return;
            const cardButton = target.closest(
                'div[class*="st-key-play_recommended_track_"] button',
            );
            if (cardButton) {
                handleCardClick(event, cardButton);
                return;
            }
            const control = target.closest(
                '#tc-recommendation-player [data-player-action]',
            );
            if (!control) return;
            event.preventDefault();
            const action = control.getAttribute("data-player-action");
            if (action === "prev") skip(-1);
            else if (action === "next") skip(1);
            else if (action === "toggle") toggleCurrentTrack();
        }

        function handlePlayerInput(event) {
            const target = event.target;
            if (!(target instanceof host.HTMLInputElement)) return;
            if (target.matches("#tc-recommendation-player [data-player-seek]")) {
                if (Number.isFinite(audio.duration) && audio.duration > 0) {
                    audio.currentTime = (Number(target.value) / 100) * audio.duration;
                    refs.currentTime.textContent = formatTime(audio.currentTime);
                }
            } else if (target.matches("#tc-recommendation-player [data-player-volume]")) {
                setVolume(target.value);
            }
        }

        function handlePlayerChange(event) {
            const target = event.target;
            if (
                target instanceof host.HTMLInputElement
                && target.matches("#tc-recommendation-player [data-player-volume]")
            ) {
                setVolume(target.value);
            }
        }

        function toggleCurrentTrack() {
            if (!currentTrack) return;
            if (!primaryPreviewUrl(currentTrack)) {
                showStatus(
                    "Preview audio tidak tersedia untuk lagu ini",
                    currentTrack.spotify_url,
                );
                render();
            } else if (audio.paused) {
                playTrack(currentTrack, false);
            } else {
                audio.pause();
            }
        }

        function reconcilePage() {
            if (doc.querySelector(".tc-rec-scope-marker")) {
                active = true;
                return;
            }
            if (!active) return;
            active = false;
            audio.pause();
            currentTrack = null;
            showStatus("");
            render();
        }

        audio.addEventListener("play", () => {
            showStatus("");
            render();
        });
        audio.addEventListener("playing", render);
        audio.addEventListener("pause", render);
        audio.addEventListener("timeupdate", render);
        audio.addEventListener("loadedmetadata", render);
        audio.addEventListener("ended", render);
        audio.addEventListener("error", () => {
            if (!currentTrack) return;
            if (audio.error && audio.error.code === 1) {
                render();
                return;
            }
            const primaryUrl = primaryPreviewUrl(currentTrack);
            const fallbackUrl = currentTrack.fallback_preview_url || "";
            const failedUrl = audio.getAttribute("src");
            if (failedUrl !== primaryUrl && failedUrl !== fallbackUrl) return;
            const failureLog = failedUrl === primaryUrl && fallbackUrl
                ? console.warn
                : console.error;
            failureLog("[TuneCluster player] audio source failed", {
                track: currentTrack.track_name,
                preview_url: failedUrl,
                error: audio.error,
            });
            if (failedUrl === primaryUrl && tryFallbackPreview(currentTrack, playRequestId)) {
                return;
            }
            audio.pause();
            showStatus("Preview audio tidak tersedia untuk lagu ini", currentTrack.spotify_url);
            render();
        });
        doc.addEventListener("click", handleDocumentClick, true);
        doc.addEventListener("input", handlePlayerInput, true);
        doc.addEventListener("change", handlePlayerChange, true);
        restoreVolume();
        const pageObserver = new host.MutationObserver(() => {
            reconcilePage();
            syncCards();
        });
        pageObserver.observe(doc.body, {
            childList: true,
            subtree: true,
        });
        const routeCheck = host.setInterval(reconcilePage, 500);

        player = {
            version: playerVersion,
            dispose() {
                pageObserver.disconnect();
                host.clearInterval(routeCheck);
                doc.removeEventListener("click", handleDocumentClick, true);
                doc.removeEventListener("input", handlePlayerInput, true);
                doc.removeEventListener("change", handlePlayerChange, true);
                audio.pause();
                bar.remove();
                audio.remove();
            },
            update(nextTracks, nextDefaultTrackId) {
                const defaultChanged = nextDefaultTrackId !== defaultTrackId;
                const previousTrackId = currentTrack && currentTrack.track_id;
                tracks = nextTracks;
                active = true;
                defaultTrackId = nextDefaultTrackId || "";
                const latestTrack = previousTrackId
                    ? tracks.find((track) => track.track_id === previousTrackId)
                    : null;
                if (defaultChanged || !latestTrack) {
                    currentTrack = (
                        tracks.find((track) => track.track_id === defaultTrackId)
                        || tracks[0]
                        || null
                    );
                    if (currentTrack) {
                        showStatus(
                            primaryPreviewUrl(currentTrack)
                                ? ""
                                : "Preview audio tidak tersedia untuk lagu ini",
                            primaryPreviewUrl(currentTrack) ? "" : currentTrack.spotify_url,
                        );
                    } else {
                        showStatus("");
                    }
                } else {
                    currentTrack = latestTrack;
                }
                render();
            },
        };
        host.__tcRecommendationPlayer = player;
    }

    player.update(incomingTracks, incomingDefaultTrackId);
})();
</script>
"""


def serialize_player_tracks(tracks: Sequence[Mapping[str, object]]) -> str:
    """Serialize card data for the browser component without closing its script tag."""
    payload = []
    for track in tracks:
        preview_url = track.get("preview_url")
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
                "preview_url": str(preview_url).strip() if preview_url else None,
                "fallback_preview_url": (
                    str(track.get("fallback_preview_url")).strip()
                    if track.get("fallback_preview_url")
                    else None
                ),
                "spotify_url": str(track.get("spotify_url") or ""),
                "card_keys": [str(card_key) for card_key in card_keys if card_key],
            }
        )
    return _serialize_script_json(payload)


def _serialize_script_json(value: object) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_recommendation_player(
    tracks: Sequence[Mapping[str, object]],
    *,
    default_track_id: str | None = None,
) -> None:
    """Install persistent browser audio controls without triggering Streamlit reruns."""
    component_html = PLAYER_COMPONENT_HTML.replace(
        "__TRACKS_JSON__",
        serialize_player_tracks(tracks),
    ).replace(
        "__DEFAULT_TRACK_ID__",
        _serialize_script_json(default_track_id or ""),
    )
    st.components.v1.html(component_html, height=1, scrolling=False)
