import reflex as rx

config = rx.Config(
    app_name="production",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    db_url="sqlite:///Production.db",
)
