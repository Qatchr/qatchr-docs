"""Generate the API reference from Swagger; keep editorial notes in endpoint-notes.json."""
import copy
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
METHODS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}
RESOURCES = {
    'health-check': ('Health', 'healthcheck', 'healthchecks'),
    'ai-credits': ('AI-credits', 'creditsaldo', 'creditsaldi'),
    'tasks': ('Taken', 'taak', 'taken'),
    'applications': ('Sollicitaties', 'sollicitatie', 'sollicitaties'),
    'candidates': ('Kandidaten', 'kandidaat', 'kandidaten'),
    'documents': ('Documenten', 'document', 'documenten'),
    'workflows': ('Processen', 'proces', 'processen'),
    'statuses': ('Statussen', 'status', 'statussen'),
    'vacancies': ('Vacatures', 'vacature', 'vacatures'),
    'locations': ('Locaties', 'locatie', 'locaties'),
    'relations': ('Relaties', 'relatie', 'relaties'),
    'contact-persons': ('Contactpersonen', 'contactpersoon', 'contactpersonen'),
    'contracts': ('Contracten', 'contract', 'contracten'),
    'talent-pools': ('Talentpools', 'talentpool', 'talentpools'),
    'call-lists': ('Bellijsten', 'bellijst', 'bellijsten'),
    'integrations': ('Integraties', 'integratie', 'integraties'),
    'resource-usage': ('Verbruik', 'resourceverbruik', 'resourceverbruik'),
    'recruitment-news': ('Recruitmentnieuws', 'nieuwsbericht', 'nieuwsberichten'),
    'organization-profile': ('Organisatieprofiel', 'organisatieprofiel', 'organisatieprofielen'),
    'organization-lifecycle': ('Organisatielevenscyclus (intern)', 'lifecycleactie', 'lifecycleacties'),
}


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def write_page(path, title, description, content='', **frontmatter):
    file = ROOT / (path + '.mdx')
    file.parent.mkdir(parents=True, exist_ok=True)
    values = {'title': title, 'description': description, **frontmatter}
    header = '\n'.join(f'{k}: {json.dumps(v, ensure_ascii=False)}' for k, v in values.items())
    file.write_text('---\n' + header + '\n---\n\n' + content.strip() + '\n')


def title_for(method, path, resource):
    _, single, plural = RESOURCES[resource]
    if '/imports' in path:
        return ('Importvoorbeeld bekijken' if path.endswith('/preview') else
                'Laatste import ophalen' if path.endswith('/latest') else
                'Import starten' if method == 'post' else 'Importstatus ophalen')
    if '/tags/' in path:
        return 'Beschikbare tags ophalen' if method == 'get' else 'Tags vervangen'
    if path.endswith('/url'):
        return 'Download-URL ophalen'
    if '/from-cv/' in path: return 'Kandidaat uit een cv aanmaken'
    if '/from-linkedin-url/' in path: return 'Kandidaat uit LinkedIn aanmaken'
    if '/from-prompt/' in path: return 'Vacature met AI genereren'
    if '/from-url/' in path: return 'Vacature vanuit een URL importeren'
    if '/existing-application/' in path: return 'Bestaande kandidaat laten solliciteren'
    if '/candidate-application/' in path: return 'Sollicitatie voor een kandidaat aanmaken'
    if '/handle/' in path: return 'Taak afhandelen'
    if '/attention/' in path: return 'Persoonlijke taakzichtbaarheid wijzigen'
    if '/deadline/' in path: return 'Taakdeadline wijzigen'
    if '/get-options/' in path: return 'Integratieopties ophalen'
    if '/oauth/start' in path: return 'OAuth-verbinding starten'
    if '/oauth/callback' in path: return 'OAuth-callback verwerken'
    if '/links' in path:
        return {'get': 'Integratiekoppelingen ophalen', 'post': 'Integratiekoppeling aanmaken',
                'patch': 'Integratiekoppeling wijzigen', 'delete': 'Integratiekoppeling verwijderen'}[method]
    if path.endswith('/organization'): return 'Eigen organisatierelatie ophalen'
    if resource == 'health-check': return 'API-beschikbaarheid controleren'
    if resource == 'ai-credits': return 'AI-creditsaldo ophalen'
    if resource == 'resource-usage': return 'Organisatieverbruik ophalen'
    if resource == 'organization-lifecycle':
        return 'Lifecycleactie uitvoeren' if method == 'post' else 'Lifecyclegereedheid controleren'
    if method == 'get':
        return (single if '{' in path else plural).capitalize() + ' ophalen'
    return single.capitalize() + {'post': ' aanmaken', 'patch': ' wijzigen', 'put': ' vervangen', 'delete': ' verwijderen'}[method]


def main():
    raw = json.loads((ROOT / 'openapi/swagger.json').read_text())
    metadata = json.loads((ROOT / 'openapi/route-metadata.json').read_text())
    notes = json.loads((ROOT / 'endpoint-notes.json').read_text())
    spec = copy.deepcopy(raw)
    spec['info'] = {**spec['info'], 'title': 'Qatchr API', 'description': 'API voor recruitment, kandidaten, vacatures, sollicitaties en processen. Zie de handleidingen voor organisatiecontext en toegangscontrole.'}
    # Keep servers unset until an actual deployment URL is supplied; no guessed
    # production host, and the reference stays in Mintlify simple playground mode.
    spec['components']['securitySchemes'] = {
        'bearerAuth': {'type': 'http', 'scheme': 'bearer', 'description': 'Access token van de Qatchr-identiteitsomgeving; verkrijgen valt buiten deze API.'},
        'lifecycleKey': {'type': 'apiKey', 'in': 'header', 'name': 'X-Lifecycle-Key', 'description': 'Interne lifecycle-servicecredential.'},
    }
    groups = {}
    index_rows = []
    for path, entry in spec['paths'].items():
        resource = path.split('/')[3] if path.startswith('/api/v1/') else path.strip('/')
        label = RESOURCES[resource][0]
        groups.setdefault(resource, {'group': label, 'pages': []})
        for method, operation in entry.items():
            if method not in METHODS:
                continue
            key = f'{method.upper()} {path}'
            meta = metadata[key]
            note = notes.get(key, {})
            title = note.get('title', title_for(method, path, resource))
            description = note.get('description', f'{title} via de Qatchr API. De specificatie toont de exacte parameters, invoer en uitvoer.')
            operation['summary'] = title
            operation['description'] = note.get('body', description)
            operation['tags'] = [label]
            permissions = meta['permissions']
            access = []
            if resource == 'organization-lifecycle':
                operation['security'] = [{'lifecycleKey': []}]
                access.append('Dit is een interne servicecall. Gebruik `X-Lifecycle-Key`; een normale bearer-token vervangt deze sleutel niet. Zie [organisatielifecycle](/guides/organization-lifecycle).')
            elif meta['membership']:
                operation['security'] = [{'bearerAuth': []}]
                params = operation.setdefault('parameters', [])
                if not any(p.get('in') == 'header' and p['name'].lower() == 'x-organization-id' for p in params):
                    params.append({'name': 'X-Organization-Id', 'in': 'header', 'required': True, 'schema': {'type': 'string'}, 'description': 'Organisatiecontext voor de permission-check.'})
                access.append('Stuur `Authorization: Bearer <access-token>` en `X-Organization-Id` mee.')
                for permission in permissions:
                    access.append(f"Vereist recht: `{permission['permission']}` binnen scope `{permission['scope']}`.")
                if not permissions:
                    access.append('De call controleert geauthenticeerd lidmaatschap; er is geen afzonderlijk permission-label op de route.')
            elif resource not in {'health-check', 'recruitment-news'}:
                access.append('De route heeft geen expliciete `check_permission`-decorator. Gebruik de organisatie- en gebruikersheaders die bij de parameters staan. Aanvullende gatewaycontroles hangen af van de deployment; zie [authenticatie](/guides/authentication).')
            else:
                access.append('De route definieert geen permission-check of organisatieheader.')
            if meta['subscription']:
                access.append('Een `require_subscription`-controle vereist algemene Qatchr-toegang voor deze mutatie.')
            if resource == 'call-lists':
                access.append('Alle bellijstcalls vereisen daarnaast recruitmenttype `others` of `selfAndOthers`. Zie [bellijsten](/guides/call-lists).')
            route_page = 'api-reference/' + resource + '/' + slug(method + '-' + (path.removeprefix('/api/v1/').removeprefix(resource)))
            if path == '/health-check': route_page = 'api-reference/health-check/get'
            content = note.get('body', description) + '\n\n## Toegang\n\n' + '\n\n'.join(access)
            if 'parameters' in operation and any(p.get('name') == 'offset' for p in operation['parameters']):
                content += '\n\n## Lijsten ophalen\n\nGebruik de ondersteunde filters voor deze call. [Paginering en sortering](/guides/pagination) beschrijft hoe je meerdere pagina’s ophaalt.'
            if note.get('guide'):
                content += f"\n\n## Meer uitleg\n\nZie [{note['guide_title']}]({note['guide']}) voor de volledige werkwijze."
            content += f"\n\n## Bron\n\nSwagger-operation: `{operation['operationId']}`. Route: `{meta['source']}` (`{meta['function']}`)."
            write_page(route_page, title, description, content, openapi=f'/openapi/qatchr.json {key}')
            groups[resource]['pages'].append(route_page)
            index_rows.append(f'| `{method.upper()}` | [`{path}`](/{route_page}) | {label} |')
    (ROOT / 'openapi/qatchr.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n')
    model_pages = []
    for name in sorted(raw['components']['schemas']):
        page = 'models/' + slug(name)
        write_page(page, name, f'Exact Swagger-schema voor {name}.', 'Velden, typen en verplichte eigenschappen komen rechtstreeks uit de Swagger-specificatie.', **{'openapi-schema': f'/openapi/qatchr.json {name}'})
        model_pages.append(page)
    write_page('api-reference/overview', 'Alle API-calls', 'Vind iedere HTTP-call uit de Qatchr Swagger-specificatie.',
               f'Deze referentie bevat **{len(index_rows)} API-calls** en **{len(model_pages)} schema’s** uit de lokale Qatchr API. De paden behouden hun exacte trailing slash.\n\nDe API-prefix is `/api/v1`; `/health-check` staat op de root. Swagger UI staat standaard op `/docs`, de OpenAPI-specificatie op `/openapi.json`. WebSockets staan niet in de HTTP-specificatie.\n\n| Methode | Pad | Onderdeel |\n| --- | --- | --- |\n' + '\n'.join(index_rows))
    config = {
        '$schema': 'https://mintlify.com/docs.json', 'theme': 'mint', 'name': 'Qatchr',
        'description': 'Documentatie voor de Qatchr recruitment API.',
        'colors': {'primary': '#4D35FF', 'light': '#AB76FA', 'dark': '#5C62F5'},
        'logo': {'light': '/logo/light.svg', 'dark': '/logo/dark.svg'},
        'favicon': '/favicon.ico', 'fonts': {'family': 'Manrope'},
        'navigation': {'tabs': [
            {'tab': 'Handleidingen', 'groups': [
                {'group': 'Aan de slag', 'pages': ['index', 'quickstart', 'guides/authentication', 'guides/errors', 'guides/pagination']},
                {'group': 'Recruitment', 'pages': ['guides/applications', 'guides/workflows', 'guides/tasks', 'guides/imports', 'guides/tags', 'guides/documents', 'guides/call-lists']},
                {'group': 'Platform', 'pages': ['guides/integrations', 'guides/ai-credits', 'guides/websockets', 'guides/organization-lifecycle']},
            ]},
            {'tab': 'API-referentie', 'groups': [{'group': 'Overzicht', 'pages': ['api-reference/overview']}, *groups.values()]},
            {'tab': 'Datamodellen', 'groups': [{'group': 'Swagger-schema’s', 'pages': model_pages}]},
        ]},
        'navbar': {'links': [{'label': 'Qatchr', 'href': 'https://qatchr.nl'}]},
        'contextual': {'options': ['copy', 'view', 'chatgpt', 'claude', 'mcp']},
    }
    (ROOT / 'docs.json').write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    print(f'Generated {len(index_rows)} endpoint pages and {len(model_pages)} schema pages.')


if __name__ == '__main__':
    main()
