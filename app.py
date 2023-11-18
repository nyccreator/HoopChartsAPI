from flask import Flask, jsonify, send_file, request
from matplotlib import pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc
from datetime import datetime
from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.static import teams
from nba_api.stats.endpoints import shotchartdetail, leaguegamefinder
import matplotlib.colors as mc
import colorsys

app = Flask(__name__)

# Configuration Constants
SHOT_CHART_FILENAME_TEMPLATE = "{game_id_nullable}_{team_id}_{player_id}_shot_chart.png"


# Endpoint to get a team by abbreviation
# Sample URL: http://127.0.0.1:5000/api/nba/team/LAL
@app.route("/api/nba/team/<abbreviation>", methods=["GET"])
def get_team_by_abbreviation(abbreviation):
    team = teams.find_team_by_abbreviation(abbreviation)

    if team:
        return jsonify(team)
    else:
        return jsonify({"error": "Team not found"}), 404


# Endpoint to get all NBA games on a certain date
# Sample URL: http://127.0.0.1:5000/api/nba/games/11-17-2023
@app.route("/api/nba/games/<date>", methods=["GET"])
def get_games_by_date(date):
    # Convert the date from the URL to the required format (e.g., "03-28-2021" to "03/28/2021")
    formatted_date = datetime.strptime(date, "%m-%d-%Y").strftime("%m/%d/%Y")

    # Query for games on the specified date
    game_finder = leaguegamefinder.LeagueGameFinder(
        date_from_nullable=formatted_date, date_to_nullable=formatted_date
    )

    # Get the games DataFrame
    games_dataframe = game_finder.get_data_frames()[0]

    # Convert DataFrame to list of dictionaries with selected columns
    games_list = games_dataframe.to_dict(orient="records")

    return jsonify({"games": games_list})


# Endpoint for shot chart with parameters
# Sample URL: http://127.0.0.1:5000/api/nba/shot_chart?player_id=203076&game_id_nullable=0042200233&team_id=1610612747&season_type_all_star=Playoffs
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
# Sample URL: http://127.0.0.1:5000/api/nba/todays_scoreboard
@app.route("/api/nba/todays_scoreboard", methods=["GET"])
def get_todays_scoreboard():
    games = scoreboard.ScoreBoard()
    return jsonify(games.get_dict())


if __name__ == "__main__":
    app.run(debug=True)
