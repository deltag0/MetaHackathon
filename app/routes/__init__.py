def register_routes(app):
    from app.routes.redirect import redirect_bp
    from app.routes.links import links_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(redirect_bp)
    app.register_blueprint(links_bp)
    app.register_blueprint(auth_bp)
