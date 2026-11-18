"""Wires everything together. No routes, SQL or rules live here."""
import os

from flask import Flask

from db import init_db
from errors import register_error_handlers
from routers import books, loans, members, reports

app = Flask(__name__)
app.register_blueprint(books.bp)
app.register_blueprint(members.bp)
app.register_blueprint(loans.bp)
app.register_blueprint(reports.bp)
register_error_handlers(app)

if not os.path.exists("library.db"):
    init_db()
