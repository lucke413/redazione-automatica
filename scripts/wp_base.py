"""Client WordPress e conversione Markdown riutilizzati da AI Vision, senza entrypoint legacy."""
from __future__ import annotations
import html,re,unicodedata
from typing import Any
from urllib.parse import urlsplit
import requests
from requests.auth import HTTPBasicAuth
REQUEST_TIMEOUT=30
USER_AGENT="Editorial-Publisher/1.0"


class PublisherError(RuntimeError):
    """Errore che riguarda un singolo articolo o la configurazione."""

def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:180] or "ai-vision-articolo"

def normalize_tag(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text[:50]

def markdown_to_html(markdown_text: str) -> str:
    """Conversione minima sicura per i paragrafi prodotti dal generatore."""
    text = str(markdown_text or "").replace("\r\n", "\n").strip()
    if not text:
        return ""

    blocks = re.split(r"\n\s*\n", text)
    html_blocks: list[str] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        content = " ".join(lines)
        heading_match = re.match(r"^(#{2,3})\s+(.+)$", content)
        if heading_match:
            level = min(3, len(heading_match.group(1)))
            value = html.escape(heading_match.group(2).strip())
            html_blocks.append(f"<h{level}>{value}</h{level}>")
            continue
        if all(line.startswith(("- ", "* ")) for line in lines):
            entries = "".join(
                f"<li>{html.escape(line[2:].strip())}</li>" for line in lines
            )
            html_blocks.append(f"<ul>{entries}</ul>")
            continue
        escaped = html.escape(content)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
        html_blocks.append(f"<p>{escaped}</p>")
    return "\n".join(html_blocks)

class WordPressClient:

    def __init__(self, base_url: str, username: str, app_password: str, dry_run: bool):
        self.dry_run = dry_run
        self.base_url = base_url.rstrip('/')
        if self.base_url.endswith('/wp-json'):
            self.api_root = f'{self.base_url}/wp/v2'
        else:
            self.api_root = f'{self.base_url}/wp-json/wp/v2'
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        if username or app_password:
            self.session.auth = HTTPBasicAuth(username, app_password)
        self.category_cache: dict[str, dict] = {}
        self.tag_cache: dict[str, dict] = {}

    def _url(self, resource: str) -> str:
        return f"{self.api_root}/{resource.lstrip('/')}"

    def get_or_create_term(self, kind: str, name: str) -> dict:
        cache = self.category_cache if kind == 'categories' else self.tag_cache
        key = name.casefold()
        if key in cache:
            return cache[key]
        if self.dry_run:
            result = {'id': None, 'name': name, 'slug': slugify(name), 'dry_run': True}
            cache[key] = result
            return result
        response = self.session.get(self._url(kind), params={'search': name, 'per_page': 100}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        matches = response.json()
        for match in matches:
            if str(match.get('name', '')).casefold() == key:
                cache[key] = match
                return match
        response = self.session.post(self._url(kind), json={'name': name, 'slug': slugify(name)}, timeout=REQUEST_TIMEOUT)
        if response.status_code == 400:
            response = self.session.get(self._url(kind), params={'search': name, 'per_page': 100}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        cache[key] = result
        return result

    def existing_post(self, slug: str) -> dict | None:
        if self.dry_run:
            return None
        response = self.session.get(self._url('posts'), params={'slug': slug, 'per_page': 1, 'context': 'edit', 'status': 'publish,future,draft,pending,private'}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        values = response.json()
        return values[0] if values else None

    def upload_media(self, content: bytes, filename: str, mime_type: str, alt_text: str, caption: str) -> dict:
        if self.dry_run:
            return {'id': None, 'source_url': 'dry-run', 'alt_text': alt_text}
        response = self.session.post(self._url('media'), data=content, headers={'Content-Disposition': f'attachment; filename="{filename}"', 'Content-Type': mime_type}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        media = response.json()
        media_id = media.get('id')
        if media_id:
            update = self.session.post(self._url(f'media/{media_id}'), json={'alt_text': alt_text, 'caption': caption}, timeout=REQUEST_TIMEOUT)
            update.raise_for_status()
            media = update.json()
        return media

    def related_link(self, draft: dict, category_id: int | None) -> str:
        """Un solo collegamento pubblicato, pertinente e sullo stesso sito."""
        if self.dry_run or not category_id:
            return ''
        try:
            response = self.session.get(self._url('posts'), params={'status': 'publish', 'categories': category_id, 'per_page': 30, '_fields': 'id,title,link,slug'}, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            stop = {'della', 'delle', 'dello', 'degli', 'come', 'sono', 'anche', 'questo', 'quello', 'ecco', 'nuovo', 'nuova', 'disponibile'}

            def words(value):
                return {w for w in re.findall('[a-zà-ù0-9]+', value.lower()) if (len(w) >= 4 or (w.isdigit() and len(w) >= 2)) and w not in stop}
            target = words(str(draft.get('title') or '') + ' ' + str(draft.get('focus_keyphrase') or ''))
            candidates = []
            own_slug = slugify(str(draft.get('slug') or draft.get('title') or ''))
            for post in response.json():
                link = str(post.get('link') or '')
                label = html.unescape(re.sub('<[^>]+>', '', str(post.get('title', {}).get('rendered') or '')))
                if urlsplit(link).netloc != urlsplit(self.base_url).netloc or urlsplit(link).scheme != 'https' or post.get('slug') == own_slug:
                    continue
                overlap = target & words(label)
                if len(overlap) >= 2:
                    candidates.append((len(overlap), label, link))
            if not candidates:
                return ''
            _, label, link = max(candidates, key=lambda row: row[0])
            return '<p>Leggi anche: <a href="' + html.escape(link, quote=True) + '">' + html.escape(label) + '</a>.</p>'
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            print('AVVISO SEO: ricerca link interni non disponibile; pubblicazione invariata.')
            return ''

    def create_post(self, payload: dict) -> dict:
        if self.dry_run:
            return {'id': None, 'link': 'dry-run', 'status': 'planned', 'payload': payload}
        response = self.session.post(self._url('posts'), json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
