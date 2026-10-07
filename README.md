# Qatchr documentation

Nederlandstalige Mintlify-documentatie voor Qatchr. De eerste versie beschrijft alle 104 HTTP-calls en 125 schema’s uit de Swagger-specificatie van de lokale API op 6 oktober 2026.

## Inhoud

- `index.mdx`, `quickstart.mdx` en `guides/`: introductie, authenticatie, fouten, paginering en recruitmentflows.
- `api-reference/`: een MDX-pagina voor iedere Swagger-operation, inclusief bronverwijzing en gedeclareerde rechten.
- `models/`: alle response-, invoer- en enum-schema’s uit Swagger.
- `openapi/swagger.json`: ongewijzigde export van `app.openapi()`.
- `openapi/route-metadata.json`: rechten, scopes en subscriptiondecorators uit de routebron.
- `openapi/qatchr.json`: documentatieversie met Nederlandse titels, toelichting en expliciete securitymetadata voor de routes die deze checks hebben.
- `endpoint-notes.json`: handgeschreven endpointtoelichting; wordt bewaard bij regenereren.
- `docs.json`, `logo/`, `favicon.ico`, `custom.css`: Mintlify-configuratie en bestaande Qatchr-huisstijl.

De voorbeelden gebruiken fictieve ID’s en `https://api.example.com`. Er is geen productie-API-origin ingevuld. De playground toont voorbeelden zonder requests naar een gegokte server te sturen. Voeg een geverifieerde `servers`-configuratie toe aan de generator wanneer de gewenste API-origin bekend is.

## Lokaal bekijken

Gebruik de geïnstalleerde Mintlify CLI:

```sh
mint dev
```

Als de CLI ontbreekt, volg [Mintlify’s installatiehandleiding](https://www.mintlify.com/docs/installation). Een lokale preview publiceert de site niet.

## API-documentatie bijwerken

Gebruik de bestaande Pythonomgeving van de backend; deze repo voegt geen backenddependencies toe. Vanuit `qatchr-api`:

```sh
poetry run python ../qatchr-docs/scripts/export_openapi.py --backend .
```

Vanuit `qatchr-docs`:

```sh
python3 scripts/generate_reference.py
```

De export importeert de FastAPI-app en roept `app.openapi()` aan. Hij start geen lifespan, achtergrondwerkers of server en voert geen endpointrequests uit. Dummy PostgreSQL-instellingen maken alleen de lazy engineconstructie bij import mogelijk; er wordt geen databaseverbinding geopend. De bestaande backendomgeving moet wel de dependencies uit haar pyproject bevatten.

De generator overschrijft gegenereerde endpointpagina’s, modelpagina’s, het overzicht en `docs.json`. Bewaar endpointteksten daarom in `endpoint-notes.json` en pas siteconfiguratie aan in de generator. Handleidingen blijven handmatig bewerkbaar. Bij verwijderde routes/schema’s blijven oude paginafiles liggen: verwijder deze na review; ze worden niet opnieuw in navigatie opgenomen. De exporter controleert dat iedere Swagger-call routemetadata heeft. Nieuwe routes met onbekende resources vragen ook om uitbreiding van `RESOURCES` in de generator.

Controleer bij een refresh ook de inhoudelijke handleidingen: OpenAPI specificeert niet alle runtimefouten, quota, validatorregels, redirects of dynamische responses. Broncode heeft voor die details voorrang. De beschikbare backend Pythonomgeving kan een andere FastAPI-versie hebben dan pyproject; exporteer voor releasegebruik vanuit de omgeving van die release.

## Validatie en publiceren

De initiële wijziging is statisch gecontroleerd op endpointdekking, schemareferenties, navigatie en lokale links. Er zijn geen API-calls, backendtests, builds, linting of typechecks uitgevoerd.

Op expliciet verzoek kun je de Mintlify-validatie uitvoeren:

```sh
mint validate
mint broken-links
```

Koppel de repository in het Mintlify-dashboard om te publiceren. Review de documentatiebranch voordat je deze naar de ingestelde deploymentbranch brengt. De koppeling of publicatie wordt door het maken van deze bestanden niet uitgevoerd.

## Mintlify-documentatie

- [OpenAPI-endpoints en schema’s in MDX](https://www.mintlify.com/docs/api-playground/openapi-setup)
- [Siteconfiguratie](https://www.mintlify.com/docs/organize/settings)
- [Lettertypen](https://www.mintlify.com/docs/customize/fonts)
