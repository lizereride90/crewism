# Crewism — Lookism Discord MMORPG

> A persistent Lookism-inspired game world inside Discord. Explore Seoul, fight, recruit,
> train, unlock masteries & bloodlines, run crews, conquer territories, hunt bosses.

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![discord.py](https://img.shields.io/badge/discord.py-2.x-blurple)
![tests](https://img.shields.io/badge/tests-19%20passing-green)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

**Fan project.** Original placeholder art only — no manga scans or scraped artwork bundled.
Cards are generated with OpenCV + Pillow (`utils/image_utils.py`) and can be swapped
for licensed art later. See [Disclaimer](#disclaimer).

## How it plays

```
/profile → /explore → Fight → Recruit → /team → /train → /shop → /conquer
```

- **Explore Seoul** — `/explore` patrols your region: wild fighters, named characters,
  cash, items, trainers, boss omens. Rarity is level-gated so early game stays fair.
- **Fight & recruit** — win street fights for a high recruit chance, then field up
  to 4 fighters with `/collection`, `/team`, `/dex`.
- **Train like Lookism** — `/trainers`, `/train`, `/claim_train`, plus `/mastery`
  (Strength/Speed/Endurance/Technique → Threshold) and `/bloodline`
  (Yamazaki, Gapryong, Mujin, Copy line, Stray) with staged awakenings.
- **Economy** — fictional **Won** only. `/daily`, patrols, fights, quests, territory
  tax. Spend on training, gear (`/shop /buy /sell /inventory /use`), scouting.
- **Gamble (fictional)** — `/coinflip`, `/dice`, `/higherlower` with cooldowns + limits.
- **PvP & bounty** — `/fight @user` friendly/ranked/wager (escrow pot), bounty climbs
  with wins. `/leaderboard`, `/bounty`.
- **Crews & turf** — `/crew create/join/info/leave/war`, `/territories`, `/conquer`.
  Crew-held turf pays hourly treasury.
- **Endgame** — `/bosses`, `/boss` (phased, cooldown-gated), `/quests`, `/events`,
  `/generations`, `/workers`. Gen 2 → Gen 1 → Gen 0 progression.

60-fighter starter roster (Lookism eras + original strays), 7 territories, 7 bosses,
trainers, quests, items — all data-driven JSON in `data/`.

## Quickstart (bot + dashboard together)

```bash
pip install -r requirements.txt
npm install            # dashboard UI deps (express)
cp .env.example .env   # put DISCORD_TOKEN inside, never commit it
npm start              # boots bot first, then dashboard → http://localhost:3000
# or: python main.py   # same thing, single entrypoint
```

- `python main.py` is the single entrypoint: DB auto-creates (`crewism.db`),
  seeds 60 fighters + items/trainers/territories/quests/bosses, starts the
  localhost bot API (`:3100`), then launches the dashboard UI (`:3000`).
  `npm start` just calls into it. Needs `node` installed for the UI;
  the bot runs fine without it.
- Never wipes player data on restart. Switch to Postgres later via `DATABASE_URL`.
- Slash commands auto-sync on startup. Set `COMMAND_GUILD_ID` in `.env` for instant
  dev sync, or leave empty for global sync.

## Dashboard

Local-only Seoul Control room: live overview, per-server feature toggles
(exploration / PvP / gambling — enforced by the bot instantly, no restart),
daily-reward tuning, spawn channel, players, economy ledger, bosses,
territory control, world-event switches. Binds `127.0.0.1` only —
never expose the port publicly.

## Requirements

Python 3.12+, `discord.py>=2.3`, `SQLAlchemy>=2.0`, `aiosqlite`,
`opencv-python-headless`, `Pillow`, `python-dotenv`, `pytest`.

## Commands

Every slash command has a `c!` prefix twin (needs Message Content Intent enabled
in the Developer Portal → Bot). Examples: `c!profile`, `c!explore`, `c!fight @user 100`.

| Area | Slash | Prefix |
|---|---|---|
| Profile | `/profile /balance /daily /stats` | `c!profile c!balance c!daily c!stats` |
| Explore | `/explore` (Fight / Recruit / Run buttons) | `c!explore` (same buttons) |
| Fighters | `/collection /team /dex` | `c!collection c!team c!dex` |
| Training | `/trainers /train /claim_train /mastery /bloodline` | same with `c!` |
| Shop | `/shop /buy /sell /inventory /use` | same with `c!` |
| Gamble | `/coinflip /dice /higherlower` | `c!coinflip c!dice c!higherlower` |
| PvP | `/fight` | `c!fight @user <wager>` |
| Boss | `/boss` (dropdown picker) | `c!boss` (lists options when empty) |
| Crew | `/crew create/join/info/leave/war` | `c!crew_create c!crew_join c!crew_info c!crew_leave c!crew_war` |
| Turf | `/territories /conquer` | `c!territories c!conquer` |
| Quests | `/quests /claim_quest /events /generations /workers` | same with `c!` |
| Ranks | `/leaderboard /bounty` | `c!leaderboard c!bounty` |
| Help | `/help` | `c!help` |

## Project structure

```
main.py            startup: dotenv → DB → seed → cogs → upkeep → bot API → dash UI → connect
config.py          env-based settings, no secrets hardcoded
dashboard/         Node UI (server.js + public/) — spawned by main.py, proxied to bot API
scripts/start.js   npm start → python main.py (single entrypoint)
cogs/              Discord layer only (calls services, no game math)
database/          models.py + repositories/ (SQL only here)
services/          game rules (combat, encounters, training, crews, quests…)
views/             buttons / pagination (no game logic)
utils/             embeds, formatting, cooldowns, image cards (cv2 + Pillow)
data/              characters, bloodlines, items, trainers, territories, quests, bosses…
assets/            placeholders + generated/ cache (gitignored)
tests/             pytest, no Discord connection needed
```

## Adding content (no combat rewrite)

- **Fighter** — append to `data/characters.json` (`source`: `canon` / `original` /
  `configurable`), restart. Lower rarities can still shine via style matchups.
- **Ability** — `data/techniques.json` with `{id, trigger, effects}`; the engine
  evaluates triggers generically (`services/combat_service.py`).
- **Item / trainer / territory / quest / boss / event** — matching JSON file, restart.
  Seeder only inserts missing rows.

## Design notes

- **Guild isolation** — every player-owned row is keyed by `(guild_id, user_id)`.
- **No cheat commands** — no admin/dev/owner commands, no Discord-permission → game-power
  path. Mods play as normal players. Dashboard-ready services (plain async methods)
  for a future web panel.
- **Anti-exploit** — ledgered money (`economy_ledger`), transactions, unique constraints,
  battle state machine, idempotent claims, wager escrow, DB cooldowns.
- **Canon vs original** — `source` field on content; unrevealed mechanics are
  `configurable` interpretations, documented in data files.

## Tests

```bash
pytest -q   # 19 tests: combat, economy, progression, bloodlines, territories, persistence
```

## Disclaimer

Unofficial fan game. Not affiliated with the Lookism rights holders. Do not upload
manga scans, official art, or pirated chapters. Bring your own licensed art via
`assets/` + `art_path`.

## License

MIT — see [LICENSE](LICENSE).
