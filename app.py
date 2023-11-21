from io import BytesIO
import requests
from flask import Flask, jsonify, send_file, request
from nba_api.stats.library.parameters import LocationNullable
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS
from matplotlib import pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc
from datetime import datetime
from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.static import teams
from nba_api.stats.endpoints import shotchartdetail, leaguegamefinder
import matplotlib.colors as mc
import colorsys
import cairosvg

# Use the 'Agg' backend for Matplotlib
import matplotlib

matplotlib.use("Agg")

app = Flask(__name__)
CORS(app)
# Add the following line to use the ProxyFix middleware
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Configuration Constants
SHOT_CHART_FILENAME_TEMPLATE = "{game_id_nullable}_{team_id}_{player_id}_shot_chart.png"

STATS_HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
    "Referer": "https://stats.nba.com/",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}


# Endpoint to get a team's light logo by abbreviation
# Sample URL: https://normal-dinosaur-yearly.ngrok-free.app/api/nba/images/logos/team/dark/LAL
@app.route("/api/nba/images/logos/team/<theme>/<abbreviation>", methods=["GET"])
def get_team_logo_light(theme, abbreviation):
    team = teams.find_team_by_abbreviation(abbreviation)

    if not team:
        return jsonify({"error": "Team not found"}), 404

    team_id = team["id"]
    letter = theme.upper()[0] if theme.lower() in ["light", "dark"] else "L"

    logo_url = f"https://cdn.nba.com/logos/nba/{team_id}/primary/{letter}/logo.svg"

    # Fetch the SVG logo from the URL
    try:
        response = requests.get(logo_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error fetching logo: {e}"}), 500

    # Convert the SVG data to PNG using cairosvg
    try:
        svg_data = response.text
        png_data = cairosvg.svg2png(bytestring=svg_data)
    except Exception as e:
        return jsonify({"error": f"Error converting SVG to PNG: {e}"}), 500

    # Use BytesIO to create a stream for the image data
    image_data = BytesIO(png_data)

    # Return the image data in the response
    return send_file(
        image_data,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"{abbreviation}_logo.png",
    )


# Endpoint to get a team by abbreviation
# Sample URL: https://normal-dinosaur-yearly.ngrok-free.app/api/nba/team/LAL
@app.route("/api/nba/team/<abbreviation>", methods=["GET"])
def get_team_by_abbreviation(abbreviation):
    team = teams.find_team_by_abbreviation(abbreviation)

    if team:
        return jsonify(team)
    else:
        return jsonify({"error": "Team not found"}), 404


# Endpoint to get all NBA games on a certain date
# Sample URL: https://normal-dinosaur-yearly.ngrok-free.app/api/nba/games/11-17-2023
@app.route("/api/nba/games/<date>", methods=["GET"])
def get_games_by_date(date):
    # Convert the date from the URL to the required format (e.g., "03-28-2021" to "03/28/2021")
    formatted_date = datetime.strptime(date, "%m-%d-%Y").strftime("%m/%d/%Y")

    # Query for games on the specified date
    game_finder = leaguegamefinder.LeagueGameFinder(
        date_from_nullable=formatted_date,
        date_to_nullable=formatted_date,
        location_nullable=LocationNullable.default,
        league_id_nullable="00",
        headers=STATS_HEADERS,
    )

    # Get the games DataFrame
    games_dataframe = game_finder.get_data_frames()[0]

    # Convert DataFrame to list of dictionaries with selected columns
    games_list = games_dataframe.to_dict(orient="records")

    # Combine and format the data based on home and away teams
    combined_data = combine_game_data(games_list)

    return jsonify({"games": combined_data})


# Function to combine and format game data based on home and away teams
def combine_game_data(data):
    # Create a dictionary to store combined data
    combined_data = {}

    # Iterate through the list of dictionaries
    for game in data:
        game_id = game["GAME_ID"]

        # Check if the game_id is already in combined_data
        if game_id not in combined_data:
            combined_data[game_id] = {}

        # Determine home and away teams
        home_team = game if "vs." in game["MATCHUP"] else None
        away_team = game if "@" in game["MATCHUP"] else None

        # Combine data for home and away teams
        if home_team:
            combined_data[game_id]["HOME"] = home_team
        elif away_team:
            combined_data[game_id]["AWAY"] = away_team

    # Create a list to store the final combined data
    final_combined_data = []

    # Iterate through the combined data
    for game_id, teams_data in combined_data.items():
        home_team = teams_data.get("HOME", {})
        away_team = teams_data.get("AWAY", {})

        combined_game_data = {
            "HOME_AST": home_team.get("AST", None),
            "AWAY_AST": away_team.get("AST", None),
            "HOME_BLK": home_team.get("BLK", None),
            "AWAY_BLK": away_team.get("BLK", None),
            "HOME_DREB": home_team.get("DREB", None),
            "AWAY_DREB": away_team.get("DREB", None),
            "HOME_FG3A": home_team.get("FG3A", None),
            "AWAY_FG3A": away_team.get("FG3A", None),
            "HOME_FG3M": home_team.get("FG3M", None),
            "AWAY_FG3M": away_team.get("FG3M", None),
            "HOME_FG3_PCT": home_team.get("FG3_PCT", None),
            "AWAY_FG3_PCT": away_team.get("FG3_PCT", None),
            "HOME_FGA": home_team.get("FGA", None),
            "AWAY_FGA": away_team.get("FGA", None),
            "HOME_FGM": home_team.get("FGM", None),
            "AWAY_FGM": away_team.get("FGM", None),
            "HOME_FG_PCT": home_team.get("FG_PCT", None),
            "AWAY_FG_PCT": away_team.get("FG_PCT", None),
            "HOME_FTA": home_team.get("FTA", None),
            "AWAY_FTA": away_team.get("FTA", None),
            "HOME_FTM": home_team.get("FTM", None),
            "AWAY_FTM": away_team.get("FTM", None),
            "HOME_FT_PCT": home_team.get("FT_PCT", None),
            "AWAY_FT_PCT": away_team.get("FT_PCT", None),
            "GAME_DATE": home_team.get("GAME_DATE", None),
            "GAME_ID": game_id,
            "MATCHUP": f"{away_team.get('TEAM_ABBREVIATION', '')} @ {home_team.get('TEAM_ABBREVIATION', '')}",
            "HOME_MIN": home_team.get("MIN", None),
            "AWAY_MIN": away_team.get("MIN", None),
            "HOME_OREB": home_team.get("OREB", None),
            "AWAY_OREB": away_team.get("OREB", None),
            "HOME_PF": home_team.get("PF", None),
            "AWAY_PF": away_team.get("PF", None),
            "HOME_PLUS_MINUS": home_team.get("PLUS_MINUS", None),
            "AWAY_PLUS_MINUS": away_team.get("PLUS_MINUS", None),
            "HOME_PTS": home_team.get("PTS", None),
            "AWAY_PTS": away_team.get("PTS", None),
            "HOME_REB": home_team.get("REB", None),
            "AWAY_REB": away_team.get("REB", None),
            "SEASON_ID": home_team.get("SEASON_ID", None),
            "HOME_STL": home_team.get("STL", None),
            "AWAY_STL": away_team.get("STL", None),
            "HOME_TEAM_ABBREVIATION": home_team.get("TEAM_ABBREVIATION", None),
            "AWAY_TEAM_ABBREVIATION": away_team.get("TEAM_ABBREVIATION", None),
            "HOME_TEAM_ID": home_team.get("TEAM_ID", None),
            "AWAY_TEAM_ID": away_team.get("TEAM_ID", None),
            "HOME_TEAM_NAME": home_team.get("TEAM_NAME", None),
            "AWAY_TEAM_NAME": away_team.get("TEAM_NAME", None),
            "HOME_TOV": home_team.get("TOV", None),
            "AWAY_TOV": away_team.get("TOV", None),
            "HOME_WL": home_team.get("WL", None),
            "AWAY_WL": away_team.get("WL", None),
        }

        # Append the combined game data to the final list
        final_combined_data.append(combined_game_data)

    return final_combined_data


# Endpoint for shot chart with parameters
# Sample URL: https://normal-dinosaur-yearly.ngrok-free.app/api/nba/shot_chart?player_id=203076&game_id_nullable=0042200233&team_id=1610612747&season_type_all_star=Playoffs
@app.route("/api/nba/shot_chart", methods=["GET"])
def get_shot_chart():
    player_id = request.args.get("player_id")
    game_id_nullable = request.args.get("game_id_nullable")
    team_id = request.args.get("team_id")
    season_type_all_star = request.args.get("season_type_all_star")

    if not all([player_id, game_id_nullable, team_id, season_type_all_star]):
        return "Missing required parameters", 400

    shot_chart_filename = generate_shot_chart(
        player_id, game_id_nullable, team_id, season_type_all_star
    )
    return send_file(shot_chart_filename, mimetype="image/png")


def generate_shot_chart(
    player_id,
    game_id_nullable,
    team_id,
    season_type_all_star,
    context_measure_simple="FGA",
):
    # Your existing shot chart generation code
    shot_detail = shotchartdetail.ShotChartDetail(
        player_id=player_id,
        game_id_nullable=game_id_nullable,
        team_id=team_id,
        context_measure_simple=context_measure_simple,
        season_type_all_star=season_type_all_star,
        headers=STATS_HEADERS,
    )
    shot_dataframe = shot_detail.get_data_frames()[0]

    made_shot = shot_dataframe[shot_dataframe.SHOT_MADE_FLAG == 1]
    missed_shot = shot_dataframe[shot_dataframe.SHOT_MADE_FLAG == 0]

    fig = plt.figure(figsize=(12, 10))
    fig.patch.set_facecolor("black")
    draw_court(outer_lines=True)
    plt.scatter(
        missed_shot.LOC_X,
        missed_shot.LOC_Y,
        s=200,
        facecolors=lighten_color("Red", 0.8),
        linewidths=3,
        marker="x",
        alpha=1,
    )
    plt.scatter(
        made_shot.LOC_X,
        made_shot.LOC_Y,
        s=200,
        facecolors="none",
        edgecolors=lighten_color("Green", 0.7),
        linewidths=2.5,
        marker="o",
        alpha=1,
    )
    plt.xlim(300, -300)
    plt.gca().invert_xaxis()
    plt.gca().invert_yaxis()
    plt.axis("off")

    # Save the shot chart as an image file
    shot_chart_filename = SHOT_CHART_FILENAME_TEMPLATE.format(
        player_id=player_id, game_id_nullable=game_id_nullable, team_id=team_id
    )
    plt.savefig(
        shot_chart_filename, bbox_inches="tight", pad_inches=0, transparent=True
    )
    return shot_chart_filename


def lighten_color(color_name, amount=0.5):
    try:
        color_rgb = mc.to_rgb(color_name)
    except ValueError:
        color_rgb = color_name

    color_hls = colorsys.rgb_to_hls(*color_rgb)
    lightened_color_rgb = colorsys.hls_to_rgb(
        color_hls[0], 1 - amount * (1 - color_hls[1]), color_hls[2]
    )
    return lightened_color_rgb


def draw_court(ax=None, color=lighten_color("White", 1), lw=3, outer_lines=False):
    # If an axes object isn't provided to plot onto, just get current one
    if ax is None:
        ax = plt.gca()

    # Create the various parts of an NBA basketball court

    # Create the basketball hoop
    # Diameter of a hoop is 18" so it has a radius of 9", which is a value
    # 7.5 in our coordinate system
    outer_lines = Rectangle(
        (-250, -47.5), 500, 470, linewidth=lw, color="black", fill=False
    )

    outer_lines2 = Rectangle(
        (-250, -47.5), 500, 470, linewidth=lw, color=color, fill=False
    )

    hoop = Circle((0, 0), radius=7.5, linewidth=lw, color=color, fill=False)

    # Create backboard
    backboard = Rectangle((-30, -7.5), 60, -1, linewidth=lw, color=color)

    # The paint
    # Create the outer box 0f the paint, width=16ft, height=19ft
    outer_box = Rectangle((-80, -47.5), 160, 190, linewidth=lw, color=color, fill=False)
    # Create the inner box of the paint, widt=12ft, height=19ft
    inner_box = Rectangle((-60, -47.5), 120, 190, linewidth=lw, color=color, fill=False)

    # Create free throw top arc
    top_free_throw = Arc(
        (0, 142.5),
        120,
        120,
        theta1=0,
        theta2=180,
        linewidth=lw,
        color=color,
        fill=False,
    )
    # Create free throw bottom arc
    bottom_free_throw = Arc(
        (0, 142.5),
        120,
        120,
        theta1=180,
        theta2=0,
        linewidth=lw,
        color=color,
        linestyle="--",
    )
    # Restricted Zone, it is an arc with 4ft radius from center of the hoop
    restricted = Arc((0, 0), 80, 80, theta1=0, theta2=180, linewidth=lw, color=color)

    # Three point line
    # Create the side 3pt lines, they are 14ft long before they begin to arc
    corner_three_a = Rectangle((-220, -47.5), 0, 140, linewidth=lw, color=color)
    corner_three_b = Rectangle((220, -47.5), 0, 140, linewidth=lw, color=color)
    # 3pt arc - center of arc will be the hoop, arc is 23'9" away from hoop
    # I just played around with the theta values until they lined up with the
    # threes
    three_arc = Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=lw, color=color)

    # Center Court
    center_outer_arc = Arc(
        (0, 422.5), 120, 120, theta1=180, theta2=0, linewidth=lw, color=color
    )
    center_inner_arc = Arc(
        (0, 422.5), 40, 40, theta1=180, theta2=0, linewidth=lw, color=color
    )

    # List of the court elements to be plotted onto the axes
    court_elements = [
        outer_lines,
        hoop,
        backboard,
        outer_box,
        inner_box,
        top_free_throw,
        bottom_free_throw,
        restricted,
        corner_three_a,
        corner_three_b,
        three_arc,
        center_outer_arc,
        center_inner_arc,
        outer_lines2,
    ]

    # Add the court elements onto the axes
    for element in court_elements:
        ax.add_patch(element)

    return ax


# Endpoint to get today's NBA scoreboard
# Sample URL: https://normal-dinosaur-yearly.ngrok-free.app/api/nba/todays_scoreboard
@app.route("/api/nba/todays_scoreboard", methods=["GET"])
def get_todays_scoreboard():
    games = scoreboard.ScoreBoard()
    return jsonify(games.get_dict())
