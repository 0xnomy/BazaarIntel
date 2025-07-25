import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')

import re
import string
from collections import Counter
import textstat
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

stop_words = set(stopwords.words('english'))

def tokenize(text):
    return [w.lower() for w in word_tokenize(text) if w.isalnum()]

def count_occurrences(keywords, text_tokens):
    count = 0
    for kw in keywords:
        for word in kw.split():
            count += text_tokens.count(word)
    return count

# 1. Keyword Density Score
def keyword_density_score(description, brand, keyword_map):
    brand = brand.strip().title()  # Normalize brand name
    text_tokens = tokenize(description)
    total_words = len(text_tokens)
    brand_keywords = [kw.lower() for kw in keyword_map.get(brand, [])]
    keyword_count = count_occurrences(brand_keywords, text_tokens)
    if total_words == 0:
        return 0
    if keyword_count == 0:
        return 0
    density = (keyword_count / total_words) * 100
    if 4 <= density <= 7:
        return 100
    elif 2 <= density < 4:
        return 80
    elif 1 <= density < 2:
        return 60
    elif 0 < density < 1:
        return 30
    elif 7 < density <= 10:
        return 70
    elif 10 < density <= 15:
        return 40
    elif density > 15:
        return 20
    return 50


def content_quality_score(description):
    text = description
    tokens = tokenize(text)
    word_count = len(tokens)
    length_score = 20 if 50 <= word_count <= 150 else 0
    sentences = re.split(r'[.!?]', text)
    sentence_lengths = [len(tokenize(s)) for s in sentences if s.strip()]
    varied_sentence = 15 if len(set(sentence_lengths)) > 1 else 0
    adjectives = ["elegant", "luxurious", "vibrant", "classic", "modern", "trendy"]
    rich_adj = 15 if any(adj in text.lower() for adj in adjectives) else 0
    technical_terms = ["cambric fabric", "jacquard", "chiffon", "lawn", "cotton"]
    technical = 10 if any(term in text.lower() for term in technical_terms) else 0
    cta_phrases = ["shop now", "order today", "don't miss", "grab yours"]
    cta = 10 if any(phrase in text.lower() for phrase in cta_phrases) else 0
    redundancy = 10 if len(set(tokens)) / (len(tokens) + 1e-5) > 0.7 else 0
    grammar = 20 if "." in text and not re.search(r'(.)\1\1', text) else 10
    return min(length_score + varied_sentence + rich_adj + technical + cta + redundancy + grammar, 100)

# 5. Brand Consistency Score
def brand_consistency_score(description, brand):
    brand = brand.strip().title()  # Normalize brand name
    brand_keywords = {
        "Khaadi": ["traditional", "embroidered", "floral", "casual"],
        "Outfitters": ["casual", "relaxed fit", "streetwear", "breathable"],
        "Sana Safinaz": ["luxury", "chiffon", "formal", "collection", "elegant"],
        "Alkaram Studio": ["cotton", "cambric", "2-piece", "ethnic wear", "printed"],
        "Breakout": ["urban", "denim", "minimalist", "street style"]
    }
    text = description.lower()
    must_have = brand_keywords.get(brand, [])
    matches = sum(1 for kw in must_have if kw in text)
    if not must_have:
        return 50
    return int((matches / len(must_have)) * 100)

# 6. Uniqueness Score (Jaccard Similarity with NLTK)
def uniqueness_score(description, brand, all_descriptions=None):
    if not all_descriptions:
        return 100
    desc_tokens = set([w for w in tokenize(description) if w not in stop_words])
    similarities = []
    for other in all_descriptions:
        if other == description:
            continue
        other_tokens = set([w for w in tokenize(other) if w not in stop_words])
        intersection = desc_tokens & other_tokens
        union = desc_tokens | other_tokens
        sim = len(intersection) / (len(union) + 1e-5)
        similarities.append(sim)
    if not similarities:
        return 100
    max_sim = max(similarities)
    if max_sim < 0.3:
        return 100
    elif max_sim < 0.5:
        return 70
    elif max_sim < 0.7:
        return 40
    else:
        return 10


# 8. Readability Score
def readability_score(description):
    word_count = len(tokenize(description))
    sentences = re.split(r'[.!?]', description)
    avg_sentence_length = sum(len(tokenize(s)) for s in sentences if s.strip()) / (len(sentences) or 1)
    wc_score = 20 if 50 <= word_count <= 150 else 0
    sl_score = 20 if 10 <= avg_sentence_length <= 20 else 0
    jargon = ["jacquard", "cambric", "fusionwear"]
    simple_vocab = 30 if not any(j in description.lower() for j in jargon) else 15
    para_score = 30 if '\n' in description else 15
    try:
        flesch = textstat.flesch_reading_ease(description)
        if flesch < 30:
            return 40
        elif flesch < 60:
            return 70
        else:
            return 100
    except Exception:
        return min(wc_score + sl_score + simple_vocab + para_score, 100)

def seo_scores(description, brand, keyword_map, all_descriptions=None):
    brand = brand.strip().title()  # Normalize brand name
    return {
        "keyword_density": keyword_density_score(description, brand, keyword_map),
        "content_quality": content_quality_score(description),
        "brand_consistency": brand_consistency_score(description, brand),
        "uniqueness": uniqueness_score(description, brand, all_descriptions),
        "readability": readability_score(description)
    }
