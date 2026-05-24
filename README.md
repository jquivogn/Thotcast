# Thotcast

Agent autonome de veille informationnelle et de podcasting automatisé, hébergé entièrement en local.

Thotcast collecte des flux RSS, filtre les articles selon vos centres d'intérêt, génère un script de dialogue via un LLM local (Ollama / Llama 3.1), synthétise chaque réplique en audio (Kokoro TTS, accéléré GPU), puis assemble le tout en un fichier MP3 prêt à écouter.

---

## Fonctionnalités

- **Collecte RSS automatique** — lecture de n'importe quel flux RSS/Atom, nettoyage du HTML parasite
- **Filtrage par mots-clés** — seuls les articles pertinents selon votre configuration sont retenus
- **Déduplication** — les URL déjà traitées sont ignorées lors des cycles suivants
- **Script LLM structuré** — prompt dynamique injecté dans Llama 3.1 (via Ollama) respectant à la lettre l'ordre des intervenants et les sujets demandés
- **TTS multi-voix** — une voix Kokoro distincte par personnage, synthèse GPU via ONNX Runtime
- **Post-production automatique** — pauses calibrées entre répliques et entre locuteurs, export MP3 128 kbps
- **API REST asynchrone** — FastAPI + SQLAlchemy async ; la génération tourne en arrière-plan sans bloquer l'API
- **Automatisation planifiée** — script cron prêt à l'emploi pour un épisode quotidien

---

## Prérequis système

| Composant | Version minimale |
|---|---|
| Ubuntu Server | 22.04 LTS |
| Python | 3.11+ |
| Pilote NVIDIA | 595.71.05+ |
| CUDA Toolkit | 13.2+ |
| Ollama | dernière version stable |

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/jquivogn/Thotcast.git
cd Thotcast
```

### 2. Lancer le script de setup

```bash
bash setup.sh
```

Ce script effectue automatiquement :
- création de l'environnement virtuel Python (`.venv/`)
- installation des dépendances Python (`requirements.txt`)
- installation du backend TTS `kokoro-onnx` + `onnxruntime-gpu`
- téléchargement des fichiers modèle Kokoro (`kokoro-v0_19.onnx`, `voices.json`)
- pull du modèle `llama3.1:8b` via Ollama

### 3. Démarrer l'API

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

L'interface Swagger est disponible sur `http://localhost:8000/docs`.

---

## Utilisation rapide

### Générer un épisode maintenant

```bash
curl -X POST http://localhost:8000/generate
```

Réponse :
```json
{ "message": "Génération lancée en arrière-plan", "episode_id": 1 }
```

### Suivre l'état de l'épisode

```bash
curl http://localhost:8000/episodes/1
```

Statuts possibles : `pending` → `fetching` → `generating_script` → `generating_audio` → `done`

### Lister tous les épisodes

```bash
curl http://localhost:8000/episodes
```

Le champ `audio_url` contient le lien direct vers le MP3 dès que la génération est terminée.

---

## Configuration

### Lire la configuration active

```bash
curl http://localhost:8000/config
```

### Modifier la configuration

```bash
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "rss_feeds": [
      "https://www.lemonde.fr/rss/une.xml",
      "https://www.lefigaro.fr/rss/figaro_actualites.xml",
      "https://feeds.bbci.co.uk/news/technology/rss.xml"
    ],
    "keywords": ["intelligence artificielle", "énergie", "espace"],
    "podcast_structure": [
      {
        "character": "Présentatrice",
        "voice": "af_heart",
        "subject": "Introduction et présentation des sujets du jour"
      },
      {
        "character": "Intervenant 1",
        "voice": "am_adam",
        "subject": "Revue des actualités technologiques"
      },
      {
        "character": "Intervenant 2",
        "voice": "am_michael",
        "subject": "Analyse approfondie du sujet principal"
      },
      {
        "character": "Présentatrice",
        "voice": "af_heart",
        "subject": "Conclusion et résumé"
      }
    ]
  }'
```

### Champs de configuration

| Champ | Type | Description |
|---|---|---|
| `rss_feeds` | `string[]` | URLs des flux RSS à surveiller |
| `keywords` | `string[]` | Mots-clés de filtrage des articles (liste vide = tout accepter) |
| `podcast_structure` | `PodcastStep[]` | Séquence ordonnée des intervenants |

#### PodcastStep

| Champ | Description |
|---|---|
| `character` | Nom du personnage (ex : `"Présentatrice"`) |
| `voice` | Identifiant de voix Kokoro (voir tableau ci-dessous) |
| `subject` | Consigne thématique injectée dans le prompt LLM |

### Voix Kokoro disponibles

| ID | Langue | Profil |
|---|---|---|
| `af_heart` | Anglais US | Féminine, chaleureuse |
| `af_bella` | Anglais US | Féminine, posée |
| `af_sky` | Anglais US | Féminine, dynamique |
| `am_adam` | Anglais US | Masculine, grave |
| `am_michael` | Anglais US | Masculine, neutre |
| `bf_emma` | Anglais UK | Féminine britannique |
| `bm_george` | Anglais UK | Masculine britannique |
| `ff_siwis` | Français | Féminine française |

> Pour un podcast en français, utilisez `ff_siwis` pour les voix féminines. Les voix masculines françaises ne sont pas disponibles dans la version actuelle de Kokoro ; les voix américaines restent fonctionnelles avec un accent marqué.

---

## Automatisation quotidienne (cron)

Pour générer un épisode automatiquement chaque matin à 07h00 :

```bash
crontab -e
```

Ajouter la ligne :

```
0 7 * * * /chemin/absolu/vers/Thotcast/cron_trigger.sh >> /chemin/absolu/vers/Thotcast/cron.log 2>&1
```

Le script `cron_trigger.sh` appelle simplement `POST /generate` sur l'API locale. L'URL de l'API peut être surchargée via la variable d'environnement `THOTCAST_API_URL`.

---

## Architecture

```
Thotcast/
├── app/
│   ├── main.py                 ← Application FastAPI, lifespan, mount /audio
│   ├── database.py             ← Moteur SQLAlchemy async (aiosqlite)
│   ├── models.py               ← Tables : Article, Episode, Config
│   ├── schemas.py              ← Schémas Pydantic (validation I/O)
│   ├── routers/
│   │   ├── config.py           ← GET /config  •  POST /config
│   │   ├── episodes.py         ← GET /episodes  •  GET /episodes/{id}
│   │   └── generate.py         ← POST /generate
│   ├── services/
│   │   ├── cleaner.py          ← Nettoyage HTML (BeautifulSoup)
│   │   ├── rss.py              ← Ingestion RSS + filtre + dédup
│   │   ├── llm.py              ← Génération de script via Ollama
│   │   ├── tts.py              ← Synthèse vocale Kokoro (GPU)
│   │   └── audio_assembler.py  ← Assemblage MP3 (pydub)
│   └── tasks/
│       └── pipeline.py         ← Orchestration complète du pipeline
├── audio/                      ← Fichiers MP3 générés (servis en statique)
├── requirements.txt
├── requirements-tts.txt        ← Dépendances TTS optionnelles
├── setup.sh                    ← Script d'installation complet
└── cron_trigger.sh             ← Déclencheur cron
```

### Pipeline de génération

```
POST /generate
     │
     ├─[1]─ fetch_and_store_articles()
     │        └─ feedparser → nettoyage HTML → filtre mots-clés → dédup DB → INSERT
     │
     ├─[2]─ generate_script()
     │        └─ articles + config → prompt LLM → Ollama → parseur [Personnage]: → lignes
     │
     ├─[3]─ synthesize_line()  × N répliques
     │        └─ kokoro-onnx (GPU) → fichiers WAV temporaires
     │
     ├─[4]─ assemble_audio()
     │        └─ pydub : concat + pauses → export MP3
     │
     └─[5]─ Episode mis à jour en DB (status=done, audio_path)
```

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./thotcast.db` | URL de connexion à la base de données |
| `AUDIO_DIR` | `audio` | Dossier de stockage des fichiers MP3 |
| `BASE_URL` | `http://localhost:8000` | URL publique de l'API (utilisée pour construire `audio_url`) |
| `KOKORO_MODEL_DIR` | `.` | Dossier contenant `kokoro-v0_19.onnx` et `voices.json` |
| `THOTCAST_API_URL` | `http://localhost:8000` | URL cible pour le script cron |

---

## Dépendances principales

| Paquet | Rôle |
|---|---|
| `fastapi` | Framework API REST |
| `uvicorn` | Serveur ASGI |
| `sqlalchemy` + `aiosqlite` | ORM async + base SQLite |
| `pydantic` | Validation des données |
| `feedparser` | Lecture des flux RSS/Atom |
| `beautifulsoup4` | Nettoyage du HTML |
| `ollama` | Client Python pour l'API Ollama locale |
| `kokoro-onnx` | Moteur TTS léger (ONNX Runtime GPU) |
| `pydub` | Manipulation et export audio |
| `soundfile` + `numpy` | Écriture des fichiers WAV intermédiaires |
