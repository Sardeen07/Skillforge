---
module: flask
capability: Flask application structure and security
technologies: flask
applies: flask, blueprint, jinja, werkzeug, app factory
checked_against: Flask 3.0 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## app-factory: Use an application factory and blueprints
tags: flask, application factory, blueprints, configuration, testing, circular imports
keywords: global app object, circular import
refs: https://flask.palletsprojects.com/en/3.0.x/patterns/appfactories/

Create the app in `create_app(config)` and register blueprints there. Create extensions unbound (`db = SQLAlchemy()`) and call `init_app(app)`. This avoids circular imports and lets tests build an app with test configuration.

## no-debug-in-production: Never run the debugger or dev server in production
tags: flask, debug mode, werkzeug debugger, production, gunicorn, security, remote code execution
keywords: app.run(debug=True) deployed
refs: https://flask.palletsprojects.com/en/3.0.x/debugging/

The Werkzeug debugger allows arbitrary code execution from the browser. Never enable `debug=True` outside local development, and serve production with a WSGI server (gunicorn, uWSGI, waitress) behind a reverse proxy, not `app.run()`.

## secret-key-and-sessions: Set a strong SECRET_KEY and secure cookie flags
tags: flask, secret key, session, cookies, csrf, security, configuration
keywords: SECRET_KEY = 'dev'
refs: https://flask.palletsprojects.com/en/3.0.x/config/#SECRET_KEY

Flask signs session cookies with `SECRET_KEY`; a weak or committed key lets attackers forge sessions. Load a long random key from the environment, set `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY` and `SESSION_COOKIE_SAMESITE='Lax'`, and add CSRF protection (Flask-WTF). The session is signed, not encrypted: store no secrets in it.

## jinja-autoescape: Rely on Jinja autoescaping; avoid |safe and Markup on user data
tags: flask, jinja, xss, autoescape, safe filter, markup, templates, security
keywords: render_template_string user input
refs: https://flask.palletsprojects.com/en/stable/web-security/

Templates ending in `.html` autoescape. `|safe`, `Markup()` and `render_template_string` with user input bypass that and enable XSS or server-side template injection. Escaping does not stop `javascript:` URLs in `href`; validate URL schemes.

## request-context-teardown: Release per-request resources in teardown handlers
tags: flask, request context, teardown, g, database connection, resource leak
keywords: connection leak, too many connections
refs: https://flask.palletsprojects.com/en/3.0.x/appcontext/

Store per-request resources on `g`, create them lazily, and release them in `@app.teardown_appcontext`, which runs even when the request raised. Do not keep request data in module globals; threaded servers share them across requests.

## sqlalchemy-session-scope: Tie each SQLAlchemy session to one Flask request and remove it at teardown
tags: flask, sqlalchemy, database session, flask-sqlalchemy, teardown, connection pool, transactions
keywords: QueuePool limit reached, connection timed out, sqlalchemy session reused by every request
refs: https://flask-sqlalchemy.readthedocs.io/en/stable/contexts/

Use Flask-SQLAlchemy (its session belongs to the app context and is removed at teardown) or, with plain SQLAlchemy, a `scoped_session` that you `remove()` in `teardown_appcontext`. A single global SQLAlchemy session reused by every request mixes transactions between users and exhausts the pool ("QueuePool limit of size 5 overflow 10 reached").

## flask-input-validation: Validate request data with a schema, not request.form lookups
tags: flask, validation, request json, marshmallow, pydantic, input, 400 bad request
keywords: KeyError on missing field, request.get_json, request.form
refs: https://flask.palletsprojects.com/en/3.0.x/api/#flask.Request.get_json

`request.json["x"]` raises a 500 on a missing field and accepts any type. Parse bodies with a schema library (marshmallow, pydantic, flask-smorest) and return 400 with field errors; `request.get_json(silent=True)` returns None for non-JSON instead of raising. Cap request size with `MAX_CONTENT_LENGTH`.

## flask-production-config: Load configuration from the environment per deployment
tags: flask, configuration, environment variables, config from prefixed env, secrets, deployment
keywords: config.py with production password, app.config.from_object
refs: https://flask.palletsprojects.com/en/3.0.x/config/#configuring-from-environment-variables

Keep defaults in code, override per environment with `app.config.from_prefixed_env()` (Flask 2.2+) or an instance-folder file that is not committed, and fail at startup when a required setting is missing. Never ship development defaults such as `SECRET_KEY = "dev"` to production.
