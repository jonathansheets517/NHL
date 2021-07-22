from source.db_models.bets_models import *
from source.db_models.nhl_models import *
from datetime import date, datetime, timedelta
from sqlalchemy import func, and_, or_, not_, asc, desc
import pandas as pd
import sqlalchemy
from sqlalchemy import select
from sqlalchemy.orm import aliased
from tqdm import tqdm
import csv

def generate_data_for(player_id, nhl_session, games_to_go_back, season):
    PlayerTeamStats = aliased(TeamStats)
    OppTeamStats = aliased(TeamStats)
    query = (
        select(SkaterStats, Game, PlayerTeamStats, OppTeamStats)
        .where(SkaterStats.playerId == player_id)
        .join(Game, SkaterStats.gamePk == Game.gamePk)
        .join(PlayerTeamStats, and_(SkaterStats.gamePk == PlayerTeamStats.gamePk, PlayerTeamStats.teamId == SkaterStats.team))
        .join(OppTeamStats, and_(SkaterStats.gamePk == OppTeamStats.gamePk, OppTeamStats.teamId != SkaterStats.team))
        .order_by(asc(Game.gameDate))
    )
    playerStatsForGames = pd.read_sql(query, nhl_session.bind)

    playerStatsForGames.columns = [u + "_SkaterStats" for u in SkaterStats.__table__.columns.keys()]\
                                + [u + "_Game" for u in Game.__table__.columns.keys()] \
                                + [u + "_PlayerTeamStats" for u in PlayerTeamStats.__table__.columns.keys()] \
                                + [u + "_OppTeamStats" for u in OppTeamStats.__table__.columns.keys()]

    df_total = pd.DataFrame()
    if season == "all":
        for i in tqdm(range(2008, 2025)):
            season = str(i) + str(i+1)
            new_df = add_games_back(playerStatsForGames[playerStatsForGames.season_Game == str(season)], games_to_go_back)
            df_total = pd.concat([df_total, new_df])

    else:
        df_total = add_games_back(playerStatsForGames[playerStatsForGames.season_Game == str(season)], games_to_go_back)

    df_total["O_1.5"] = (df_total["shots_SkaterStats"] > 1.5).astype(int)
    df_total["O_2.5"] = (df_total["shots_SkaterStats"] > 2.5).astype(int)
    df_total["O_3.5"] = (df_total["shots_SkaterStats"] > 3.5).astype(int)
    df_total["O_4.5"] = (df_total["shots_SkaterStats"] > 4.5).astype(int)
    df_total["U_1.5"] = (df_total["shots_SkaterStats"] < 1.5).astype(int)
    df_total["U_2.5"] = (df_total["shots_SkaterStats"] < 2.5).astype(int)
    df_total["U_3.5"] = (df_total["shots_SkaterStats"] < 3.5).astype(int)
    df_total["U_4.5"] = (df_total["shots_SkaterStats"] < 4.5).astype(int)

    # Get date of last game in df_total
    last_game_date = df_total.iloc[-1]["gameDate_Game"]

    return (df_total, last_game_date)


def add_games_back(df, games_to_go_back):
    df_total = pd.DataFrame()
    for i in range(1, games_to_go_back + 1):
        dfc = df.copy()
        dfc = dfc.shift(periods=i)
        dfc.columns = [u + "_{}_games_back".format(i) for u in dfc.head()]
        df_total = pd.concat([df_total, dfc], axis=1)
    df = pd.concat([df, df_total], axis=1)
    return df
