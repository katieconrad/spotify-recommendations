import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, render_template, request, flash
from flask_bootstrap import Bootstrap
import os
from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, NumberRange
from dotenv import load_dotenv
from requests.exceptions import Timeout

#  Load information from .env file
load_dotenv()

# Set spotipy authorization information
client = os.environ.get("CLIENT_ID")
secret = os.environ.get("CLIENT_SECRET")
redirect_uri = os.environ.get("SPOTIPY_REDIRECT_URI")
SCOPE = "playlist-modify-private user-library-read user-top-read"

# Create and authorize spotipy client
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client, client_secret=secret, redirect_uri=redirect_uri,
                                               scope=SCOPE, show_dialog=True))


def get_top_artists():
    """Send API request for user's top artists"""
    top_artists = sp.current_user_top_artists(limit=5, time_range="medium_term")
    artist_ids = [artist["id"] for artist in top_artists["items"]]
    return artist_ids


def get_recommendations(seeds, num, attribute):
    """Send API request for recommendations based on top artists and an attribute"""
    recommendations = sp.recommendations(seed_artists=seeds, limit=num, **{attribute: 1.0})
    recommendation_uris = [track["uri"] for track in recommendations["tracks"]]
    return recommendation_uris


def convert_attribute(desc):
    """Converts descriptor into kwarg attribute for spotify recommendation API call"""
    if desc == "Acoustic":
        qual = "target_acousticness"
    elif desc == "Danceable":
        qual = "target_danceability"
    elif desc == "Instrumental":
        qual = "target_instrumentalness"
    elif desc == "Live":
        qual = "target_liveness"
    elif desc == "Speechy":
        qual = "target_speechiness"
    else:
        qual = "target_loudness"
    return qual


def create_playlist(title, adj, tracks):
    """Creates playlist and adds recommended tracks"""
    user_id = sp.current_user()["id"]
    playlist = sp.user_playlist_create(user=user_id, name=title, public=False, collaborative=False,
                                       description=f"Recommended {adj} Tracks based on Top Artists")
    playlist_id = playlist["id"]
    sp.playlist_add_items(playlist_id=playlist_id, items=tracks, position=None)


# Configure Flask
app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(32)
bootstrap = Bootstrap(app)

# Create form
quality_list = ["Acoustic", "Danceable", "Instrumental", "Live", "Speechy", "Loud"]


class PlaylistForm(FlaskForm):
    num_songs = IntegerField("How many recommended songs do you want? (max. 100)",
                             validators=[DataRequired(), NumberRange(min=1, max=100)])
    playlist_type = SelectField("What type of  playlist would you like?", choices=quality_list,
                                validators=[DataRequired()])
    submit = SubmitField("Get playlist")


# Server Routing
@app.route("/", methods=["GET", "POST"])
def home():
    form = PlaylistForm()
    if request.method == "POST":
        pl_length = request.form["num_songs"]
        quality = request.form["playlist_type"]
        attribute = convert_attribute(quality)
        pl_title = f"Top Artist {quality} Recommendations"
        try:
            artists = get_top_artists()
        except spotipy.oauth2.SpotifyOauthError:
            flash("Could not authorize user")
        except spotipy.SpotifyException:
            flash("Could not retrieve top artists")
        except Timeout:
            flash("API request timed out. Please try again.")
        else:
            try:
                tracks = get_recommendations(artists, pl_length, attribute)
            except spotipy.SpotifyException:
                flash("Could not retrieve recommended tracks")
            except Timeout:
                flash("API request timed out. Please try again.")
            else:
                try:
                    create_playlist(pl_title, quality, tracks)
                except spotipy.SpotifyException:
                    flash("Could not create playlist")
                except Timeout:
                    flash("API request timed out. Please try again.")
                else:
                    flash(f"Your playlist has been created with title {pl_title}")
    return render_template("index.html", form=form)


# Run app
if __name__ == "__main__":
    app.run(debug=True)
