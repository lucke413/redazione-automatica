"""Estrattore HTML riutilizzato da AI Vision."""
from html.parser import HTMLParser

class SourceArticleParser(HTMLParser):
    """Estrae solo testo in article/main; esclude menu, script e widget."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            self.stack.append(tag)
        if tag in {'p', 'h1', 'h2', 'h3', 'li', 'br'}:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]
        if tag in {'p', 'h1', 'h2', 'h3', 'li'}:
            self.parts.append('\n')

    def handle_data(self, data):
        blocked = {'script', 'style', 'nav', 'aside', 'footer', 'form', 'noscript', 'button'}
        if ('article' in self.stack or 'main' in self.stack) and not blocked.intersection(self.stack):
            self.parts.append(data)

    def text(self):
        return '\n'.join(' '.join(line.split()) for line in ''.join(self.parts).splitlines() if line.strip())[:14000]
