"""Export Swagger and decorator metadata without starting the API lifespan."""
import argparse
import ast
import inspect
import json
import os
from pathlib import Path
import sys
import textwrap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', type=Path, required=True)
    args = parser.parse_args()
    backend = args.backend.resolve()
    if not (backend / 'main.py').is_file():
        parser.error('--backend must contain the Qatchr API main.py')
    # Engine construction at import requires a valid URL. These dummy values never
    # connect to a database. Do not use real database credentials for this export.
    for name, value in {
        'POSTGRES_USER': 'docs', 'POSTGRES_PASSWORD': 'docs',
        'POSTGRES_HOST': '127.0.0.1', 'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'docs', 'ORGANIZATION_DELETE_ENABLED': 'false',
    }.items():
        os.environ[name] = value
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(backend))
    from fastapi.routing import APIRoute
    from main import app

    root = Path(__file__).resolve().parents[1]
    target = root / 'openapi'
    target.mkdir(exist_ok=True)
    spec = app.openapi()
    metadata = {}
    # Scan decorator declarations directly: recent FastAPI releases keep included
    # routers nested in app.routes, while Swagger already contains flattened paths.
    sources = [(backend / 'main.py', ''),
               (backend / 'app/services/organization_lifecycle.py', '/api/v1/organization-lifecycle')]
    index = ast.parse((backend / 'app/api/v1/index.py').read_text())
    imports = {alias.asname or alias.name: node.module for node in index.body
               if isinstance(node, ast.ImportFrom) for alias in node.names}
    for node in ast.walk(index):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != 'include_router':
            continue
        if not node.args or not isinstance(node.args[0], ast.Name):
            continue
        module = imports.get(node.args[0].id)
        if not module:
            continue
        prefix = next(ast.literal_eval(k.value) for k in node.keywords if k.arg == 'prefix')
        sources.append((backend / (module.replace('.', '/') + '.py'), '/api/v1' + prefix))
    sources += [(backend / 'app/api/v1/candidate_imports.py', '/api/v1/candidates'),
                (backend / 'app/api/v1/relation_imports.py', '/api/v1/relations')]
    for source_path, prefix in sources:
        tree = ast.parse(source_path.read_text())
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            route_decorators = [d for d in function.decorator_list if isinstance(d, ast.Call)
                                and isinstance(d.func, ast.Attribute)
                                and d.func.attr in {'get', 'post', 'patch', 'put', 'delete', 'options', 'head'}]
            for route in route_decorators:
                path = prefix + ast.literal_eval(route.args[0])
                method = route.func.attr.upper()
                if method.lower() not in spec['paths'].get(path, {}):
                    continue
                permissions = []
                membership = subscription = False
                for decorator in function.decorator_list:
                    name = ast.unparse(decorator.func if isinstance(decorator, ast.Call) else decorator).split('.')[-1]
                    if name == 'check_permission':
                        membership = True
                        if isinstance(decorator, ast.Call) and len(decorator.args) > 1:
                            permissions.append({'scope': ast.unparse(decorator.args[0]).split('.')[-1].lower(),
                                                'permission': ast.literal_eval(decorator.args[1])})
                    if name == 'require_subscription':
                        subscription = True
                metadata[f'{method} {path}'] = {
                    'source': source_path.relative_to(backend).as_posix(), 'function': function.name,
                    'permissions': permissions, 'membership': membership, 'subscription': subscription,
                }
    operation_count = sum(1 for entry in spec['paths'].values() for method in entry
                          if method in {'get', 'post', 'patch', 'put', 'delete', 'options', 'head'})
    if len(metadata) != operation_count:
        raise RuntimeError(f'Route metadata coverage mismatch: {len(metadata)} / {operation_count}')
    (target / 'swagger.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n')
    (target / 'route-metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    print(f'Exported {len(metadata)} operations and {len(spec["components"]["schemas"])} schemas. No lifespan or requests executed.')


if __name__ == '__main__':
    main()
