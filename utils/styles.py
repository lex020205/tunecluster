"""Shared matte-dark styling for every TuneCluster Streamlit page."""

from __future__ import annotations

import streamlit as st

GLOBAL_UI_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    color-scheme: dark;
    --tc-bg: #121212;
    --tc-sidebar: #181818;
    --tc-surface: #1E1E1E;
    --tc-hover: #282828;
    --tc-accent: #1DB954;
    --tc-text: #FFFFFF;
    --tc-muted: #A7A7A7;
    --tc-divider: rgba(255, 255, 255, 0.07);
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
    background: var(--tc-bg) !important;
    color: var(--tc-text) !important;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--tc-text) !important;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.025em;
}

[data-testid="stMainBlockContainer"] {
    max-width: 1440px;
    padding-top: 1.25rem;
    padding-bottom: 3rem;
}

[data-testid="stAppHeader"] {
    background: transparent !important;
}

[data-testid="stDecoration"],
[data-testid="stDeployButton"],
footer,
#MainMenu {
    display: none !important;
}

section[data-testid="stSidebar"] {
    background: var(--tc-sidebar) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}

[data-testid="stSidebarNav"] {
    display: none !important;
}

[data-testid="stSidebarContent"] {
    padding-top: 1.2rem;
}

[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stExpander"] {
    background: var(--tc-surface) !important;
    border: 1px solid var(--tc-divider) !important;
    border-radius: 12px !important;
    box-shadow: none !important;
}

[data-testid="stVerticalBlockBorderWrapper"]:hover {
    background: var(--tc-hover) !important;
}

[data-testid="stMetric"] {
    background: var(--tc-surface);
    border: 1px solid var(--tc-divider);
    border-radius: 10px;
    padding: 0.75rem 0.9rem;
    box-shadow: none;
}

button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
    background: #FFFFFF !important;
    border: 1px solid #FFFFFF !important;
    border-radius: 8px !important;
    color: #121212 !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}

button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background: #E8E8E8 !important;
    border-color: #E8E8E8 !important;
}

button[kind="secondary"],
button[data-testid="stBaseButton-secondary"] {
    background: #242424 !important;
    border: 1px solid var(--tc-divider) !important;
    border-radius: 8px !important;
    color: var(--tc-text) !important;
    box-shadow: none !important;
}

button[kind="secondary"]:hover,
button[data-testid="stBaseButton-secondary"]:hover {
    background: var(--tc-hover) !important;
    border-color: rgba(255, 255, 255, 0.16) !important;
}

button:focus-visible,
a:focus-visible,
input:focus-visible {
    outline: 2px solid var(--tc-accent) !important;
    outline-offset: 2px !important;
}

[data-testid="stAlert"] {
    background: var(--tc-surface) !important;
    border: 1px solid var(--tc-divider) !important;
    border-radius: 9px !important;
    color: var(--tc-text) !important;
}

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="base-input"],
textarea {
    background: #242424 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px !important;
    color: var(--tc-text) !important;
}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="base-input"]:focus-within,
textarea:focus {
    border-color: var(--tc-accent) !important;
}

div[data-testid="stPageLink"] a {
    border-radius: 8px;
    color: var(--tc-muted);
    padding: 0.55rem 0.65rem;
}

div[data-testid="stPageLink"] a:hover {
    background: var(--tc-hover);
    color: var(--tc-text);
}

div[data-testid="stPageLink"] a[aria-current="page"],
div[data-testid="stPageLink"][aria-current="page"] a {
    background: rgba(255, 255, 255, 0.08);
    color: var(--tc-text);
}

.tc-brand {
    color: var(--tc-text);
    font-size: 1.2rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    padding: 0.2rem 0 0.9rem;
}

.tc-brand-accent {
    color: var(--tc-accent);
}

.tc-account {
    background: #202020;
    border: 1px solid var(--tc-divider);
    border-radius: 10px;
    margin-top: 1rem;
    padding: 0.7rem 0.8rem;
}

.tc-account-secondary,
.tc-muted {
    color: var(--tc-muted) !important;
}

.hero-card,
.cluster-box,
.crisp-card,
.insight-box,
.history-card {
    background: var(--tc-surface);
    border: 1px solid var(--tc-divider);
    border-radius: 12px;
    box-shadow: none;
}

.hero-card {
    padding: 1.5rem 1.7rem;
    margin-bottom: 1rem;
}

.hero-title {
    color: var(--tc-text);
    font-size: 2.2rem;
    font-weight: 700;
    letter-spacing: -0.04em;
    margin: 0;
}

.hero-accent,
.hero-tagline {
    color: var(--tc-accent);
}

.hero-tagline {
    font-size: 1rem;
    margin: 0.4rem 0 0.8rem;
}

.hero-desc {
    color: var(--tc-muted);
    font-size: 0.95rem;
    line-height: 1.6;
}

.history-card,
.cluster-box,
.insight-box,
.crisp-card {
    padding: 1rem;
}

.genre-badge {
    background: #262626;
    border: 1px solid var(--tc-divider);
    border-radius: 999px;
    color: #D8D8D8;
    display: inline-block;
    font-size: 0.82rem;
    padding: 0.3rem 0.7rem;
}

.tc-track-card {
    background: var(--tc-surface);
    border: 1px solid var(--tc-divider);
    border-radius: 12px;
    padding: 0.85rem;
}

.tc-track-card:hover {
    background: var(--tc-hover);
}

.tc-track-title {
    color: var(--tc-text);
    font-size: 1rem;
    font-weight: 600;
    line-height: 1.35;
}

.tc-track-header {
    align-items: center;
    display: flex;
    gap: 0.75rem;
    margin-bottom: 0.45rem;
}

.tc-track-cover {
    align-items: center;
    background: #303030;
    border: 1px solid var(--tc-divider);
    border-radius: 7px;
    color: #E8E8E8;
    display: flex;
    flex: 0 0 42px;
    font-size: 0.8rem;
    font-weight: 600;
    height: 42px;
    justify-content: center;
}

.tc-genre-badge {
    background: #262626;
    border: 1px solid var(--tc-divider);
    border-radius: 999px;
    color: #D8D8D8;
    display: inline-block;
    font-size: 0.76rem;
    margin: 0.15rem 0.2rem 0.15rem 0;
    padding: 0.15rem 0.55rem;
}

.tc-track-score {
    color: var(--tc-muted);
    font-size: 0.8rem;
    margin-top: 0.45rem;
}

.tc-score-track {
    background: #333333;
    border-radius: 999px;
    height: 4px;
    margin-top: 0.3rem;
    overflow: hidden;
}

.tc-score-fill {
    background: var(--tc-accent);
    border-radius: 999px;
    height: 100%;
}

.tc-fallback {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-top: 0.55rem;
}

.tc-link-button {
    background: #242424;
    border: 1px solid var(--tc-divider);
    border-radius: 7px;
    color: var(--tc-text) !important;
    font-size: 0.8rem;
    padding: 0.35rem 0.65rem;
    text-decoration: none !important;
}

.tc-link-button-primary {
    background: #FFFFFF;
    border-color: #FFFFFF;
    color: #121212 !important;
    font-weight: 600;
}

.tc-link-button:hover {
    background: var(--tc-hover);
}

.tc-link-button-primary:hover {
    background: #E8E8E8;
}

.tc-track-meta {
    color: var(--tc-muted);
    font-size: 0.84rem;
    line-height: 1.45;
}

.tc-top-pick {
    height: 100%;
}

.tunecluster-footer {
    border-top: 1px solid var(--tc-divider);
    color: var(--tc-muted);
    font-size: 0.8rem;
    margin-top: 2rem;
    padding: 1rem 0 0.4rem;
    text-align: center;
}

::-webkit-scrollbar {
    width: 7px;
    height: 7px;
}

::-webkit-scrollbar-track {
    background: var(--tc-bg);
}

::-webkit-scrollbar-thumb {
    background: #444444;
    border-radius: 999px;
}

@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] {
        padding-left: 0.9rem;
        padding-right: 0.9rem;
    }

    .hero-card {
        padding: 1.1rem;
    }

    .hero-title {
        font-size: 1.8rem;
    }
}

@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
        transition-duration: 0.01ms !important;
    }
}
</style>
"""


def inject_global_styles() -> None:
    """Apply the shared matte-dark stylesheet to the active Streamlit page."""
    st.markdown(GLOBAL_UI_CSS, unsafe_allow_html=True)
