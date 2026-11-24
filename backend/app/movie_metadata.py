"""Title lookup through OMDb. The official rating is informational only."""
import requests
from .common import env

def search_movie(title: str) -> dict:
    key = env("OMDB_API_KEY")
    if not key:
        raise RuntimeError("OMDB_API_KEY is not set.")
    r = requests.get("https://www.omdbapi.com/", params={"apikey": key, "t": title}, timeout=15).json()
    if r.get("Response") != "True":
        raise LookupError(r.get("Error", "Movie not found"))
    return {"title": r["Title"], "year": r.get("Year"), "poster": r.get("Poster"),
            "plot": r.get("Plot"), "official_rating": r.get("Rated"), "runtime": r.get("Runtime")}
