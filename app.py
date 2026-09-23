import random
import uuid
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Dragon Dice Wheel")

app.mount("/static", StaticFiles(directory="static"), name="static")

DICE = {
    "Loreley": [0, 0, 0, 5, 5, 5, 5, 10, 10, 10],
    "Klabautermann": [2, 2, 3, 3, 4, 4, 5, 5],
    "Heinzelmaennchen": [1, 1, 3, 3, 6, 6],
    "Wolpertinger": [0, 0, 0, 6, 6, 6, 6, 6, 6, 12, 12, 12],
    "Tatzelwurm": [2, 2, 4, 4, 6, 6, 8, 8],
    "Brockenhexe": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "Doener-Golem": [3, 3, 3, 3, 3, 3, 8, 8, 8, 8, 8, 8],
    "Spaeti-Kobold": [1, 2, 3, 4, 5, 6],
}

BLURBS = {
    "Loreley": {"die": "d10", "faces": [0, 5, 10], "ability": "Once per round, declare All-In. 10 wins round immediately, 0 loses round immediately."},
    "Klabautermann": {"die": "d8", "faces": [2, 3, 4, 5], "ability": "Optional reroll after rolling if losing."},
    "Heinzelmaennchen": {"die": "d6", "faces": [1, 3, 6], "ability": "Gains token on loss. Spend 2 tokens for +1 to roll before rolling."},
    "Wolpertinger": {"die": "d12", "faces": [0, 6, 12], "ability": "Chaos die triggers automatically (4-5: +1, 6: reroll trope die)."},
    "Tatzelwurm": {"die": "d8", "faces": [2, 4, 6, 8], "ability": "Wins ties when rolling an 8."},
    "Brockenhexe": {"die": "d10", "faces": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "ability": "Force opponent to reroll when losing."},
    "Spaeti-Kobold": {"die": "d6", "faces": [1, 2, 3, 4, 5, 6], "ability": "Gains token on loss. Spend 2 tokens to force opponent reroll."},
    "Doener-Golem": {"die": "d12", "faces": [3, 8], "ability": "Roll 8 gives opponent -1 token. Roll 3 gives self +1 token."}
}

GAMES: Dict[str, Dict[str, Any]] = {}

class StartGameRequest(BaseModel):
    player_trope: str
    cpu_trope: Optional[str] = None

class PlayRoundRequest(BaseModel):
    game_id: str
    player_all_in: bool = False
    spend_heinzel: bool = False
    use_klabauter: bool = False
    use_brocken: bool = False
    use_spaeti: bool = False

def roll(trope: str) -> int:
    return random.choice(DICE[trope])

def roll_d6() -> int:
    return random.randint(1, 6)

@app.get("/")
def get_index():
    return FileResponse("static/index.html")

@app.get("/api/tropes")
def get_tropes():
    return {"tropes": list(DICE.keys()), "details": BLURBS, "dice_values": DICE}

@app.post("/api/start")
def start_game(req: StartGameRequest):
    if req.player_trope not in DICE:
        raise HTTPException(status_code=400, detail="Invalid player trope")
    
    cpu_choices = [t for t in DICE.keys() if t != req.player_trope]
    cpu_trope = req.cpu_trope if (req.cpu_trope and req.cpu_trope in cpu_choices) else random.choice(cpu_choices)

    game_id = str(uuid.uuid4())
    GAMES[game_id] = {
        "player_trope": req.player_trope,
        "cpu_trope": cpu_trope,
        "player_wins": 0,
        "cpu_wins": 0,
        "player_tokens": 0,
        "cpu_tokens": 0,
        "round": 0,
        "is_over": False
    }

    return {"game_id": game_id, "state": GAMES[game_id]}

@app.post("/api/play")
def play_round(req: PlayRoundRequest):
    game = GAMES.get(req.game_id)
    if not game or game["is_over"]:
        raise HTTPException(status_code=400, detail="Invalid session or game over")

    events = []
    
    cpu_all_in = (game["cpu_trope"] == "Loreley" and game["cpu_wins"] < game["player_wins"])
    if cpu_all_in:
        events.append("CPU Loreley declares All-In!")

    player_bonus, cpu_bonus = 0, 0

    # STRICT TOKEN CHECK & DEDUCTION: Heinzelmännchen
    if game["player_trope"] == "Heinzelmaennchen" and req.spend_heinzel:
        if game["player_tokens"] >= 2:
            game["player_tokens"] -= 2
            player_bonus = 1
            events.append("Spent 2 tokens (+1 modifier applied).")
        else:
            events.append("Not enough tokens to use Heinzelmännchen boost!")

    if game["cpu_trope"] == "Heinzelmaennchen" and game["cpu_tokens"] >= 2 and game["cpu_wins"] < game["player_wins"]:
        game["cpu_tokens"] -= 2
        cpu_bonus = 1
        events.append("CPU Heinzelmännchen spent 2 tokens for +1 bonus.")

    p_roll = roll(game["player_trope"])
    c_roll = roll(game["cpu_trope"])

    p_auto, c_auto = None, None
    if game["player_trope"] == "Loreley" and req.player_all_in:
        if p_roll == 10: p_auto = "win"; events.append("Loreley sings! Auto-win.")
        elif p_roll == 0: p_auto = "lose"; events.append("Loreley chokes! Auto-lose.")

    if game["cpu_trope"] == "Loreley" and cpu_all_in:
        if c_roll == 10: c_auto = "win"; events.append("CPU Loreley sings! Auto-win.")
        elif c_roll == 0: c_auto = "lose"; events.append("CPU Loreley chokes! Auto-lose.")

    if game["player_trope"] == "Wolpertinger":
        fate = roll_d6()
        events.append(f"Your Chaos die: {fate}.")
        if fate in (4, 5): p_roll += 1
        elif fate == 6: p_roll = roll("Wolpertinger"); events.append(f"Chaos reroll: {p_roll}.")

    if game["cpu_trope"] == "Wolpertinger":
        fate = roll_d6()
        events.append(f"CPU Chaos die: {fate}.")
        if fate in (4, 5): c_roll += 1
        elif fate == 6: c_roll = roll("Wolpertinger"); events.append(f"CPU Chaos reroll: {c_roll}.")

    p_roll += player_bonus
    c_roll += cpu_bonus

    if game["player_trope"] == "Klabautermann" and req.use_klabauter:
        p_roll = roll("Klabautermann")
        events.append(f"You rerolled Klabautermann to {p_roll}.")

    if game["cpu_trope"] == "Klabautermann" and c_roll < p_roll:
        c_roll = roll("Klabautermann")
        events.append(f"CPU Klabautermann rerolled to {c_roll}.")

    if game["player_trope"] == "Brockenhexe" and req.use_brocken:
        c_roll = roll(game["cpu_trope"])
        events.append(f"You hexed CPU to reroll into {c_roll}.")

    if game["cpu_trope"] == "Brockenhexe" and p_roll > c_roll:
        p_roll = roll(game["player_trope"])
        events.append(f"CPU hexed you to reroll into {p_roll}.")

    # STRICT TOKEN CHECK & DEDUCTION: Späti-Kobold
    if game["player_trope"] == "Spaeti-Kobold" and req.use_spaeti:
        if game["player_tokens"] >= 2:
            game["player_tokens"] -= 2
            c_roll = roll(game["cpu_trope"])
            events.append(f"Spent 2 tokens! Forced CPU reroll into {c_roll}.")
        else:
            events.append("Not enough tokens to force CPU reroll!")

    if game["cpu_trope"] == "Spaeti-Kobold" and game["cpu_tokens"] >= 2 and p_roll > c_roll:
        game["cpu_tokens"] -= 2
        p_roll = roll(game["player_trope"])
        events.append(f"CPU spent 2 tokens and forced you to reroll into {p_roll}.")

    # Döner-Golem Token Modifiers
    if game["player_trope"] == "Doener-Golem":
        if p_roll == 8:
            game["cpu_tokens"] = max(0, game["cpu_tokens"] - 1)
            events.append("Döner effect: CPU lost 1 token.")
        elif p_roll == 3:
            game["player_tokens"] += 1
            events.append("Döner effect: You gained 1 token.")

    if game["cpu_trope"] == "Doener-Golem":
        if c_roll == 8:
            game["player_tokens"] = max(0, game["player_tokens"] - 1)
            events.append("CPU Döner effect: You lost 1 token.")
        elif c_roll == 3:
            game["cpu_tokens"] += 1
            events.append("CPU Döner effect: CPU gained 1 token.")

    # WIN EVALUATION
    winner = None
    win_reason = ""

    if p_auto == "win" or c_auto == "lose":
        winner = "player"
        win_reason = "Loreley All-In Trigger (Auto-Win)"
    elif c_auto == "win" or p_auto == "lose":
        winner = "cpu"
        win_reason = "CPU Loreley All-In Trigger (Auto-Win)"
    elif p_roll == c_roll and game["player_trope"] == "Tatzelwurm" and p_roll == 8:
        winner = "player"
        win_reason = "Tatzelwurm Ambush (Wins ties on 8)"
    elif p_roll == c_roll and game["cpu_trope"] == "Tatzelwurm" and c_roll == 8:
        winner = "cpu"
        win_reason = "CPU Tatzelwurm Ambush (Wins ties on 8)"
    elif p_roll > c_roll:
        winner = "player"
        win_reason = f"Higher Roll ({p_roll} > {c_roll})"
    elif c_roll > p_roll:
        winner = "cpu"
        win_reason = f"Higher Roll ({c_roll} > {p_roll})"
    else:
        winner = "draw"
        win_reason = f"Equal Roll ({p_roll} == {c_roll})"

    # ON-LOSS TOKEN GENERATION
    if winner == "player":
        game["player_wins"] += 1
        if game["cpu_trope"] in ("Heinzelmaennchen", "Spaeti-Kobold"): 
            game["cpu_tokens"] += 1
            events.append("CPU gained +1 token for losing round.")
    elif winner == "cpu":
        game["cpu_wins"] += 1
        if game["player_trope"] in ("Heinzelmaennchen", "Spaeti-Kobold"): 
            game["player_tokens"] += 1
            events.append("You gained +1 token for losing round.")

    game["round"] += 1
    if game["round"] >= 5:
        game["is_over"] = True

    return {
        "events": events,
        "rolls": {"player": p_roll, "cpu": c_roll},
        "winner": winner,
        "win_reason": win_reason,
        "state": game
    }