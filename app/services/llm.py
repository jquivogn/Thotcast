import logging
import re

import ollama
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article, Config

logger = logging.getLogger(__name__)

MODEL = "llama3.1:8b"
MAX_ARTICLES = 15


def _build_prompt(articles: list[Article], structure: list[dict], keywords: list[str]) -> str:
    articles_block = "\n\n".join(
        f"ARTICLE {i + 1} — {a.title}:\n{a.content}"
        for i, a in enumerate(articles[:MAX_ARTICLES])
    )
    structure_block = "\n".join(
        f"{i + 1}. [{s['character']}] : {s['subject']}"
        for i, s in enumerate(structure)
    )
    keywords_str = ", ".join(keywords) if keywords else "actualités générales"

    return f"""Tu es un scénariste de podcast d'information. Rédige un script de podcast d'environ 10 minutes \
basé sur les articles ci-dessous.

ARTICLES :
{articles_block}

THÉMATIQUES : {keywords_str}

STRUCTURE DU PODCAST — respecte STRICTEMENT cet ordre :
{structure_block}

RÈGLES :
1. Chaque réplique commence par [NomPersonnage]: suivi du texte, sans ligne vide entre les deux.
2. Aucune didascalie, parenthèse ou commentaire hors dialogue.
3. Vise ~1 500 mots au total (≈ 10 minutes de lecture).
4. Base-toi uniquement sur les articles fournis.
5. Enchaîne les répliques sans numérotation.

SCRIPT :"""


def _parse_script(script_text: str, structure: list[dict]) -> list[dict]:
    characters = {s["character"] for s in structure}
    voice_map = {s["character"]: s["voice"] for s in structure}

    lines = []
    pattern = re.compile(
        r"\[([^\]]+)\]\s*:\s*(.+?)(?=\n\[[^\]]+\]\s*:|$)", re.DOTALL
    )
    for m in pattern.finditer(script_text):
        character = m.group(1).strip()
        text = re.sub(r"\s+", " ", m.group(2)).strip()
        if character in characters and text:
            lines.append({
                "character": character,
                "text": text,
                "voice": voice_map[character],
            })

    return lines


async def generate_script(db: AsyncSession) -> tuple[str, str, list[dict]]:
    cfg_result = await db.execute(select(Config).order_by(Config.id.desc()).limit(1))
    config = cfg_result.scalar_one_or_none()
    if not config:
        raise ValueError("Aucune configuration trouvée")

    arts_result = await db.execute(
        select(Article).order_by(Article.created_at.desc()).limit(MAX_ARTICLES)
    )
    articles = arts_result.scalars().all()
    if not articles:
        raise ValueError("Aucun article disponible pour générer le script")

    prompt = _build_prompt(articles, config.podcast_structure, config.keywords)
    logger.info("Génération du script : %d articles, modèle %s", len(articles), MODEL)

    raw = ollama.generate(
        model=MODEL,
        prompt=prompt,
        options={"num_ctx": 8192, "temperature": 0.7},
    )
    script_text = raw.response if hasattr(raw, "response") else raw["response"]

    lines = _parse_script(script_text, config.podcast_structure)
    if not lines:
        raise ValueError("Le LLM n'a renvoyé aucune réplique parsable")

    title_raw = ollama.generate(
        model=MODEL,
        prompt=(
            "En une phrase courte et accrocheuse (max 15 mots), quel titre donnerais-tu à ce podcast "
            f"basé sur : {', '.join(a.title for a in articles[:5])} ? Réponds uniquement avec le titre, sans guillemets."
        ),
        options={"num_ctx": 512, "temperature": 0.5},
    )
    title_text = title_raw.response if hasattr(title_raw, "response") else title_raw["response"]
    title = title_text.strip().strip('"').strip("'")[:200]

    summary = (
        f"Podcast du {articles[0].created_at.strftime('%d/%m/%Y') if articles else 'jour'} "
        f"— {len(articles)} articles — thèmes : {', '.join(config.keywords[:3])}"
    )

    return title, summary, lines
