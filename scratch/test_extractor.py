import bs4

with open('scratch/wiki.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = bs4.BeautifulSoup(html, 'html.parser')

TAGS_RUIDO = [
    'script', 'style', 'nav', 'header', 'footer',
    'aside', 'advertisement', 'cookie', 'banner',
    'iframe', 'form', 'button', 'input', 'select',
    '[document]', 'noscript', 'meta', 'link'
]
for tag in soup(TAGS_RUIDO):
    tag.decompose()

CLASSES_RUIDO = [
    'nav', 'menu', 'sidebar', 'footer', 'header',
    'cookie', 'banner', 'ad', 'advertisement',
    'related', 'share', 'social', 'comment',
    'vector-header', 'vector-menu', 'mw-jump-link'
]

for classe in CLASSES_RUIDO:
    for elem in soup.find_all(class_=lambda c: c and classe in (' '.join(c) if isinstance(c, list) else c).lower()):
        elem.decompose()

SELETORES_CONTEUDO = [
    'article', 'main', '[role="main"]',
    '.mw-parser-output', '#bodyContent',
    '.content', '.post-content', '.entry-content',
    '.article-body', '.post-body',
    '#content', '#main', '#article'
]

texto = ''
for seletor in SELETORES_CONTEUDO:
    elemento = soup.select_one(seletor)
    if elemento:
        texto = elemento.get_text(separator='\n\n', strip=True)
        if len(texto) > 500:
            print(f'Encontrado com seletor {seletor}, tamanho: {len(texto)}')
            break

if len(texto) < 500:
    print('Usando fallback p/h1/h2...')
    elementos = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li', 'blockquote'])
    partes = [e.get_text(strip=True) for e in elementos if len(e.get_text(strip=True)) > 30]
    texto = '\n\n'.join(partes)
    print(f'Tamanho fallback 1: {len(texto)}')

if len(texto) < 200:
    texto = soup.get_text(separator='\n', strip=True)
    print(f'Tamanho fallback 2: {len(texto)}')

print(f'Tamanho final: {len(texto)}')
